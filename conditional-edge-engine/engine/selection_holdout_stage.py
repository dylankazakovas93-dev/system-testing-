"""CAMPAIGN-LEVEL selection holdout, human final-configuration selection and the hand-over to automatic CPCV.

Lifecycle (nothing in this module creates a human file):
  DEVELOPMENT / IS -> IS SHORTLIST + NEAR-TIE DETECTION (engine/near_tie.py, shown in the IS report) -> HUMAN DECISION
    A. choose ONE config directly from the deterministic IS-eligible list and skip the holdout (SELECTION_HOLDOUT_SKIPPED),
    B. approve the top-2 near-tied configs of ONE near-tie cluster for the selection holdout,
    C. decline.
  Holdout path (campaign-wide):
    1. every experiment of the campaign finishes its IS stage;
    2. the human writes approvals/EXP_xxxx_SELECTION_HOLDOUT_APPROVAL.yaml (exactly the 2 proposable configs of one near-tie cluster);
    3. ``freeze_campaign_selection_holdout`` CLOSES the campaign and freezes ALL approved configs of ALL experiments together
       (max 2 per experiment, max 6 per campaign => at most 18 model evaluations);
    4. the human writes approvals/CAMPAIGN_xxxx_SELECTION_HOLDOUT_OPEN_APPROVAL.yaml citing the freeze hash;
    5. ``run_campaign_selection_holdout`` opens the shared holdout EXACTLY ONCE; the ledger row is written BEFORE any holdout data is read;
       BH and Bonferroni run over EVERY approved config x 3 models of the whole campaign. This is SELECTION DATA, never confirmation.
  Final configuration: the human writes approvals/EXP_xxxx_FINAL_CONFIG_SELECTION.yaml (exactly ONE config, or DECLINE).
  ``freeze_final_config`` validates it (FINAL_CONFIG_FROZEN); the fixed CPCV then runs AUTOMATICALLY (no approval; engine/cpcv.py);
  a CPCV failure ends the lineage — there is no fallback to a runner-up. The final lockbox is never opened here.
Bars at/after selection_holdout_end (the final lockbox) are removed before any computation.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from engine import near_tie as nt
from engine import trial_registry as reg
from engine.acceptance import SHORTLIST, path_verification, rank_groups
from engine.common import EngineError, Frozen, engine_code_hash, load_frozen, model_names, now_utc_iso, sha256_file, utc_ns
from engine.event_contract import load_event_module, load_spec
from engine.experiment_lifecycle import MANIFEST, experiment_dir, verify_manifest
from engine.experiment_runner import bars_fingerprint, build_event_tables
from engine.holdout_preference import holdout_preference
from engine.model_engine import make_model_factory
from engine.multiplicity import benjamini_hochberg
from engine.partitions import parse_partitions, selection_holdout_view
from engine.score_calibration import WFConfig, assign_state, calibrate_threshold
from engine.statistics import evaluate_panel, week_key, weeks_in_intervals

APPROVER = "HUMAN_USER"
CAMPAIGN_APPROVAL_KEYS = ["campaign_id", "selection_holdout_freeze_sha256", "approved_by", "approved", "approval_note"]
APPROVAL_KEYS = ["experiment_id", "campaign_id", "manifest_sha256", "is_report_sha256", "near_tie_cluster_id", "approved", "approved_by",
                 "approved_configs", "approval_note"]
FINAL_KEYS = ["experiment_id", "campaign_id", "manifest_sha256", "is_report_sha256", "selection_holdout_report_sha256", "selected_config_id",
              "selected_by", "selection_note"]
DECLINE = "DECLINE"
HOLDOUT_BANNER = "SELECTION DATA — USED TO CHOOSE FINAL CONFIGURATION / NOT FINAL CONFIRMATION"
PENDING_FINAL = ("NEAR_TIE_REVIEW_REQUIRED", "AWAITING_HUMAN_FINAL_CONFIG_SELECTION")


class ApprovalError(EngineError):
    pass


SelectionHoldoutContaminated = reg.SelectionHoldoutContaminated


# ---------------------------------------------------------------------------- paths / read-only helpers for the human
def approval_path(ws: reg.Workspace, experiment_id: str) -> Path:
    return ws.approvals / f"{experiment_id}_SELECTION_HOLDOUT_APPROVAL.yaml"


def final_selection_path(ws: reg.Workspace, experiment_id: str) -> Path:
    return ws.approvals / f"{experiment_id}_FINAL_CONFIG_SELECTION.yaml"


def campaign_approval_path(ws: reg.Workspace, campaign_id: str) -> Path:
    return ws.approvals / f"CAMPAIGN_{campaign_id}_SELECTION_HOLDOUT_OPEN_APPROVAL.yaml"


def freeze_path(ws: reg.Workspace, campaign_id: str) -> Path:
    return ws.root / "registry" / f"selection_holdout_freeze_{campaign_id}.json"


def holdout_report_path(ws: reg.Workspace, experiment_id: str) -> Path:
    return experiment_dir(ws, experiment_id) / "results" / "SELECTION_HOLDOUT_REPORT.json"


def approval_hashes(ws: reg.Workspace, experiment_id: str) -> dict:
    """Read-only helper for the HUMAN: the exact hashes an approval / selection file must reference, the deterministic eligible list and the near-tie clusters."""
    d = experiment_dir(ws, experiment_id)
    rep = d / "results" / "IS_REPORT.json"
    out = {"manifest_sha256": sha256_file(d / MANIFEST), "is_report_sha256": sha256_file(rep) if rep.exists() else None}
    if rep.exists():
        J = json.loads(rep.read_text())
        out["allowed_target_side_groups"] = [g["group_id"] for g in J["I_top_configurations"]["top_groups"]]
        out["eligible_config_ids"] = [nt.config_id(experiment_id, g) for g in out["allowed_target_side_groups"]]
        out["near_tie_clusters"] = [{"cluster_id": c["cluster_id"], "proposable_for_holdout": c["proposable_for_holdout"], "members": c["members"]}
                                    for c in J.get("NT_configuration_uncertainty", {}).get("clusters", [])]
    hp = holdout_report_path(ws, experiment_id)
    if hp.exists():
        out["selection_holdout_report_sha256"] = sha256_file(hp)
    return out


def mark_contamination_if_mutated(ws: reg.Workspace, experiment_id: str) -> bool:
    """If the campaign's selection holdout was spent and the frozen experiment was changed afterwards, mark it SELECTION_HOLDOUT_CONTAMINATED."""
    if not reg.selection_holdout_spent(ws, experiment_id):
        return False
    errs = verify_manifest(ws, experiment_id, raise_on_error=False)["errors"]
    if errs:
        reg.set_status(ws, experiment_id, "SELECTION_HOLDOUT_CONTAMINATED", "frozen experiment changed after the selection holdout was spent: " + "; ".join(errs[:3]))
        return True
    return False


def assert_campaign_group_cap(entries: list[dict], frozen: Frozen) -> int:
    """Frozen caps over ALL positively approved configs: <= 2 per experiment, <= 6 per campaign. Returns the config count.
    The cap is a frozen constant: it is never relaxed because Bonferroni becomes strict."""
    pol = frozen.trial_policy["selection_holdout"]
    per_exp, per_camp = pol["max_groups_per_experiment"], pol["max_groups_per_campaign"]
    for e in entries:
        if len(e["approved_configs"]) > per_exp:
            raise ApprovalError(f"{e['experiment_id']}: {len(e['approved_configs'])} configs approved; MAX_SELECTION_HOLDOUT_CONFIGS_PER_EXPERIMENT = {per_exp}")
    total = sum(len(e["approved_configs"]) for e in entries)
    if total > per_camp:
        raise ApprovalError(f"{total} approved configs across the campaign > MAX_SELECTION_HOLDOUT_CONFIGS_PER_CAMPAIGN = {per_camp} "
                            f"(max {per_camp} x 3 models = {3 * per_camp} holdout evaluations); the campaign selection holdout freeze is refused and nothing was changed")
    return total


