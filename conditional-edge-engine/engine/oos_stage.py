"""CAMPAIGN-LEVEL one-shot CONFIRMATION OOS behind manual HUMAN approvals.

Process (nothing in this module creates a human file):
  1. every experiment of the campaign finishes its IS stage (no DRAFT / FROZEN experiment may remain);
  2. the human writes approvals/EXP_xxxx_OOS_APPROVAL.yaml for the experiments/groups he wants confirmed (<= 2 groups each);
  3. ``freeze_campaign_oos`` CLOSES the campaign (no new experiments, verification or IS reports), re-validates every approval
     and records all approved experiment/group pairs together with their hashes in one freeze document;
  4. the human writes approvals/CAMPAIGN_xxxx_OOS_OPEN_APPROVAL.yaml citing the exact freeze hash;
  5. ``run_campaign_oos`` opens the shared OOS partition EXACTLY ONCE for the whole campaign: the ledger row ("CAMPAIGN OOS HAS
     BEEN SPENT") is written BEFORE any OOS data is touched; BH and Bonferroni run across every 3 x approved_group model
     confirmation of the entire campaign; per-experiment OOS reports and statuses are preserved.
Bars at/after oos_end (final lockbox) are removed before any computation. A spent campaign accepts no new experiment, and no
campaign whose OOS interval overlaps a spent OOS partition can claim it as untouched confirmation.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from engine import trial_registry as reg
from engine.acceptance import SHORTLIST, path_verification
from engine.common import EngineError, Frozen, engine_code_hash, load_frozen, model_names, now_utc_iso, sha256_file, utc_ns
from engine.event_contract import load_event_module, load_spec
from engine.experiment_lifecycle import MANIFEST, experiment_dir, verify_manifest
from engine.experiment_runner import bars_fingerprint, build_event_tables
from engine.model_engine import make_model_factory
from engine.multiplicity import benjamini_hochberg
from engine.partitions import oos_view, parse_partitions
from engine.score_calibration import UPPER, WFConfig, assign_state, calibrate_threshold
from engine.statistics import evaluate_panel, week_key, weeks_in_intervals

APPROVER = "HUMAN_USER"
CAMPAIGN_APPROVAL_KEYS = ["campaign_id", "oos_freeze_sha256", "approved_by", "approved", "approval_note"]
APPROVAL_KEYS = ["experiment_id", "campaign_id", "experiment_manifest_sha256", "is_report_sha256", "approved_by", "approved",
                 "approved_target_side_groups", "approval_note"]


class ApprovalError(EngineError):
    pass


OOSContaminated = reg.OOSContaminated


def approval_path(ws: reg.Workspace, experiment_id: str) -> Path:
    return ws.approvals / f"{experiment_id}_OOS_APPROVAL.yaml"


def approval_hashes(ws: reg.Workspace, experiment_id: str) -> dict:
    """Read-only helper for the HUMAN: the exact hashes an approval file must reference."""
    d = experiment_dir(ws, experiment_id)
    rep = d / "results" / "IS_REPORT.json"
    out = {"experiment_manifest_sha256": sha256_file(d / MANIFEST),
           "is_report_sha256": sha256_file(rep) if rep.exists() else None}
    if rep.exists():
        out["allowed_target_side_groups"] = [g["group_id"] for g in json.loads(rep.read_text())["I_top_configurations"]["top_groups"]]
    return out


def mark_contamination_if_mutated(ws: reg.Workspace, experiment_id: str) -> bool:
    """If OOS was spent and the frozen experiment was changed afterwards, mark it OOS_CONTAMINATED permanently."""
    if not reg.oos_spent(ws, experiment_id):
        return False
    errs = verify_manifest(ws, experiment_id, raise_on_error=False)["errors"]
    if errs:
        reg.set_status(ws, experiment_id, "OOS_CONTAMINATED", "frozen experiment changed after OOS was spent: " + "; ".join(errs[:3]))
        return True
    return False


def campaign_approval_path(ws: reg.Workspace, campaign_id: str) -> Path:
    return ws.approvals / f"CAMPAIGN_{campaign_id}_OOS_OPEN_APPROVAL.yaml"


def freeze_path(ws: reg.Workspace, campaign_id: str) -> Path:
    return ws.root / "registry" / f"oos_freeze_{campaign_id}.json"


def validate_approval(ws: reg.Workspace, experiment_id: str, frozen: Frozen | None = None, *, campaign_frozen: bool = False) -> dict:
    """Validate the human's per-experiment approval. ``campaign_frozen=True`` is used when re-validating at campaign open."""
    frozen = frozen or load_frozen()
    exp = reg.experiment_row(ws, experiment_id)
    if exp["status"] == "OOS_CONTAMINATED":
        raise OOSContaminated(f"{experiment_id} is OOS_CONTAMINATED")
    cid = exp["campaign_id"]
    if reg.campaign_oos_spent(ws, cid):
        raise OOSContaminated(f"CAMPAIGN OOS HAS BEEN SPENT ({cid}); {experiment_id} cannot claim the shared OOS partition as untouched confirmation")
    if not campaign_frozen:
        reg.assert_campaign_open(ws, cid, f"approve OOS for {experiment_id}")
    reg.assert_oos_partition_untouched(ws, reg.campaign_partitions(ws, cid), exclude_campaign=cid)
    p = approval_path(ws, experiment_id)
    if not p.exists():
        raise ApprovalError(f"no human approval file: {p}. OOS stays sealed. (The approval must be written by the human; "
                            f"no script or LLM creates it. Hashes to reference: scripts/show_approval_hashes.py)")
    ap = yaml.safe_load(p.read_text())
    if not isinstance(ap, dict) or any(k not in ap for k in APPROVAL_KEYS):
        raise ApprovalError(f"approval file must contain exactly the keys {APPROVAL_KEYS}")
    errs: list[str] = []
    if ap["experiment_id"] != experiment_id:
        errs.append("experiment_id mismatch")
    if ap["campaign_id"] != exp["campaign_id"]:
        errs.append("campaign_id mismatch")
    if ap["approved_by"] != APPROVER:
        errs.append(f"approved_by must be exactly {APPROVER}")
    if ap["approved"] is not True:
        if ap["approved"] is False:
            reg.set_status(ws, experiment_id, "OOS_NOT_APPROVED", "human declined OOS (approved: false)")
            raise ApprovalError(f"{experiment_id}: the human did not approve OOS (OOS_NOT_APPROVED)")
        errs.append("approved must be the boolean true")
    if not (isinstance(ap["approval_note"], str) and ap["approval_note"].strip()):
        errs.append("approval_note must be non-empty")
    d = experiment_dir(ws, experiment_id)
    mv = verify_manifest(ws, experiment_id, raise_on_error=False)
    errs += [f"experiment changed since freeze (approval invalidated): {e}" for e in mv["errors"]]
    if ap["experiment_manifest_sha256"] != sha256_file(d / MANIFEST):
        errs.append("experiment_manifest_sha256 does not match the exact frozen manifest (wrong or stale approval)")
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
    if exp["is_report_sha256"] and exp["is_report_sha256"] != sha256_file(rep):
        errs.append("IS_REPORT.json differs from the registry")
    groups = ap["approved_target_side_groups"]
    mx = frozen.trial_policy["oos"]["max_target_side_groups"]
    if not (isinstance(groups, list) and groups and all(isinstance(g, str) for g in groups)):
        errs.append("approved_target_side_groups must be a non-empty list of 'TARGET|STATE' ids")
    else:
        if len(groups) > mx:
            errs.append(f"{len(groups)} target/side groups approved; MAX_OOS_TARGET_SIDE_GROUPS = {mx}")
        if len(set(groups)) != len(groups):
            errs.append("duplicate approved groups")
        allowed = {g["group_id"] for g in J["I_top_configurations"]["top_groups"]}
        for g in groups:
            if g not in allowed:
                errs.append(f"{g} is not in the frozen IS shortlist (top groups: {sorted(allowed)})")
    if errs:
        raise ApprovalError("; ".join(errs))
    # re-derive eligibility under the CURRENT campaign universe (campaign values are retroactive)
    if exp["status"] != "AWAITING_HUMAN_OOS_APPROVAL":
        raise ApprovalError(f"{experiment_id} is {exp['status']}, not AWAITING_HUMAN_OOS_APPROVAL (it may have lost IS eligibility "
                            f"as the campaign universe grew); OOS stays sealed")
    trials = reg.experiment_trials(ws, experiment_id)
    ver = json.loads(exp["verification_json"] or "{}")
    for g in groups:
        t, s = g.split("|")
        rows = trials[(trials["target"] == t) & (trials["state"] == s)].to_dict("records")
        if sum(1 for r in rows if r["decision"] == SHORTLIST) < frozen.acceptance["model_agreement"]["min_models_passing"]:
            errs.append(f"{g} is no longer IS_SHORTLIST_ELIGIBLE under the current campaign universe")
        for r in rows:
            if path_verification(ver, r, frozen.acceptance) != "PASS":
                errs.append(f"model path {r['target']}|{r['model']} is not externally verified (strong mode, research families PASS); "
                            f"all 3 models of an approved group must be verified")
    if errs:
        raise ApprovalError("; ".join(errs))
    ap["_approval_file_sha256"] = sha256_file(p)
    ap["_is_report"] = J
    return ap


