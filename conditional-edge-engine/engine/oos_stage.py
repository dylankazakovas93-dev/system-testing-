"""One-shot CONFIRMATION OOS behind a manual HUMAN approval.

Nothing in this module creates an approval file. ``validate_approval`` checks the human-written
approvals/EXP_xxxx_OOS_APPROVAL.yaml against: the exact FROZEN_MANIFEST.json bytes, the exact IS_REPORT.json bytes (and the
markdown / results hashes inside it), the current IS shortlist (re-derived under the CURRENT campaign universe), external
verification of all three model paths of every approved group, the group cap (2) and the OOS ledger (one unlock ever).
The unlock is appended to the append-only ledger BEFORE any OOS data is touched. Bars at/after oos_end (final lockbox)
are removed before any computation.
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
APPROVAL_KEYS = ["experiment_id", "campaign_id", "experiment_manifest_sha256", "is_report_sha256", "approved_by", "approved",
                 "approved_target_side_groups", "approval_note"]


class ApprovalError(EngineError):
    pass


class OOSContaminated(EngineError):
    pass


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


def check_lineage_clean(ws: reg.Workspace, experiment_id: str) -> None:
    """A changed lineage cannot claim the same OOS was untouched: if an ancestor already spent this campaign's OOS, refuse."""
    exps = reg.read_experiments(ws).set_index("experiment_id")
    cur = exps.at[experiment_id, "lineage_parent"]
    seen = set()
    while cur and cur not in seen:
        seen.add(cur)
        if reg.oos_spent(ws, cur) and exps.at[cur, "campaign_id"] == exps.at[experiment_id, "campaign_id"]:
            raise OOSContaminated(f"OOS CONTAMINATED: lineage ancestor {cur} already spent this campaign's confirmation OOS; "
                                  f"{experiment_id} cannot claim it as untouched confirmation")
        cur = exps.at[cur, "lineage_parent"] if cur in exps.index else ""


def mark_contamination_if_mutated(ws: reg.Workspace, experiment_id: str) -> bool:
    """If OOS was spent and the frozen experiment was changed afterwards, mark it OOS_CONTAMINATED permanently."""
    if not reg.oos_spent(ws, experiment_id):
        return False
    errs = verify_manifest(ws, experiment_id, raise_on_error=False)["errors"]
    if errs:
        reg.set_status(ws, experiment_id, "OOS_CONTAMINATED", "frozen experiment changed after OOS was spent: " + "; ".join(errs[:3]))
        return True
    return False


def validate_approval(ws: reg.Workspace, experiment_id: str, frozen: Frozen | None = None) -> dict:
    frozen = frozen or load_frozen()
    exp = reg.experiment_row(ws, experiment_id)
    if exp["status"] == "OOS_CONTAMINATED":
        raise OOSContaminated(f"{experiment_id} is OOS_CONTAMINATED")
    if reg.oos_spent(ws, experiment_id):
        raise ApprovalError(f"OOS HAS BEEN SPENT for {experiment_id}; it can never be unlocked again")
    check_lineage_clean(ws, experiment_id)
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


def run_oos(ws: reg.Workspace, experiment_id: str, bars: pd.DataFrame, *, verbose: bool = True) -> dict:
    """The ONE-SHOT confirmation. Requires a valid human approval; spends the OOS permanently (ledger first)."""
    frozen = load_frozen()
    ap = validate_approval(ws, experiment_id, frozen)              # raises unless the human approved the exact frozen state
    d = experiment_dir(ws, experiment_id)
    spec = load_spec(d / "EVENT_SPEC.yaml")
    parts = parse_partitions(spec["partitions"])
    bars_oos = oos_view(bars, parts)                                # final lockbox removed BEFORE any computation
    del bars
    assert bars_oos.index.tz_convert("UTC").max() < parts.oos_end
    module = load_event_module(d / "event.py")
    # the ledger entry is written first (inside execute_oos); tables are then built from dev+OOS bars only
    tables = lambda: build_event_tables(module, spec, bars_oos, frozen)[:4]   # noqa: E731
    fp = bars_fingerprint(bars_oos[bars_oos.index.tz_convert("UTC") >= parts.development_end])
    return execute_oos(ws, experiment_id, ap, tables, bars_oos.index, fp, verbose=verbose)