def _is_report_checks(ws, experiment_id: str, exp: dict, ap: dict, errs: list[str], hash_key: str = "manifest_sha256") -> dict:
    """Shared integrity checks of a human file against the exact frozen manifest and IS report. Returns the parsed IS report."""
    d = experiment_dir(ws, experiment_id)
    mv = verify_manifest(ws, experiment_id, raise_on_error=False)
    errs += [f"experiment changed since freeze (approval invalidated): {e}" for e in mv["errors"]]
    if ap[hash_key] != sha256_file(d / MANIFEST):
        errs.append("manifest_sha256 does not match the exact frozen manifest (wrong or stale file)")
    rep = d / "results" / "IS_REPORT.json"
    if not rep.exists():
        errs.append("IS_REPORT.json missing")
        raise ApprovalError("; ".join(errs))
    if ap["is_report_sha256"] != sha256_file(rep):
        errs.append("is_report_sha256 does not match the exact IS_REPORT.json (wrong IS report or IS results changed)")
    J = json.loads(rep.read_text())
    if hashlib.sha256((d / "results" / "IS_REPORT.md").read_bytes()).hexdigest() != J["markdown_sha256"]:
        errs.append("IS_REPORT.md was edited after the report was generated")
    if sha256_file(d / "results" / "results.json") != J["X_hashes"]["results_sha256"]:
        errs.append("IS results.json changed after the IS report was generated (IS results invalidate the approval)")
    ps = J["X_hashes"].get("path_diagnostics_sha256")
    if ps and sha256_file(d / "results" / "PATH_DIAGNOSTICS.json") != ps:
        errs.append("PATH_DIAGNOSTICS.json changed after the IS report was generated")
    if exp["is_report_sha256"] and exp["is_report_sha256"] != sha256_file(rep):
        errs.append("IS_REPORT.json differs from the registry")
    return J


def _verified(ws, experiment_id: str, group_id: str, frozen: Frozen, errs: list[str]) -> None:
    exp = reg.experiment_row(ws, experiment_id)
    trials = reg.experiment_trials(ws, experiment_id)
    ver = json.loads(exp["verification_json"] or "{}")
    t, s = group_id.split("|")
    rows = trials[(trials["target"] == t) & (trials["state"] == s)].to_dict("records")
    if sum(1 for r in rows if r["decision"] == SHORTLIST) < frozen.acceptance["model_agreement"]["min_models_passing"]:
        errs.append(f"{group_id} is no longer IS_SHORTLIST_ELIGIBLE under the current campaign universe")
    for r in rows:
        if path_verification(ver, r, frozen.acceptance) != "PASS":
            errs.append(f"model path {r['target']}|{r['model']} is not externally verified (strong mode, research families PASS); all 3 models of a config must be verified")


# ---------------------------------------------------------------------------- per-experiment holdout approval
def validate_approval(ws: reg.Workspace, experiment_id: str, frozen: Frozen | None = None, *, campaign_frozen: bool = False) -> dict:
    """Validate the human's per-experiment selection-holdout approval: exactly the 2 proposable configs of ONE near-tie cluster."""
    frozen = frozen or load_frozen()
    exp = reg.experiment_row(ws, experiment_id)
    if exp["status"] == "SELECTION_HOLDOUT_CONTAMINATED":
        raise SelectionHoldoutContaminated(f"{experiment_id} is SELECTION_HOLDOUT_CONTAMINATED")
    cid = exp["campaign_id"]
    if reg.campaign_selection_holdout_spent(ws, cid):
        raise SelectionHoldoutContaminated(f"CAMPAIGN SELECTION HOLDOUT HAS BEEN SPENT ({cid}); {experiment_id} cannot claim the shared holdout partition as untouched selection data")
    if not campaign_frozen:
        reg.assert_campaign_open(ws, cid, f"approve the selection holdout for {experiment_id}")
    reg.assert_selection_holdout_partition_untouched(ws, reg.campaign_partitions(ws, cid), exclude_campaign=cid)
    p = approval_path(ws, experiment_id)
    if not p.exists():
        raise ApprovalError(f"no human approval file: {p}. The selection holdout stays sealed. (Written by the human only; "
                            f"no script or LLM creates it. Hashes to reference: scripts/show_approval_hashes.py)")
    ap = yaml.safe_load(p.read_text())
    if not isinstance(ap, dict) or any(k not in ap for k in APPROVAL_KEYS):
        raise ApprovalError(f"approval file must contain the keys {APPROVAL_KEYS}")
    errs: list[str] = []
    if ap["experiment_id"] != experiment_id:
        errs.append("experiment_id mismatch")
    if ap["campaign_id"] != cid:
        errs.append("campaign_id mismatch")
    if ap["approved_by"] != APPROVER:
        errs.append(f"approved_by must be exactly {APPROVER}")
    if ap["approved"] is not True:
        if ap["approved"] is False:
            reg.set_status(ws, experiment_id, "HUMAN_DECLINED", "human declined the selection holdout (approved: false)")
            raise ApprovalError(f"{experiment_id}: the human did not approve the selection holdout (HUMAN_DECLINED)")
        errs.append("approved must be the boolean true")
    if not (isinstance(ap["approval_note"], str) and ap["approval_note"].strip()):
        errs.append("approval_note must be non-empty")
    J = _is_report_checks(ws, experiment_id, exp, ap, errs)
    cfgs = ap["approved_configs"]
    pol = frozen.trial_policy["selection_holdout"]
    cluster = None
    if not (isinstance(cfgs, list) and cfgs and all(isinstance(c, str) for c in cfgs)):
        errs.append("approved_configs must be a non-empty list of config ids '<experiment>|<TARGET>|<STATE>'")
    else:
        if len(cfgs) > pol["max_groups_per_experiment"]:
            errs.append(f"{len(cfgs)} configs approved; MAX_SELECTION_HOLDOUT_CONFIGS_PER_EXPERIMENT = {pol['max_groups_per_experiment']}")
        if len(set(cfgs)) != len(cfgs):
            errs.append("duplicate approved configs")
    expected = "SELECTION_HOLDOUT_FROZEN" if campaign_frozen else "NEAR_TIE_REVIEW_REQUIRED"      # at the opening the freeze has already moved the status
    if exp["status"] != expected:
        errs.append(f"{experiment_id} is {exp['status']}, not {expected}: only a near-tie cluster can be proposed for the selection holdout "
                    f"(a clearly preferred config is chosen directly; the holdout stays unread)")
    if errs:
        raise ApprovalError("; ".join(errs))
    det = nt.detect(ws, experiment_id, frozen)                                # re-derived NOW under the current campaign universe
    cluster = next((c for c in det["clusters"] if c["cluster_id"] == ap["near_tie_cluster_id"]), None)
    if cluster is None:
        raise ApprovalError(f"near_tie_cluster_id {ap['near_tie_cluster_id']!r} does not exist (clusters: {[c['cluster_id'] for c in det['clusters']]}); "
                            f"the IS evidence may have changed since the approval")
    for c in cfgs:
        if c not in cluster["proposable_for_holdout"]:
            errs.append(f"{c} is not one of the top-2 (by the frozen IS group ranking) configs of {cluster['cluster_id']}: {cluster['proposable_for_holdout']}")
    if set(cfgs) != set(cluster["proposable_for_holdout"]):
        errs.append(f"the holdout compares the near-tied pair: approved_configs must be exactly {cluster['proposable_for_holdout']}")
    groups = []
    for c in cfgs:
        e_, g = nt.split_config_id(c)
        if e_ != experiment_id:
            errs.append(f"{c} belongs to another experiment")
        groups.append(g)
        _verified(ws, experiment_id, g, frozen, errs)
    if errs:
        raise ApprovalError("; ".join(errs))
    ap["_approval_file_sha256"] = sha256_file(p)
    ap["_groups"] = groups
    ap["_cluster"] = cluster
    ap["_is_report"] = J
    return ap