def _oos_gate(row: dict, rule: dict) -> tuple[bool, str]:
    why = []
    if not row["n_selected"] > 0 or any(np.isnan(row[k]) for k in ("selected_frequency", "standardized_uplift", "selected_effect", "bootstrap_ci_low")):
        return False, "NOT_EVALUABLE: no selected OOS events"
    if row["selected_frequency"] < rule["min_selected_frequency_per_week"]:
        why.append(f"selected frequency {row['selected_frequency']:.3f}/week < {rule['min_selected_frequency_per_week']}")
    if row["standardized_uplift"] < rule["min_standardized_uplift"]:
        why.append(f"standardized uplift {row['standardized_uplift']:.3f} < {rule['min_standardized_uplift']}")
    if not row["selected_effect"] > rule["selected_effect_must_exceed"]:
        why.append(f"selected effect {row['selected_effect']:+.5f} <= 0")
    if not row["bootstrap_ci_low"] > rule["bootstrap_ci_lower_bound_must_exceed"]:
        why.append(f"CI lower bound {row['bootstrap_ci_low']:.5f} <= 0")
    if row["oos_q"] > rule["max_oos_bh_q"]:
        why.append(f"OOS BH q {row['oos_q']:.4f} > {rule['max_oos_bh_q']}")
    if row["oos_bonferroni_p"] > rule["max_oos_bonferroni_p"]:
        why.append(f"OOS Bonferroni p {row['oos_bonferroni_p']:.4f} > {rule['max_oos_bonferroni_p']}")
    return (not why), "; ".join(why)