def execute_oos(ws: reg.Workspace, experiment_id: str, ap: dict, tables, calendar_index: pd.DatetimeIndex, oos_fingerprint: str,
                *, verbose: bool = True) -> dict:
    """Spend the OOS (ledger first), compute 3 x G model confirmations, correct for ALL of them, record, set status.

    ``tables`` is a callable returning (events, features, eligible, targets) built from development + OOS rows only.
    """
    frozen = load_frozen()
    log = (lambda *a: print(*a, flush=True)) if verbose else (lambda *a: None)
    d = experiment_dir(ws, experiment_id)
    exp = reg.experiment_row(ws, experiment_id)
    spec = load_spec(d / "EVENT_SPEC.yaml")
    parts = parse_partitions(spec["partitions"])
    groups = ap["approved_target_side_groups"]
    manifest_sha = sha256_file(d / MANIFEST)
    # --- spend the OOS: permanent ledger entry written BEFORE any OOS data is analysed
    reg.append_oos_access(ws, campaign_id=exp["campaign_id"], experiment_id=experiment_id, approval_file_hash=ap["_approval_file_sha256"],
                          IS_report_hash=ap["is_report_sha256"], manifest_hash=manifest_sha, approved_target_side_groups=";".join(groups),
                          oos_start=f"{parts.development_end:%Y-%m-%d}", oos_end=f"{parts.oos_end:%Y-%m-%d}",
                          unlock_timestamp=now_utc_iso(), code_hash=engine_code_hash(),
                          verification_summary_hash=hashlib.sha256((exp["verification_json"] or "{}").encode()).hexdigest())
    log(f"[{experiment_id}] OOS UNLOCKED by human approval; ledger entry written; groups {groups}")
    events, features, eligible, targets = tables()
    cfg = WFConfig.from_policy(frozen.trial_policy)
    pol = frozen.trial_policy
    from engine.feature_engine import feature_names
    names = feature_names(frozen)
    dev_end_ns = int(parts.development_end.value)
    oos_end_ns = int(parts.oos_end.value)
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
                base = {"group_id": g, "target": t, "state": state, "model": mname}
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
    rule = frozen.acceptance["oos_confirmation"]
    conf = oos_confirmations(raw_rows, rule)
    verdicts = group_verdicts(conf, rule)
    now = now_utc_iso()
    reg.append_table(ws, "oos_trials.csv", reg.OOS_TRIAL_COLS, [{
        "campaign_id": exp["campaign_id"], "experiment_id": experiment_id, "oos_trial_id": f"{experiment_id}_OOS{i + 1:02d}",
        "group_id": r["group_id"], "target": r["target"], "state": r["state"], "model": r["model"], "n_parent_events": r["n_parent"],
        "n_selected_events": r["n_selected"], "parent_frequency": r["parent_frequency"], "selected_frequency": r["selected_frequency"],
        "retention_ratio": r["retention_ratio"], "parent_effect": r["parent_effect"], "selected_effect": r["selected_effect"],
        "uplift": r["uplift"], "standardized_uplift": r["standardized_uplift"], "bootstrap_ci_low": r["bootstrap_ci_low"],
        "bootstrap_ci_high": r["bootstrap_ci_high"], "raw_p": r["raw_p"], "oos_q": r["oos_q"], "oos_bonferroni_p": r["oos_bonferroni_p"],
        "oos_trials_in_family": r["oos_trials_in_family"], "gates_pass": r["gates_pass"],
        "decision": ("OOS_MODEL_PASS" if r["gates_pass"] else "OOS_MODEL_FAIL"), "rejection_reason": r["rejection_reason"], "revealed_at": now}
        for i, r in enumerate(conf)])
    confirmed = [g for g, v in verdicts.items() if v["confirmed"]]
    status = "OOS_CONFIRMED" if confirmed else "OOS_REJECTED"
    reg.set_status(ws, experiment_id, status, f"OOS one-shot: confirmed groups {confirmed or 'none'}")
    report = {"experiment_id": experiment_id, "campaign_id": exp["campaign_id"], "status": status, "approved_groups": groups,
              "oos_period": [f"{parts.development_end:%Y-%m-%d}", f"{parts.oos_end:%Y-%m-%d}"],
              "oos_bars_fingerprint": oos_fingerprint,
              "oos_model_confirmations": 3 * len(groups), "family_size_for_multiple_testing": len(conf),
              "formulas": {"oos_bonferroni_p": f"min(raw_p * {len(conf)}, 1)", "oos_q": f"BH over all {len(conf)} approved model confirmations"},
              "group_verdicts": verdicts, "confirmations": conf, "oos_weeks": wk["total"],
              "campaign_oos_unlocks_so_far": int((reg.read_oos_access(ws)["campaign_id"] == exp["campaign_id"]).sum()),
              "approval_file_sha256": ap["_approval_file_sha256"], "is_report_sha256": ap["is_report_sha256"],
              "manifest_sha256": manifest_sha, "note": "OOS is spent: no parameter, feature, model, filter, event, target or state change may follow."}
    from engine.experiment_runner import _clean
    rdir = d / "results"
    (rdir / "OOS_REPORT.json").write_text(json.dumps(_clean(report), indent=2, sort_keys=True))
    (rdir / "OOS_REPORT.md").write_text(_oos_md(report))
    log(f"[{experiment_id}] OOS result: {status}; group verdicts {json.dumps({g: v['confirmed'] for g, v in verdicts.items()})}")
    return report


def _oos_md(r: dict) -> str:
    L = [f"# OOS REPORT — {r['experiment_id']}  ({r['status']})\n",
         f"One-shot confirmation OOS {r['oos_period'][0]} … {r['oos_period'][1]} (final lockbox untouched). Approved groups: {r['approved_groups']}.",
         f"OOS model confirmations: {r['oos_model_confirmations']} (= 3 × {len(r['approved_groups'])}); multiple-testing family = {r['family_size_for_multiple_testing']}: "
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
    L.append(f"\nCampaign OOS unlocks so far (informational; OOS is shared by the campaign's experiments and is not multiplicity-corrected across experiments): {r['campaign_oos_unlocks_so_far']}.")
    L.append("\n" + r["note"] + "\n")
    return "\n".join(L)