# ---------------------------------------------------------------------------- selection-holdout evidence (NOT confirmation)
def _selection_holdout_gate(row: dict, rule: dict) -> tuple[bool, str]:
    """INFORMATIONAL evidence gates (the IS-style gates applied to the holdout). They label evidence; they never confirm anything."""
    why = []
    if not row["n_selected"] > 0 or any(np.isnan(row[k]) for k in ("selected_frequency", "standardized_uplift", "selected_effect", "bootstrap_ci_low")):
        return False, "NOT_EVALUABLE: no selected selection-holdout events"
    if row["selected_frequency"] < rule["min_selected_frequency_per_week"]:
        why.append(f"selected frequency {row['selected_frequency']:.3f}/week < {rule['min_selected_frequency_per_week']}")
    if row["standardized_uplift"] < rule["min_standardized_uplift"]:
        why.append(f"standardized uplift {row['standardized_uplift']:.3f} < {rule['min_standardized_uplift']}")
    if not row["selected_effect"] > rule["selected_effect_must_exceed"]:
        why.append(f"selected effect {row['selected_effect']:+.5f} <= 0")
    if not row["bootstrap_ci_low"] > rule["bootstrap_ci_lower_bound_must_exceed"]:
        why.append(f"CI lower bound {row['bootstrap_ci_low']:.5f} <= 0")
    if row["selection_holdout_q"] > rule["max_selection_holdout_bh_q"]:
        why.append(f"selection-holdout BH q {row['selection_holdout_q']:.4f} > {rule['max_selection_holdout_bh_q']}")
    if row["selection_holdout_bonferroni_p"] > rule["max_selection_holdout_bonferroni_p"]:
        why.append(f"selection-holdout Bonferroni p {row['selection_holdout_bonferroni_p']:.4f} > {rule['max_selection_holdout_bonferroni_p']}")
    return (not why), "; ".join(why)


def selection_holdout_evaluations(rows: list[dict], rule: dict) -> list[dict]:
    """Add selection-holdout BH q and Bonferroni p across ALL approved config x 3 model evaluations of the campaign (never only winners)."""
    m = len(rows)
    p = np.array([r["raw_p"] for r in rows], dtype=float)
    q = benjamini_hochberg(p)
    out = []
    for r, qi, pi in zip(rows, q, p):
        r = dict(r, selection_holdout_q=float(qi), selection_holdout_bonferroni_p=float(min(pi * m, 1.0)), selection_holdout_trials_in_family=m)
        r["gates_pass"], r["rejection_reason"] = _selection_holdout_gate(r, rule)
        out.append(r)
    return out


def group_verdicts(rows: list[dict], rule: dict) -> dict[str, dict]:
    """Informational: how many of a config's 3 models meet the evidence gates (>= 2 of 3 = 'evidence_gates_met'). Not a confirmation."""
    verdicts = {}
    for gid in sorted({r["group_id"] for r in rows}):
        g = [r for r in rows if r["group_id"] == gid]
        npass = sum(1 for r in g if r["gates_pass"])
        verdicts[gid] = {"models_passing": npass, "models": sorted(r["model"] for r in g if r["gates_pass"]),
                         "evidence_gates_met": npass >= rule["min_models_passing"]}
    return verdicts


# ---------------------------------------------------------------------------- campaign freeze (closes the campaign)
def freeze_campaign_selection_holdout(ws: reg.Workspace, campaign_id: str, frozen: Frozen | None = None) -> dict:
    """HUMAN-run step: close the campaign and freeze every approved config of every experiment TOGETHER.

    Requires every experiment of the campaign to have finished its IS stage. Only experiments in NEAR_TIE_REVIEW_REQUIRED can carry an approval.
    An explicit `approved: false` becomes HUMAN_DECLINED; experiments without a holdout approval simply keep their status (they may still be chosen
    directly). Any INVALID approval aborts the freeze with nothing changed; more than 6 configs / 2 per experiment is refused atomically."""
    frozen = frozen or load_frozen()
    reg.assert_campaign_open(ws, campaign_id, "freeze its selection holdout")
    parts = reg.campaign_partitions(ws, campaign_id)
    reg.assert_selection_holdout_partition_untouched(ws, parts, exclude_campaign=campaign_id)
    exps = reg.read_experiments(ws)
    exps = exps[exps["campaign_id"] == campaign_id]
    if exps.empty:
        raise EngineError(f"campaign {campaign_id} has no experiments")
    incomplete = sorted(exps[exps["status"].isin(["DRAFT", "FROZEN"])]["experiment_id"])
    if incomplete:
        raise EngineError(f"campaign {campaign_id} IS stage is incomplete: {incomplete} have not completed their IS run. "
                          f"ALL IS experiments must be completed before the selection holdout can be frozen or opened")
    included, excluded, to_decline = [], {}, []
    for e, st in zip(exps["experiment_id"], exps["status"]):
        if st != "NEAR_TIE_REVIEW_REQUIRED":
            excluded[e] = st
            continue
        p = approval_path(ws, e)
        raw = yaml.safe_load(p.read_text()) if p.exists() else None
        if raw is None:
            excluded[e] = "NO_HOLDOUT_APPROVAL"
        elif isinstance(raw, dict) and raw.get("approved") is False:
            excluded[e] = "HUMAN_DECLINED"
            to_decline.append(e)
        else:
            ap = validate_approval(ws, e, frozen)                      # raises on any problem: nothing is changed
            d = experiment_dir(ws, e)
            included.append({"experiment_id": e, "near_tie_cluster_id": ap["near_tie_cluster_id"], "approved_configs": list(ap["approved_configs"]),
                             "is_ranks": ap["_cluster"]["is_ranks"], "manifest_sha256": sha256_file(d / MANIFEST), "is_report_sha256": ap["is_report_sha256"],
                             "approval_file_sha256": ap["_approval_file_sha256"],
                             "verification_hash": hashlib.sha256((reg.experiment_row(ws, e)["verification_json"] or "{}").encode()).hexdigest()})
    if not included:
        raise EngineError(f"nothing to freeze for {campaign_id}: no experiment has a valid positive human selection-holdout approval")
    n_cfg = assert_campaign_group_cap(included, frozen)                       # BEFORE any state change or file write
    pp = parse_partitions(parts)
    doc = {"campaign_id": campaign_id, "partitions": parts, "partitions_hash": pp.hash(), "selection_holdout_years": pp.selection_holdout_years,
           "frozen_at": now_utc_iso(), "experiments": included, "experiments_not_included": excluded, "n_approved_configs": n_cfg,
           "approved_config_ids": [c for e in included for c in e["approved_configs"]], "n_holdout_evaluations": 3 * n_cfg,
           "code_hash": engine_code_hash(),
           "note": "Campaign closed. Every approved config of every experiment is evaluated together in ONE selection-holdout opening; "
                   "BH and Bonferroni run over all n_holdout_evaluations = 3 models x n_approved_configs. SELECTION DATA, not confirmation."}
    path = freeze_path(ws, campaign_id)
    path.write_text(json.dumps(doc, indent=2, sort_keys=True))
    h = sha256_file(path)
    for e in to_decline:
        reg.set_status(ws, e, "HUMAN_DECLINED", "human declined the selection holdout (approved: false)")
    for ent in included:
        reg.set_status(ws, ent["experiment_id"], "SELECTION_HOLDOUT_FROZEN", f"configs {ent['approved_configs']} frozen before any holdout byte is read")
    reg.update_campaign(ws, campaign_id, status="SELECTION_HOLDOUT_FROZEN", selection_holdout_freeze_hash=h)
    return {**doc, "freeze_sha256": h, "path": str(path)}