def oos_confirmations(rows: list[dict], rule: dict) -> list[dict]:
    """Add OOS BH q and OOS Bonferroni p across ALL 3G approved model confirmations (never only winners), then gate each."""
    m = len(rows)
    p = np.array([r["raw_p"] for r in rows], dtype=float)
    q = benjamini_hochberg(p)
    out = []
    for r, qi, pi in zip(rows, q, p):
        r = dict(r, oos_q=float(qi), oos_bonferroni_p=float(min(pi * m, 1.0)), oos_trials_in_family=m)
        r["gates_pass"], r["rejection_reason"] = _oos_gate(r, rule)
        out.append(r)
    return out


def group_verdicts(rows: list[dict], rule: dict) -> dict[str, dict]:
    """Target/side confirmation needs >= 2 of 3 models to satisfy the frozen OOS gates."""
    verdicts = {}
    for gid in sorted({r["group_id"] for r in rows}):
        g = [r for r in rows if r["group_id"] == gid]
        npass = sum(1 for r in g if r["gates_pass"])
        verdicts[gid] = {"models_passing": npass, "models": sorted(r["model"] for r in g if r["gates_pass"]),
                         "confirmed": npass >= rule["min_models_passing"]}
    return verdicts


# ---------------------------------------------------------------------------- campaign freeze (closes the campaign)
def freeze_campaign_oos(ws: reg.Workspace, campaign_id: str, frozen: Frozen | None = None) -> dict:
    """HUMAN-run step: close the campaign and freeze every approved experiment/group pair together.

    Requires every experiment of the campaign to have finished its IS stage. Experiments awaiting approval without a (positive)
    human approval file are set to OOS_NOT_APPROVED. Any INVALID approval file aborts the freeze with nothing changed."""
    frozen = frozen or load_frozen()
    reg.assert_campaign_open(ws, campaign_id, "freeze its OOS")
    parts = reg.campaign_partitions(ws, campaign_id)
    reg.assert_oos_partition_untouched(ws, parts, exclude_campaign=campaign_id)
    exps = reg.read_experiments(ws)
    exps = exps[exps["campaign_id"] == campaign_id]
    if exps.empty:
        raise EngineError(f"campaign {campaign_id} has no experiments")
    incomplete = sorted(exps[exps["status"].isin(["DRAFT", "FROZEN"])]["experiment_id"])
    if incomplete:
        raise EngineError(f"campaign {campaign_id} IS stage is incomplete: {incomplete} have not completed their IS run. "
                          f"ALL IS experiments must be completed before the confirmation OOS can be frozen or opened")
    included, excluded, to_decline = [], {}, []
    for e, st in zip(exps["experiment_id"], exps["status"]):
        if st != "AWAITING_HUMAN_OOS_APPROVAL":
            excluded[e] = st
            continue
        p = approval_path(ws, e)
        raw = yaml.safe_load(p.read_text()) if p.exists() else None
        if raw is None:
            excluded[e] = "NO_HUMAN_APPROVAL"
            to_decline.append(e)
        elif isinstance(raw, dict) and raw.get("approved") is False:
            excluded[e] = "HUMAN_DECLINED"
            to_decline.append(e)
        else:
            ap = validate_approval(ws, e, frozen)                      # raises on any problem: nothing is changed
            d = experiment_dir(ws, e)
            included.append({"experiment_id": e, "approved_target_side_groups": list(ap["approved_target_side_groups"]),
                             "experiment_manifest_sha256": sha256_file(d / MANIFEST), "is_report_sha256": ap["is_report_sha256"],
                             "approval_file_sha256": ap["_approval_file_sha256"],
                             "verification_hash": hashlib.sha256((reg.experiment_row(ws, e)["verification_json"] or "{}").encode()).hexdigest()})
    if not included:
        raise EngineError(f"nothing to freeze for {campaign_id}: no experiment has a valid positive human approval")
    n_groups = sum(len(i["approved_target_side_groups"]) for i in included)
    doc = {"campaign_id": campaign_id, "partitions": parts, "frozen_at": now_utc_iso(), "experiments": included,
           "experiments_not_included": excluded, "n_approved_groups": n_groups,
           "n_oos_confirmations": 3 * n_groups, "code_hash": engine_code_hash(),
           "note": "Campaign closed. Every approved group of every experiment is confirmed together in ONE OOS opening; "
                   "BH and Bonferroni run over all n_oos_confirmations = 3 x n_approved_groups."}
    path = freeze_path(ws, campaign_id)
    path.write_text(json.dumps(doc, indent=2, sort_keys=True))
    h = sha256_file(path)
    for e in to_decline:
        reg.set_status(ws, e, "OOS_NOT_APPROVED", f"not included in the campaign OOS freeze ({excluded[e]})")
    reg.update_campaign(ws, campaign_id, status="OOS_FROZEN", oos_freeze_hash=h)
    return {**doc, "freeze_sha256": h, "path": str(path)}