def campaign_open_hashes(ws: reg.Workspace, campaign_id: str) -> dict:
    """Read-only helper for the HUMAN: what the campaign-open approval must cite."""
    c = reg.campaign_row(ws, campaign_id)
    return {"campaign_id": campaign_id, "campaign_status": c["status"], "selection_holdout_freeze_sha256": c["selection_holdout_freeze_hash"] or None,
            "freeze_file": str(freeze_path(ws, campaign_id))}


def validate_campaign_open(ws: reg.Workspace, campaign_id: str, frozen: Frozen | None = None) -> tuple[dict, dict, dict]:
    """Everything that must hold before the shared selection holdout may be opened (once) for the campaign."""
    frozen = frozen or load_frozen()
    c = reg.campaign_row(ws, campaign_id)
    if c["status"] == "SELECTION_HOLDOUT_SPENT" or reg.campaign_selection_holdout_spent(ws, campaign_id):
        raise SelectionHoldoutContaminated(f"CAMPAIGN SELECTION HOLDOUT HAS BEEN SPENT ({campaign_id}); it can never be opened again")
    if c["status"] != "SELECTION_HOLDOUT_FROZEN":
        raise ApprovalError(f"campaign {campaign_id} is {c['status']}; its selection holdout must first be frozen with scripts/freeze_campaign_selection_holdout.py")
    reg.assert_selection_holdout_partition_untouched(ws, reg.campaign_partitions(ws, campaign_id), exclude_campaign=campaign_id)
    fp = freeze_path(ws, campaign_id)
    if not fp.exists() or sha256_file(fp) != c["selection_holdout_freeze_hash"]:
        raise ApprovalError("the campaign selection holdout freeze document is missing or was edited after the freeze")
    doc = json.loads(fp.read_text())
    n = assert_campaign_group_cap(doc["experiments"], frozen)                  # integrity: a (re-hashed) tampered freeze cannot exceed the cap
    if doc["n_approved_configs"] != n or doc["n_holdout_evaluations"] != 3 * n:
        raise ApprovalError("freeze document is internally inconsistent (config / evaluation counts)")
    if {e["experiment_id"] for e in doc["experiments"]} - set(reg.read_experiments(ws).query("campaign_id == @campaign_id")["experiment_id"]):
        raise ApprovalError("freeze document references experiments outside the campaign")
    p = campaign_approval_path(ws, campaign_id)
    if not p.exists():
        raise ApprovalError(f"no human campaign-open approval file: {p}. The shared selection holdout stays sealed. (Written by the human only; "
                            f"cite the freeze hash from scripts/show_approval_hashes.py --campaign {campaign_id})")
    cap = yaml.safe_load(p.read_text())
    if not isinstance(cap, dict) or any(k not in cap for k in CAMPAIGN_APPROVAL_KEYS):
        raise ApprovalError(f"campaign approval file must contain the keys {CAMPAIGN_APPROVAL_KEYS}")
    errs = []
    if cap["campaign_id"] != campaign_id:
        errs.append("campaign_id mismatch")
    if cap["approved_by"] != APPROVER:
        errs.append(f"approved_by must be exactly {APPROVER}")
    if cap["approved"] is not True:
        errs.append("approved must be the boolean true")
    if cap["selection_holdout_freeze_sha256"] != c["selection_holdout_freeze_hash"]:
        errs.append("selection_holdout_freeze_sha256 does not match the exact campaign freeze document")
    if not (isinstance(cap["approval_note"], str) and cap["approval_note"].strip()):
        errs.append("approval_note must be non-empty")
    if errs:
        raise ApprovalError("; ".join(errs))
    cap["_file_sha256"] = sha256_file(p)
    aps = {}
    for ent in doc["experiments"]:
        e = ent["experiment_id"]
        ap = validate_approval(ws, e, frozen, campaign_frozen=True)       # re-check every per-experiment approval and hash
        for k, v in (("approval_file_sha256", ap["_approval_file_sha256"]), ("is_report_sha256", ap["is_report_sha256"]),
                     ("approved_configs", list(ap["approved_configs"]))):
            if ent[k] != v:
                raise ApprovalError(f"{e}: {k} changed since the campaign freeze")
        if ent["manifest_sha256"] != sha256_file(experiment_dir(ws, e) / MANIFEST):
            raise ApprovalError(f"{e}: manifest changed since the campaign freeze")
        aps[e] = ap
    return doc, cap, aps


# ---------------------------------------------------------------------------- the single campaign opening
def run_campaign_selection_holdout(ws: reg.Workspace, campaign_id: str, bars: pd.DataFrame, *, verbose: bool = True) -> dict:
    """Open the campaign's shared selection holdout ONCE (ledger first). ``bars`` may extend past selection_holdout_end: that is cut first."""
    frozen = load_frozen()
    doc, cap, aps = validate_campaign_open(ws, campaign_id, frozen)
    parts = parse_partitions(reg.campaign_partitions(ws, campaign_id))
    bars_h = selection_holdout_view(bars, parts)                              # final lockbox removed BEFORE any computation
    del bars
    assert bars_h.index.tz_convert("UTC").max() < parts.selection_holdout_end
    items = []
    for e, ap in aps.items():
        d = experiment_dir(ws, e)
        spec = load_spec(d / "EVENT_SPEC.yaml")
        module = load_event_module(d / "event.py")
        items.append((e, ap, (lambda module=module, spec=spec: build_event_tables(module, spec, bars_h, frozen)[:4]), bars_h.index, bars_h))
    fp = bars_fingerprint(bars_h[bars_h.index.tz_convert("UTC") >= parts.development_end])
    return execute_campaign_selection_holdout(ws, campaign_id, cap, items, fp, verbose=verbose)


def _holdout_raw_rows(experiment_id: str, groups: list[str], tables, calendar_index: pd.DatetimeIndex, parts, frozen: Frozen):
    """3 x (configs) raw holdout model results of ONE experiment + the per-(group, model) holdout series (no multiplicity correction yet)."""
    cfg = WFConfig.from_policy(frozen.trial_policy)
    pol = frozen.trial_policy
    from engine.feature_engine import feature_names
    names = feature_names(frozen)
    dev_end_ns = int(parts.development_end.value)
    end_ns = int(parts.selection_holdout_end.value)
    events, features, eligible, targets = tables()
    ev = events.assign(_el=np.asarray(eligible, dtype=bool))
    ev = ev[ev["_el"]].sort_values(["event_time", "event_id"], kind="stable").reset_index(drop=True)
    feat = features.set_index("event_id")
    wk = weeks_in_intervals(calendar_index, [(dev_end_ns, end_ns)], frozen.tz)
    raw_rows: list[dict] = []
    series: dict = {}
    for t in sorted({g.split("|")[0] for g in groups}):
        tdf = targets[t].set_index("event_id")
        ids = [i for i in ev["event_id"] if i in tdf.index]
        sub = ev.set_index("event_id").loc[ids]
        etime = pd.DatetimeIndex(sub["event_time"])
        ev_ns = utc_ns(etime)
        te_ns = utc_ns(pd.DatetimeIndex(tdf.loc[ids, "effective_target_end"]))
        y = tdf.loc[ids, "value"].to_numpy("float64")
        X = feat.loc[ids, names].reset_index(drop=True)
        train = np.flatnonzero((ev_ns < dev_end_ns) & (te_ns < dev_end_ns))      # only information available before the holdout
        hidx = np.flatnonzero((ev_ns >= dev_end_ns) & (te_ns <= end_ns))
        for mname in model_names(frozen):
            fac = make_model_factory(mname, frozen)
            thr = calibrate_threshold(fac, X, y, ev_ns, te_ns, train, cfg)[0] if len(train) >= cfg.min_outer_train_events else None
            for g in [g for g in groups if g.startswith(t + "|")]:
                state = g.split("|")[1]
                base = {"experiment_id": experiment_id, "group_id": g, "target": t, "state": state, "model": mname, "selection_holdout_weeks": wk["total"]}
                if thr is None or len(hidx) == 0:
                    raw_rows.append({**base, "n_parent": 0, "n_selected": 0, "raw_p": 1.0, "selected_frequency": float("nan"),
                                     "standardized_uplift": float("nan"), "selected_effect": float("nan"), "bootstrap_ci_low": float("nan"),
                                     "bootstrap_ci_high": float("nan"), "uplift": float("nan"), "parent_effect": float("nan"),
                                     "parent_frequency": float("nan"), "retention_ratio": float("nan"), "not_evaluable": True, "target_sd": float("nan")})
                    continue
                model = fac().fit(X.iloc[train], y[train])
                score = model.predict(X.iloc[hidx])
                states = assign_state(score, thr)
                stats = evaluate_panel(y[hidx], states, etime[hidx].tz_convert("UTC").year.to_numpy(), week_key(etime[hidx], frozen.tz),
                                       ev_ns[hidx], wk["total"], bootstrap_reps=pol["bootstrap_repetitions"],
                                       permutation_reps=pol["permutation_repetitions"], seed=pol["seed"], ci_level=pol["ci_level"],
                                       min_events_year=frozen.acceptance["year_consistency"]["min_selected_events_for_eligible_year"])[state]
                raw_rows.append({**base, **{k: stats[k] for k in ("n_parent", "n_selected", "parent_frequency", "selected_frequency", "retention_ratio",
                                                                  "parent_effect", "selected_effect", "uplift", "standardized_uplift",
                                                                  "bootstrap_ci_low", "bootstrap_ci_high", "raw_p", "target_sd")}, "threshold": float(thr)})
                et_h = etime[hidx]
                sel = states == state
                series[(g, mname)] = {"week_keys": week_key(et_h, frozen.tz), "y": y[hidx], "selected": sel, "sign": 1.0 if state == "UPPER_HALF" else -1.0,
                                      "sd": float(stats["target_sd"]), "selected_ids": set(np.asarray(ids)[hidx][sel].tolist()),
                                      "months": pd.Series(et_h.tz_convert("UTC").strftime("%Y-%m")).to_numpy()}
    return raw_rows, series, (events, features, eligible)


def _month_table(ser: dict, min_events: int, by: str = "months") -> list[dict]:
    """Selected-event breakdown by calendar month (``by='months'``) or calendar year (``by='years'``); ``sample_ok`` flags >= min_events selected events."""
    out = []
    sel = ser["selected"]
    keys = ser["months"] if by == "months" else np.array([m[:4] for m in ser["months"]])
    for k in sorted(set(keys[sel].tolist())):
        m = sel & (keys == k)
        out.append({("month" if by == "months" else "year"): k, "n_selected": int(m.sum()), "mean_directional_effect": float(ser["sign"] * ser["y"][m].mean()),
                    "sample_ok": bool(m.sum() >= min_events)})
    return out