def campaign_open_hashes(ws: reg.Workspace, campaign_id: str) -> dict:
    """Read-only helper for the HUMAN: what the campaign-open approval must cite."""
    c = reg.campaign_row(ws, campaign_id)
    return {"campaign_id": campaign_id, "campaign_status": c["status"], "oos_freeze_sha256": c["oos_freeze_hash"] or None,
            "freeze_file": str(freeze_path(ws, campaign_id))}


def validate_campaign_open(ws: reg.Workspace, campaign_id: str, frozen: Frozen | None = None) -> tuple[dict, dict, dict]:
    """Everything that must hold before the shared OOS partition may be opened (once) for the campaign."""
    frozen = frozen or load_frozen()
    c = reg.campaign_row(ws, campaign_id)
    if c["status"] == "OOS_SPENT" or reg.campaign_oos_spent(ws, campaign_id):
        raise OOSContaminated(f"CAMPAIGN OOS HAS BEEN SPENT ({campaign_id}); it can never be opened again")
    if c["status"] != "OOS_FROZEN":
        raise ApprovalError(f"campaign {campaign_id} is {c['status']}; its OOS must first be frozen with scripts/freeze_campaign_oos.py")
    reg.assert_oos_partition_untouched(ws, reg.campaign_partitions(ws, campaign_id), exclude_campaign=campaign_id)
    fp = freeze_path(ws, campaign_id)
    if not fp.exists() or sha256_file(fp) != c["oos_freeze_hash"]:
        raise ApprovalError("the campaign OOS freeze document is missing or was edited after the freeze")
    doc = json.loads(fp.read_text())
    p = campaign_approval_path(ws, campaign_id)
    if not p.exists():
        raise ApprovalError(f"no human campaign-open approval file: {p}. The shared OOS stays sealed. (Written by the human only; "
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
    if cap["oos_freeze_sha256"] != c["oos_freeze_hash"]:
        errs.append("oos_freeze_sha256 does not match the exact campaign freeze document")
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
                     ("approved_target_side_groups", list(ap["approved_target_side_groups"]))):
            if ent[k] != v:
                raise ApprovalError(f"{e}: {k} changed since the campaign freeze")
        if ent["experiment_manifest_sha256"] != sha256_file(experiment_dir(ws, e) / MANIFEST):
            raise ApprovalError(f"{e}: manifest changed since the campaign freeze")
        aps[e] = ap
    return doc, cap, aps