def execute_campaign_selection_holdout(ws: reg.Workspace, campaign_id: str, cap: dict, items: list, fingerprint: str, *, verbose: bool = True) -> dict:
    """Spend the campaign selection holdout (ledger first), evaluate every approved config x 3 models, correct for ALL of them jointly
    (BH + Bonferroni over the whole campaign family), record per-experiment reports and mark the campaign SELECTION_HOLDOUT_SPENT.

    ``items`` = [(experiment_id, approval, tables_callable, calendar_index, bars_or_None)]; the callable returns
    (events, features, eligible, targets) built from development + selection-holdout rows only."""
    frozen = load_frozen()
    log = (lambda *a: print(*a, flush=True)) if verbose else (lambda *a: None)
    c = reg.campaign_row(ws, campaign_id)
    parts = parse_partitions(reg.campaign_partitions(ws, campaign_id))
    cfg_ids = [cid for _, ap, *_ in items for cid in ap["approved_configs"]]
    assert_campaign_group_cap([{"experiment_id": e, "approved_configs": ap["approved_configs"]} for e, ap, *_ in items], frozen)
    # --- spend the holdout: ONE permanent ledger entry for the whole campaign, written BEFORE any holdout data is analysed
    reg.append_selection_holdout_access(ws, campaign_id=campaign_id, freeze_hash=c["selection_holdout_freeze_hash"], open_approval_file_hash=cap["_file_sha256"],
                                        experiments=";".join(it[0] for it in items), approved_experiment_groups=";".join(cfg_ids),
                                        n_holdout_evaluations=3 * len(cfg_ids), selection_holdout_start=f"{parts.development_end:%Y-%m-%d}",
                                        selection_holdout_end=f"{parts.selection_holdout_end:%Y-%m-%d}", unlock_timestamp=now_utc_iso(), code_hash=engine_code_hash())
    reg.update_campaign(ws, campaign_id, status="SELECTION_HOLDOUT_SPENT", selection_holdout_spent_at=now_utc_iso())
    log(f"[{campaign_id}] CAMPAIGN SELECTION HOLDOUT OPENED ONCE by human approval; ledger entry written; {len(cfg_ids)} frozen configs -> {3 * len(cfg_ids)} model evaluations")
    raw_rows: list[dict] = []
    extras: dict[str, tuple] = {}
    for e, ap, tables, cal, _bars in items:
        rows, series, tabs = _holdout_raw_rows(e, list(ap["_groups"]), tables, cal, parts, frozen)
        raw_rows += rows
        extras[e] = (series, tabs)
    rule = frozen.acceptance["selection_holdout_evidence"]
    conf = selection_holdout_evaluations(raw_rows, rule)                      # BH + Bonferroni over EVERY evaluation of the campaign
    m = len(conf)
    now = now_utc_iso()
    from engine import holdout_path as hp
    from engine.experiment_runner import _clean
    min_ev = frozen.acceptance["year_consistency"]["min_selected_events_for_eligible_year"]
    reports = {}
    for e, ap, _tables, cal, bars in items:
        mine = [r for r in conf if r["experiment_id"] == e]
        series, (events, features, eligible) = extras[e]
        verdicts = group_verdicts(mine, rule)
        reg.append_table(ws, "selection_holdout_trials.csv", reg.SELECTION_HOLDOUT_TRIAL_COLS, [{
            "campaign_id": campaign_id, "experiment_id": e, "selection_holdout_trial_id": f"{e}_HOLDOUT{i + 1:02d}",
            "group_id": r["group_id"], "target": r["target"], "state": r["state"], "model": r["model"], "n_parent_events": r["n_parent"],
            "n_selected_events": r["n_selected"], "parent_frequency": r["parent_frequency"], "selected_frequency": r["selected_frequency"],
            "retention_ratio": r["retention_ratio"], "parent_effect": r["parent_effect"], "selected_effect": r["selected_effect"],
            "uplift": r["uplift"], "standardized_uplift": r["standardized_uplift"], "bootstrap_ci_low": r["bootstrap_ci_low"],
            "bootstrap_ci_high": r["bootstrap_ci_high"], "raw_p": r["raw_p"], "selection_holdout_q": r["selection_holdout_q"],
            "selection_holdout_bonferroni_p": r["selection_holdout_bonferroni_p"],
            "selection_holdout_trials_in_family": r["selection_holdout_trials_in_family"], "gates_pass": r["gates_pass"],
            "decision": ("EVIDENCE_GATES_MET" if r["gates_pass"] else "EVIDENCE_GATES_NOT_MET"), "rejection_reason": r["rejection_reason"], "revealed_at": now}
            for i, r in enumerate(mine)])
        reg.set_status(ws, e, "SELECTION_HOLDOUT_SPENT", f"selection holdout opened once (family of {m}); awaiting the human's final configuration selection")
        ranks = next(x["is_ranks"] for x in json.load(open(freeze_path(ws, campaign_id)))["experiments"] if x["experiment_id"] == e)
        configs = []
        for cid_ in ap["approved_configs"]:
            _, g = nt.split_config_id(cid_)
            rows_g = [r for r in mine if r["group_id"] == g]
            configs.append({"config_id": cid_, "group_id": g, "is_rank": ranks[cid_], "model_rows": rows_g})
        pref = holdout_preference(
            [{"config_id": c_["config_id"], "is_rank": c_["is_rank"], "model_rows": c_["model_rows"]} for c_ in configs], frozen,
            series_of=lambda cid_, series=series: [(s["week_keys"], s["y"], s["selected"], s["sign"], s["sd"]) for (g, mm), s in sorted(series.items())
                                                   if g == nt.split_config_id(cid_)[1]])
        viable = [c_["config_id"] for c_ in pref["cards"] if c_["qualifies"]]           # minimum viability floor: the human may choose only among these
        no_final = not viable
        if no_final:
            reg.set_status(ws, e, "NO_FINAL_CONFIG", "no frozen config meets the minimum viability floor in the selection holdout: the experiment stops, CPCV never runs")
        ptxt, psha, pinfo = "", "", {"status": "NOT_COMPUTED_NO_BARS"}
        if bars is not None:
            sel_ids = {f"{c_['config_id']}|{r['model']}": series[(c_["group_id"], r["model"])]["selected_ids"] for c_ in configs for r in c_["model_rows"]
                       if (c_["group_id"], r["model"]) in series}
            prep = _clean(hp.holdout_path_diagnostics(bars, events, features, eligible, sel_ids, parts, frozen))
            if prep.get("status") == "COMPUTED":
                ptxt = json.dumps(prep, separators=(",", ":"), sort_keys=True)
                psha = hp.sha(ptxt)
                (experiment_dir(ws, e) / "results" / "SELECTION_HOLDOUT_PATH_DIAGNOSTICS.json").write_text(ptxt)
                pinfo = {"status": "COMPUTED", "file": "SELECTION_HOLDOUT_PATH_DIAGNOSTICS.json", "sha256": psha,
                         "per_config_model": {k: hp.compact(prep, k) for k in sel_ids}, "all_holdout_events": hp.compact(prep, "ALL_HOLDOUT_EVENTS"),
                         "label": prep["label"], "use_rule": prep["use_rule"], "cost_banner": prep["cost_banner"], "selection_banner": prep["selection_banner"]}
            else:
                pinfo = {"status": prep.get("status", "NOT_COMPUTED")}
        d = experiment_dir(ws, e)
        report = {"experiment_id": e, "campaign_id": campaign_id, "status": "NO_FINAL_CONFIG" if no_final else "SELECTION_HOLDOUT_SPENT", "label": HOLDOUT_BANNER,
                  "viable_configs": viable, "no_final_config": no_final,
                  "viability_floor": "selected effect > 0, selected frequency >= 1.0/week, positive uplift in >= 2 of 3 models (no human override)",
                  "is_independent_confirmation": False, "approved_configs": list(ap["approved_configs"]), "near_tie_cluster_id": ap["near_tie_cluster_id"],
                  "selection_holdout_period": [f"{parts.development_end:%Y-%m-%d}", f"{parts.selection_holdout_end:%Y-%m-%d}"],
                  "selection_holdout_years": parts.selection_holdout_years, "selection_holdout_bars_fingerprint": fingerprint,
                  "holdout_model_evaluations": 3 * len(configs), "family_size_for_multiple_testing": m,
                  "campaign_experiments_in_family": [x[0] for x in items], "scope_of_multiplicity": "ENTIRE CAMPAIGN",
                  "formulas": {"selection_holdout_bonferroni_p": f"min(raw_p * {m}, 1)", "selection_holdout_q": f"BH over all {m} approved config x model evaluations of the campaign"},
                  "evidence_gate_verdicts": verdicts, "evaluations": mine, "selection_holdout_weeks": mine[0]["selection_holdout_weeks"] if mine else 0,
                  "preference": pref, "path_diagnostics": pinfo,
                  "by_month": {f"{g}|{mm}": _month_table(s, min_ev) for (g, mm), s in sorted(series.items())},
                  "by_year": {f"{g}|{mm}": _month_table(s, min_ev, "years") for (g, mm), s in sorted(series.items())},
                  "campaign_selection_holdout_opened_once": True, "campaign_freeze_sha256": c["selection_holdout_freeze_hash"],
                  "open_approval_file_sha256": cap["_file_sha256"], "approval_file_sha256": ap["_approval_file_sha256"],
                  "is_report_sha256": ap["is_report_sha256"], "manifest_sha256": sha256_file(d / MANIFEST),
                  "next_step": "The HUMAN writes approvals/<EXP>_FINAL_CONFIG_SELECTION.yaml choosing exactly ONE of the frozen configs (or DECLINE). "
                               "No new config, threshold, bracket or model parameter may be introduced from these diagnostics.",
                  "note": "The selection holdout is spent: it influenced configuration choice, so it is NOT independent evidence. "
                          "Only the untouched final lockbox may be called confirmation."}
        (d / "results" / "SELECTION_HOLDOUT_REPORT.json").write_text(json.dumps(_clean(report), indent=2, sort_keys=True))
        (d / "results" / "SELECTION_HOLDOUT_REPORT.md").write_text(_holdout_md(_clean(report)))
        reports[e] = report
        log(f"[{e}] selection holdout evaluated; preference: {pref['status']} {pref.get('holdout_preferred_config') or ''}")
    camp_report = {"campaign_id": campaign_id, "campaign_status": "SELECTION_HOLDOUT_SPENT", "family_size": m, "label": HOLDOUT_BANNER,
                   "experiments": {e: r["preference"]["status"] for e, r in reports.items()},
                   "evaluations": [{k: r[k] for k in ("experiment_id", "group_id", "model", "raw_p", "selection_holdout_q", "selection_holdout_bonferroni_p", "gates_pass")} for r in conf],
                   "freeze_sha256": c["selection_holdout_freeze_hash"], "selection_holdout_bars_fingerprint": fingerprint}
    (ws.root / "registry" / f"selection_holdout_campaign_report_{campaign_id}.json").write_text(json.dumps(_clean(camp_report), indent=2, sort_keys=True))
    return {**camp_report, "reports": reports}