def run_campaign_oos(ws: reg.Workspace, campaign_id: str, bars: pd.DataFrame, *, verbose: bool = True) -> dict:
    """Open the campaign's shared confirmation OOS ONCE (ledger first). ``bars`` may extend past oos_end: that is cut first."""
    frozen = load_frozen()
    doc, cap, aps = validate_campaign_open(ws, campaign_id, frozen)
    parts = parse_partitions(reg.campaign_partitions(ws, campaign_id))
    bars_oos = oos_view(bars, parts)                                # final lockbox removed BEFORE any computation
    del bars
    assert bars_oos.index.tz_convert("UTC").max() < parts.oos_end
    items = []
    for e, ap in aps.items():
        d = experiment_dir(ws, e)
        spec = load_spec(d / "EVENT_SPEC.yaml")
        module = load_event_module(d / "event.py")
        items.append((e, ap, (lambda module=module, spec=spec: build_event_tables(module, spec, bars_oos, frozen)[:4]), bars_oos.index))
    fp = bars_fingerprint(bars_oos[bars_oos.index.tz_convert("UTC") >= parts.development_end])
    return execute_campaign_oos(ws, campaign_id, cap, items, fp, verbose=verbose)


def _oos_raw_rows(experiment_id: str, groups: list[str], tables, calendar_index: pd.DatetimeIndex, parts, frozen: Frozen) -> list[dict]:
    """3 x G raw OOS model results of ONE experiment (no multiplicity correction yet)."""
    cfg = WFConfig.from_policy(frozen.trial_policy)
    pol = frozen.trial_policy
    from engine.feature_engine import feature_names
    names = feature_names(frozen)
    dev_end_ns = int(parts.development_end.value)
    oos_end_ns = int(parts.oos_end.value)
    events, features, eligible, targets = tables()
    ev = events.assign(_el=np.asarray(eligible, dtype=bool))
    ev = ev[ev["_el"]].sort_values(["event_time", "event_id"], kind="stable").reset_index(drop=True)
    feat = features.set_index("event_id")
    wk = weeks_in_intervals(calendar_index, [(dev_end_ns, oos_end_ns)], frozen.tz)
    raw_rows: list[dict] = []
    for t in sorted({g.split("|")[0] for g in groups}):
        tdf = targets[t].set_index("event_id")
        ids = [i for i in ev["event_id"] if i in tdf.index]
        sub = ev.set_index("event_id").loc[ids]
        etime = pd.DatetimeIndex(sub["event_time"])
        ev_ns = utc_ns(etime)
        te_ns = utc_ns(pd.DatetimeIndex(tdf.loc[ids, "effective_target_end"]))
        y = tdf.loc[ids, "value"].to_numpy("float64")
        X = feat.loc[ids, names].reset_index(drop=True)
        train = np.flatnonzero((ev_ns < dev_end_ns) & (te_ns < dev_end_ns))      # only information available before OOS
        oos_idx = np.flatnonzero((ev_ns >= dev_end_ns) & (te_ns <= oos_end_ns))
        for mname in model_names(frozen):
            fac = make_model_factory(mname, frozen)
            thr = calibrate_threshold(fac, X, y, ev_ns, te_ns, train, cfg)[0] if len(train) >= cfg.min_outer_train_events else None
            for g in [g for g in groups if g.startswith(t + "|")]:
                state = g.split("|")[1]
                base = {"experiment_id": experiment_id, "group_id": g, "target": t, "state": state, "model": mname, "oos_weeks": wk["total"]}
                if thr is None or len(oos_idx) == 0:
                    raw_rows.append({**base, "n_parent": 0, "n_selected": 0, "raw_p": 1.0, "selected_frequency": float("nan"),
                                     "standardized_uplift": float("nan"), "selected_effect": float("nan"), "bootstrap_ci_low": float("nan"),
                                     "bootstrap_ci_high": float("nan"), "uplift": float("nan"), "parent_effect": float("nan"),
                                     "parent_frequency": float("nan"), "retention_ratio": float("nan"), "not_evaluable": True})
                    continue
                model = fac().fit(X.iloc[train], y[train])
                score = model.predict(X.iloc[oos_idx])
                states = assign_state(score, thr)
                stats = evaluate_panel(y[oos_idx], states, etime[oos_idx].tz_convert("UTC").year.to_numpy(), week_key(etime[oos_idx], frozen.tz),
                                       ev_ns[oos_idx], wk["total"], bootstrap_reps=pol["bootstrap_repetitions"],
                                       permutation_reps=pol["permutation_repetitions"], seed=pol["seed"], ci_level=pol["ci_level"],
                                       min_events_year=frozen.acceptance["year_consistency"]["min_selected_events_for_eligible_year"])[state]
                raw_rows.append({**base, **{k: stats[k] for k in ("n_parent", "n_selected", "parent_frequency", "selected_frequency", "retention_ratio",
                                                                  "parent_effect", "selected_effect", "uplift", "standardized_uplift",
                                                                  "bootstrap_ci_low", "bootstrap_ci_high", "raw_p")}, "threshold": float(thr)})
    return raw_rows


def execute_campaign_oos(ws: reg.Workspace, campaign_id: str, cap: dict, items: list, oos_fingerprint: str, *, verbose: bool = True) -> dict:
    """Spend the campaign OOS (ledger first), compute every approved experiment's 3 x G confirmations, correct for ALL of them
    jointly (BH + Bonferroni over the whole campaign family), record per-experiment results and mark the campaign OOS_SPENT.

    ``items`` = [(experiment_id, approval, tables_callable, calendar_index)]; each callable returns
    (events, features, eligible, targets) built from development + OOS rows only."""
    frozen = load_frozen()
    log = (lambda *a: print(*a, flush=True)) if verbose else (lambda *a: None)
    c = reg.campaign_row(ws, campaign_id)
    parts = parse_partitions(reg.campaign_partitions(ws, campaign_id))
    pairs = [(e, g) for e, ap, _, _ in items for g in ap["approved_target_side_groups"]]
    # --- spend the OOS: ONE permanent ledger entry for the whole campaign, written BEFORE any OOS data is analysed
    reg.append_oos_access(ws, campaign_id=campaign_id, freeze_hash=c["oos_freeze_hash"], open_approval_file_hash=cap["_file_sha256"],
                          experiments=";".join(e for e, *_ in items), approved_experiment_groups=";".join(f"{e}:{g}" for e, g in pairs),
                          n_oos_confirmations=3 * len(pairs), oos_start=f"{parts.development_end:%Y-%m-%d}",
                          oos_end=f"{parts.oos_end:%Y-%m-%d}", unlock_timestamp=now_utc_iso(), code_hash=engine_code_hash())
    reg.update_campaign(ws, campaign_id, status="OOS_SPENT", oos_spent_at=now_utc_iso())
    log(f"[{campaign_id}] CAMPAIGN OOS OPENED ONCE by human approval; ledger entry written; {len(pairs)} approved groups -> {3 * len(pairs)} confirmations")
    raw_rows: list[dict] = []
    for e, ap, tables, cal in items:
        raw_rows += _oos_raw_rows(e, list(ap["approved_target_side_groups"]), tables, cal, parts, frozen)
    rule = frozen.acceptance["oos_confirmation"]
    conf = oos_confirmations(raw_rows, rule)                              # BH + Bonferroni over EVERY confirmation of the campaign
    m = len(conf)
    now = now_utc_iso()
    from engine.experiment_runner import _clean
    reports = {}
    for e, ap, _, _ in items:
        mine = [r for r in conf if r["experiment_id"] == e]
        verdicts = group_verdicts(mine, rule)
        reg.append_table(ws, "oos_trials.csv", reg.OOS_TRIAL_COLS, [{
            "campaign_id": campaign_id, "experiment_id": e, "oos_trial_id": f"{e}_OOS{i + 1:02d}",
            "group_id": r["group_id"], "target": r["target"], "state": r["state"], "model": r["model"], "n_parent_events": r["n_parent"],
            "n_selected_events": r["n_selected"], "parent_frequency": r["parent_frequency"], "selected_frequency": r["selected_frequency"],
            "retention_ratio": r["retention_ratio"], "parent_effect": r["parent_effect"], "selected_effect": r["selected_effect"],
            "uplift": r["uplift"], "standardized_uplift": r["standardized_uplift"], "bootstrap_ci_low": r["bootstrap_ci_low"],
            "bootstrap_ci_high": r["bootstrap_ci_high"], "raw_p": r["raw_p"], "oos_q": r["oos_q"], "oos_bonferroni_p": r["oos_bonferroni_p"],
            "oos_trials_in_family": r["oos_trials_in_family"], "gates_pass": r["gates_pass"],
            "decision": ("OOS_MODEL_PASS" if r["gates_pass"] else "OOS_MODEL_FAIL"), "rejection_reason": r["rejection_reason"], "revealed_at": now}
            for i, r in enumerate(mine)])
        confirmed = [g for g, v in verdicts.items() if v["confirmed"]]
        status = "OOS_CONFIRMED" if confirmed else "OOS_REJECTED"
        reg.set_status(ws, e, status, f"campaign OOS (one opening, family of {m}): confirmed groups {confirmed or 'none'}")
        groups = list(ap["approved_target_side_groups"])
        d = experiment_dir(ws, e)
        report = {"experiment_id": e, "campaign_id": campaign_id, "status": status, "approved_groups": groups,
                  "oos_period": [f"{parts.development_end:%Y-%m-%d}", f"{parts.oos_end:%Y-%m-%d}"],
                  "oos_bars_fingerprint": oos_fingerprint,
                  "oos_model_confirmations": 3 * len(groups), "family_size_for_multiple_testing": m,
                  "campaign_experiments_in_family": [x[0] for x in items], "scope_of_multiplicity": "ENTIRE CAMPAIGN",
                  "formulas": {"oos_bonferroni_p": f"min(raw_p * {m}, 1)", "oos_q": f"BH over all {m} approved model confirmations of the campaign"},
                  "group_verdicts": verdicts, "confirmations": mine, "oos_weeks": mine[0]["oos_weeks"] if mine else 0,
                  "campaign_oos_opened_once": True, "campaign_freeze_sha256": c["oos_freeze_hash"],
                  "open_approval_file_sha256": cap["_file_sha256"], "approval_file_sha256": ap["_approval_file_sha256"],
                  "is_report_sha256": ap["is_report_sha256"], "manifest_sha256": sha256_file(d / MANIFEST),
                  "note": "The campaign OOS is spent: no parameter, feature, model, filter, event, target or state change may follow, "
                          "and no later experiment may claim this partition as untouched confirmation."}
        (d / "results" / "OOS_REPORT.json").write_text(json.dumps(_clean(report), indent=2, sort_keys=True))
        (d / "results" / "OOS_REPORT.md").write_text(_oos_md(report))
        reports[e] = report
        log(f"[{e}] OOS result: {status}; group verdicts {json.dumps({g: v['confirmed'] for g, v in verdicts.items()})}")
    camp_report = {"campaign_id": campaign_id, "campaign_status": "OOS_SPENT", "family_size": m,
                   "experiments": {e: r["status"] for e, r in reports.items()},
                   "confirmations": [{k: r[k] for k in ("experiment_id", "group_id", "model", "raw_p", "oos_q", "oos_bonferroni_p", "gates_pass")} for r in conf],
                   "freeze_sha256": c["oos_freeze_hash"], "oos_bars_fingerprint": oos_fingerprint}
    (ws.root / "registry" / f"oos_campaign_report_{campaign_id}.json").write_text(json.dumps(_clean(camp_report), indent=2, sort_keys=True))
    return {**camp_report, "reports": reports}