def _holdout_md(r: dict) -> str:
    f = lambda c, k, fmt="{:+.5f}": ("n/a" if c.get(k) is None else fmt.format(c[k]))  # noqa: E731
    L = [f"# SELECTION HOLDOUT REPORT — {r['experiment_id']}", "", f"**{r['label']}**", "",
         f"Campaign-level selection holdout {r['selection_holdout_period'][0]} … {r['selection_holdout_period'][1]} ({r['selection_holdout_years']} calendar year(s)); the final lockbox was not read. "
         f"Configs frozen BEFORE opening (near-tie cluster {r['near_tie_cluster_id']}): {', '.join(r['approved_configs'])}.", "",
         f"This experiment's model evaluations: {r['holdout_model_evaluations']}. The multiple-testing family is the ENTIRE CAMPAIGN "
         f"({', '.join(r['campaign_experiments_in_family'])}): {r['family_size_for_multiple_testing']} evaluations: `{r['formulas']['selection_holdout_bonferroni_p']}`; "
         f"`{r['formulas']['selection_holdout_q']}`. All evaluations are listed, not only winners. These are selection-holdout evidence values, NOT confirmation p-values.", "",
         "| config | model | N sel | sel f/wk | parent effect | selected effect | uplift | std uplift | CI low | raw p | holdout BH q | holdout Bonferroni p | evidence gates (informational) | reason |",
         "|" + "---|" * 14]
    for c in r["evaluations"]:
        cid = f"{r['experiment_id']}|{c['group_id']}"
        L.append(f"| {cid} | {c['model']} | {c['n_selected']} | {f(c, 'selected_frequency', '{:.2f}')} | {f(c, 'parent_effect')} | {f(c, 'selected_effect')} | {f(c, 'uplift')} | "
                 f"{f(c, 'standardized_uplift', '{:+.3f}')} | {f(c, 'bootstrap_ci_low')} | {f(c, 'raw_p', '{:.4f}')} | {f(c, 'selection_holdout_q', '{:.4f}')} | "
                 f"{f(c, 'selection_holdout_bonferroni_p', '{:.4f}')} | {c['gates_pass']} | {c['rejection_reason'] or '-'} |")
    p = r["preference"]
    L += ["", "## Minimum viability floor (no human override)", "",
          "A config may be chosen as the final config only if: selected effect > 0, selected frequency >= 1.0/week and positive uplift in >= 2 of 3 models.",
          f"Viable configs: {', '.join(r['viable_configs']) or '**none -> NO_FINAL_CONFIG: the experiment stops, CPCV does not run**'}", ""]
    L += ["", "## Deterministic holdout preference (ADVISORY — the human decides)", "",
          f"**{p['status']}**" + (f": `{p['holdout_preferred_config']}`" if p.get("holdout_preferred_config") else ""), "", p["note"], ""]
    if p.get("ranking_leader_advisory"):
        L.append(f"Ranking leader (not a winner): `{p['ranking_leader_advisory']}`\n")
    L.append("| config | frozen IS rank | qualifies | median std uplift | median selected effect | median f/wk | why not |")
    L.append("|---|---|---|---|---|---|---|")
    for c in p["cards"]:
        L.append(f"| {c['config_id']} | {c['is_rank']} | {c['qualifies']} | {c['median_standardized_uplift']:+.3f} | {c['median_selected_effect']:+.5f} | "
                 f"{c['median_selected_frequency']:.2f} | {'; '.join(c['disqualified_because']) or '-'} |")
    if p.get("pair_test"):
        L.append(f"\nPaired test of the top two: {p['pair_test']}\n")
    L += ["", "## Evidence-gate verdicts (informational; >= 2 of 3 models)", ""]
    for g, v in r["evidence_gate_verdicts"].items():
        L.append(f"* {g}: evidence gates {'MET' if v['evidence_gates_met'] else 'NOT MET'} ({v['models_passing']}/3: {', '.join(v['models']) or '-'})")
    L += ["", "## Path / bracket diagnostics of the holdout (SELECTION DATA)", ""]
    pi = r["path_diagnostics"]
    if pi.get("status") != "COMPUTED":
        L.append(f"_not computed ({pi.get('status')})_")
    else:
        L += [f"{pi['label']}. {pi['use_rule']}. {pi['cost_banner']}; {pi['selection_banner']}. Full detail: `results/{pi['file']}` (sha256 `{pi['sha256']}`).", "",
              "| config | model | N selected | continuation@60 | reversal@60 | median MFE pts@60 | median abs MAE pts@60 | bracket cells with positive mean gross |", "|---|---|---|---|---|---|---|---|"]
        for k, v in sorted(pi["per_config_model"].items()):
            if v:
                co, re_ = v["continuation_60"], v["reversal_60"]
                L.append(f"| {k.rsplit('|', 1)[0]} | {k.rsplit('|', 1)[1]} | {v['n_events']} | {co['n']}/{co['denominator']} | {re_['n']}/{re_['denominator']} | "
                         f"{v['median_MFE_points_60']} | {v['median_abs_MAE_points_60']} | {v['bracket_cells_positive_mean_gross']}/{v['bracket_cells']} |")
    L += ["", "## Year / month breakdown of selected events (years/months with >= 20 selected events shown)", ""]
    for k, rows in r["by_year"].items():
        ok = [x for x in rows if x["sample_ok"]]
        if ok:
            L.append(f"* {k} by year: " + "; ".join(f"{x['year']} n={x['n_selected']} effect {x['mean_directional_effect']:+.5f}" for x in ok))
    for k, rows in r["by_month"].items():
        ok = [x for x in rows if x["sample_ok"]]
        if ok:
            L.append(f"* {k}: " + "; ".join(f"{x['month']} n={x['n_selected']} effect {x['mean_directional_effect']:+.5f}" for x in ok))
    L += ["", f"**{r['label']}**", "", r["next_step"], "", r["note"], ""]
    return "\n".join(L)


# ---------------------------------------------------------------------------- final human configuration selection
def validate_final_selection(ws: reg.Workspace, experiment_id: str, frozen: Frozen | None = None) -> dict:
    """Validate approvals/<EXP>_FINAL_CONFIG_SELECTION.yaml. Returns an info dict; does NOT change any state."""
    frozen = frozen or load_frozen()
    exp = reg.experiment_row(ws, experiment_id)
    st = exp["status"]
    if reg.final_config_of(ws, experiment_id) is not None:
        raise ApprovalError(f"{experiment_id} already froze its final configuration; it can never be replaced and there is no fallback to a runner-up")
    if st == "SELECTION_HOLDOUT_CONTAMINATED":
        raise SelectionHoldoutContaminated(f"{experiment_id} is SELECTION_HOLDOUT_CONTAMINATED")
    if st == "NO_FINAL_CONFIG":
        raise ApprovalError(f"{experiment_id} is NO_FINAL_CONFIG: no frozen config met the minimum viability floor in the selection holdout; the experiment stopped and the human cannot override this")
    if st == "SELECTION_HOLDOUT_FROZEN":
        raise ApprovalError(f"{experiment_id}'s configs are frozen for the selection holdout: open the campaign holdout first (or decline); the holdout cannot be skipped after the freeze")
    if st not in PENDING_FINAL + ("SELECTION_HOLDOUT_SPENT",):
        raise ApprovalError(f"{experiment_id} is {st}: a final configuration can only be chosen from {PENDING_FINAL + ('SELECTION_HOLDOUT_SPENT',)}")
    p = final_selection_path(ws, experiment_id)
    if not p.exists():
        raise ApprovalError(f"no human final-configuration selection file: {p}. The engine never writes it and does not choose for you.")
    sel = yaml.safe_load(p.read_text())
    if not isinstance(sel, dict) or any(k not in sel for k in FINAL_KEYS):
        raise ApprovalError(f"selection file must contain the keys {FINAL_KEYS}")
    errs: list[str] = []
    if sel["experiment_id"] != experiment_id:
        errs.append("experiment_id mismatch")
    if sel["campaign_id"] != exp["campaign_id"]:
        errs.append("campaign_id mismatch")
    if sel["selected_by"] != APPROVER:
        errs.append(f"selected_by must be exactly {APPROVER}")
    if not (isinstance(sel["selection_note"], str) and sel["selection_note"].strip()):
        errs.append("selection_note must be non-empty")
    # the IS report is sealed once the campaign is frozen; its file hash still binds the selection
    d = experiment_dir(ws, experiment_id)
    mv = verify_manifest(ws, experiment_id, raise_on_error=False)
    errs += [f"experiment changed since freeze: {e}" for e in mv["errors"]]
    if sel["manifest_sha256"] != sha256_file(d / MANIFEST):
        errs.append("manifest_sha256 does not match the exact frozen manifest")
    rep = d / "results" / "IS_REPORT.json"
    if sel["is_report_sha256"] != sha256_file(rep):
        errs.append("is_report_sha256 does not match the exact IS_REPORT.json")
    cfg = sel["selected_config_id"]
    if cfg == DECLINE:
        if errs:
            raise ApprovalError("; ".join(errs))
        return {"decline": True, "experiment_id": experiment_id, "file_sha256": sha256_file(p), "status": st}
    if not isinstance(cfg, str) or "|" not in cfg:
        errs.append("selected_config_id must be exactly ONE config id '<experiment>|<TARGET>|<STATE>' (or DECLINE)")
        raise ApprovalError("; ".join(errs))
    e_, group = nt.split_config_id(cfg)
    if e_ != experiment_id:
        errs.append(f"{cfg} belongs to another experiment")
    J = json.loads(rep.read_text())
    eligible = [g["group_id"] for g in J["I_top_configurations"]["top_groups"]]
    used = st == "SELECTION_HOLDOUT_SPENT"
    holdout_rank = ""
    if used:
        hrep = holdout_report_path(ws, experiment_id)
        if not hrep.exists():
            errs.append("SELECTION_HOLDOUT_REPORT.json is missing")
        else:
            if sel["selection_holdout_report_sha256"] != sha256_file(hrep):
                errs.append("selection_holdout_report_sha256 does not match the exact selection-holdout report the human saw")
            H = json.loads(hrep.read_text())
            if cfg not in H["approved_configs"]:
                errs.append(f"{cfg} was not evaluated in the selection holdout (frozen configs: {H['approved_configs']}); the human may only choose among configs frozen before opening")
            frz = json.loads(freeze_path(ws, exp["campaign_id"]).read_text())
            if cfg not in next((x["approved_configs"] for x in frz["experiments"] if x["experiment_id"] == experiment_id), []):
                errs.append(f"{cfg} is not in the campaign freeze record")
            card = next((c_ for c_ in H["preference"]["cards"] if c_["config_id"] == cfg), None)
            if card is None or not card["qualifies"]:
                errs.append(f"{cfg} fails the minimum viability floor in the selection holdout ({'; '.join(card['disqualified_because']) if card else 'not evaluated'}); it cannot be selected and the human cannot override this")
            rk = H["preference"].get("ranking", [])
            holdout_rank = str(rk.index(cfg) + 1) if cfg in rk else "not qualifying"
    else:
        if sel["selection_holdout_report_sha256"] not in (None, "", "SKIPPED"):
            errs.append("the selection holdout was not used for this experiment: selection_holdout_report_sha256 must be null (direct IS selection)")
        if group not in eligible:
            errs.append(f"{cfg} is not in the deterministic IS-eligible list {eligible}")
    if group in eligible:
        _verified(ws, experiment_id, group, frozen, errs)                     # all 3 model paths of the chosen config must be strong-mode verified
    if errs:
        raise ApprovalError("; ".join(errs))
    clusters = J.get("NT_configuration_uncertainty", {}).get("clusters", [])
    cl = next((c["cluster_id"] for c in clusters if cfg in c["members"]), "")
    is_rank = next(g["rank"] for g in J["I_top_configurations"]["top_groups"] if g["group_id"] == group) if group in eligible else ""
    return {"decline": False, "experiment_id": experiment_id, "selected_config_id": cfg, "group_id": group, "holdout_used": used, "holdout_rank": holdout_rank,
            "is_rank": is_rank, "near_tie_cluster": cl, "file_sha256": sha256_file(p), "status": st}


def freeze_final_config(ws: reg.Workspace, experiment_id: str, frozen: Frozen | None = None) -> dict:
    """Accept the human's final-configuration file: SELECTION_HOLDOUT_SKIPPED (if applicable) -> FINAL_CONFIG_FROZEN, ledger row appended.
    CPCV then runs automatically (engine/cpcv.py). DECLINE -> HUMAN_DECLINED (no CPCV, no lockbox)."""
    info = validate_final_selection(ws, experiment_id, frozen)
    d = experiment_dir(ws, experiment_id)
    if info["decline"]:
        reg.set_status(ws, experiment_id, "HUMAN_DECLINED", "the human declined to choose a final configuration")
        return info
    if not info["holdout_used"]:
        reg.set_status(ws, experiment_id, "SELECTION_HOLDOUT_SKIPPED", "the human chose one IS-eligible config directly; the selection holdout stays unread")
    reg.append_final_config(ws, campaign_id=reg.experiment_row(ws, experiment_id)["campaign_id"], experiment_id=experiment_id, event="FINAL_CONFIG_FROZEN",
                            selected_config_id=info["selected_config_id"], is_rank=info["is_rank"], near_tie_cluster=info["near_tie_cluster"],
                            selection_holdout_used="yes" if info["holdout_used"] else "no", selection_holdout_rank=info["holdout_rank"],
                            human_selection_file_hash=info["file_sha256"], manifest_hash=sha256_file(d / MANIFEST), frozen_at=now_utc_iso(), cpcv_status="PENDING")
    reg.set_status(ws, experiment_id, "FINAL_CONFIG_FROZEN", f"final config {info['selected_config_id']} frozen by the human; fixed CPCV runs next with no further approval")
    return info