def _oos_md(r: dict) -> str:
    L = [f"# OOS REPORT — {r['experiment_id']}  ({r['status']})\n",
         f"Campaign-level one-shot confirmation OOS {r['oos_period'][0]} … {r['oos_period'][1]} (final lockbox untouched). Approved groups of THIS experiment: {r['approved_groups']}.",
         f"This experiment's OOS model confirmations: {r['oos_model_confirmations']} (= 3 × {len(r['approved_groups'])}). The multiple-testing family is the ENTIRE CAMPAIGN ({', '.join(r['campaign_experiments_in_family'])}): {r['family_size_for_multiple_testing']} confirmations: "
         f"`{r['formulas']['oos_bonferroni_p']}`; `{r['formulas']['oos_q']}`. All approved confirmations are listed, not only winners.\n",
         "| group | model | N sel | sel f/wk | parent effect | selected effect | uplift | std uplift | CI low | raw p | OOS q | OOS Bonf p | pass | reason |", "|" + "---|" * 14]
    for c in r["confirmations"]:
        f = lambda k, fmt="{:+.5f}": ("n/a" if c.get(k) is None or (isinstance(c.get(k), float) and np.isnan(c.get(k))) else fmt.format(c[k]))  # noqa: E731
        L.append(f"| {c['group_id']} | {c['model']} | {c['n_selected']} | {f('selected_frequency', '{:.2f}')} | {f('parent_effect')} | {f('selected_effect')} | "
                 f"{f('uplift')} | {f('standardized_uplift', '{:+.3f}')} | {f('bootstrap_ci_low')} | {f('raw_p', '{:.4f}')} | {f('oos_q', '{:.4f}')} | "
                 f"{f('oos_bonferroni_p', '{:.4f}')} | {c['gates_pass']} | {c['rejection_reason'] or '-'} |")
    L.append("\n## Group verdicts (>= 2 of 3 models must satisfy the frozen OOS gates)\n")
    for g, v in r["group_verdicts"].items():
        L.append(f"* {g}: {'CONFIRMED' if v['confirmed'] else 'NOT CONFIRMED'} ({v['models_passing']}/3: {', '.join(v['models']) or '-'})")
    L.append("\nThe shared OOS partition was opened exactly once for the whole campaign; BH and Bonferroni above cover every approved confirmation of every experiment in it.")
    L.append("\n" + r["note"] + "\n")
    return "\n".join(L)
