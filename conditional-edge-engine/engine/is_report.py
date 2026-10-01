"""IS_REPORT.json / IS_REPORT.md: everything a human needs to understand how a candidate arose WITHOUT opening OOS.

The report is built only from development-stage artifacts (results.json, the registry) and is sealed once OOS is unlocked:
``oos_status_label`` is the single source of the "OOS status" line, so "NOT ACCESSED" cannot be printed after OOS has run.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from engine import trial_registry as reg
from engine.acceptance import (PROVISIONAL, SHORTLIST, rank_groups, rank_trials)
from engine.common import (CODE_ROOT, EngineError, Frozen, engine_code_hash, load_frozen, load_yaml, sha256_file)
from engine.experiment_lifecycle import MANIFEST, experiment_dir

DECILE_NOTE = ("These bins were not selection trials and cannot promote a candidate.\n"
               "Using them to construct a rule requires a new registered experiment.")
DIAG_BANNER = "DIAGNOSTIC ONLY — NOT A SELECTION TRIAL"
NOT_ACCESSED = "NOT ACCESSED"


class ReportSealedError(EngineError):
    pass


def oos_status_label(ws: reg.Workspace, experiment_id: str) -> str:
    """'NOT ACCESSED' iff the OOS ledger has no entry for the experiment and no OOS artifact exists."""
    d = experiment_dir(ws, experiment_id) / "results"
    if reg.oos_spent(ws, experiment_id) or (d / "OOS_REPORT.json").exists():
        return "OOS SPENT — ACCESSED (see registry/oos_access.csv); this IS report is sealed"
    return NOT_ACCESSED


def _n(x, fmt="{:.4f}"):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "n/a"
    return "n/a" if math.isnan(x) else fmt.format(x)


def _table(header, rows) -> str:
    if not rows:
        return "_none_\n"
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out) + "\n"


TRIAL_HEADER = ["trial", "opp #", "target", "model", "state", "N sel", "parent f/wk", "sel f/wk", "retention", "parent effect",
                "selected effect", "uplift", "std uplift", "95% block-boot CI (uplift)", "raw p", "exp q", "exp Bonf p",
                "camp q", "camp Bonf p", "pos-eff yrs", "pos-uplift yrs", "pos-eff folds", "pos-uplift folds", "decision"]


def _trial_row(r) -> list:
    def cnt(a, b):
        return f"{int(a) if not pd.isna(a) else 0}/{int(b) if not pd.isna(b) else 0}"
    return [r["trial_id"], int(r["selection_opportunity_number"]), r["target"], r["model"], r["state"], int(r["n_selected_events"]),
            _n(r["parent_frequency"], "{:.2f}"), _n(r["selected_frequency"], "{:.2f}"), _n(r["retention_ratio"], "{:.2f}"),
            _n(r["parent_effect"], "{:+.5f}"), _n(r["selected_effect"], "{:+.5f}"), _n(r["uplift"], "{:+.5f}"),
            _n(r["standardized_uplift"], "{:+.3f}"),
            f"[{_n(r['bootstrap_ci_low'], '{:+.5f}')}, {_n(r['bootstrap_ci_high'], '{:+.5f}')}]",
            _n(r["raw_p"], "{:.4f}"), _n(r["experiment_q"], "{:.4f}"), _n(r["experiment_bonferroni_p"], "{:.4f}"),
            _n(r["campaign_q"], "{:.4f}"), _n(r["campaign_bonferroni_p"], "{:.4f}"),
            cnt(r["positive_years"], r["eligible_years"]), cnt(r["positive_uplift_years"], r["eligible_years"]),
            cnt(r["positive_effect_folds"], r["folds_evaluated"]), cnt(r["positive_uplift_folds"], r["folds_evaluated"]),
            r["decision"] + (" ⚠YEAR_CONCENTRATION_WARNING" if r.get("year_concentration_warning") else "")]


def _vlabel(ver: dict, r: dict) -> str:
    v = ver.get(f"{r['target']}|{r['model']}")
    if isinstance(v, dict):
        return f"{v.get('label', 'PENDING')}({v.get('mode', '?')})"
    return "PENDING"


def _json_safe(o):
    if isinstance(o, dict):
        return {str(k): _json_safe(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_json_safe(v) for v in o]
    if isinstance(o, (float, np.floating)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return o


def build_is_report(ws: reg.Workspace, experiment_id: str, bundle: dict, trials: pd.DataFrame, obs: pd.DataFrame,
                    frozen: Frozen) -> tuple[dict, str]:
    status = oos_status_label(ws, experiment_id)
    if status != NOT_ACCESSED:
        raise ReportSealedError(f"{experiment_id}: {status}. The IS report can no longer be (re)generated.")
    d = experiment_dir(ws, experiment_id)
    exp = reg.experiment_row(ws, experiment_id)
    summ = reg.campaign_summary(ws, exp["campaign_id"], frozen)
    spec = load_yaml(d / "EVENT_SPEC.yaml")
    manifest = json.loads((d / MANIFEST).read_text())
    acc = frozen.acceptance
    rows = trials.to_dict("records")
    top_trials = rank_trials(rows)
    top_groups = rank_groups(rows, acc, frozen.trial_policy["shortlist"]["top_groups_reported"])
    b = bundle["base_event"]
    n_rev = summ["selection_trials_revealed"]
    cap = summ["selection_trials_max"]
    ver = json.loads(exp["verification_json"] or "{}")
    sens = json.loads(exp["sensitivity_json"] or "{}")
    my_obs = obs[obs["experiment_id"] == experiment_id]
    cumulative = int(trials["cumulative_campaign_selection_trials"].iloc[0]) if len(trials) else 0
    first_opp, last_opp = int(trials["selection_opportunity_number"].min()), int(trials["selection_opportunity_number"].max())

    # ---------------------------------------------------------------- JSON
    J: dict = {
        "experiment_id": experiment_id, "campaign_id": exp["campaign_id"],
        "counters": {"experiment_selection_trials": f"{len(trials)} / 24", "campaign_revealed_selection_trials": f"{n_rev} / {cap}",
                     "statistical_selection_opportunities_exposed_so_far": n_rev,
                     "cumulative_campaign_selection_trials_when_this_experiment_was_revealed": cumulative,
                     "this_experiment_opportunity_numbers": [first_opp, last_opp]},
        "A_hypothesis": {"hypothesis": spec["hypothesis"], "hypothesis_md": (d / "HYPOTHESIS.md").read_text()},
        "B_event_definition": {k: spec.get(k) for k in ("event_condition", "base_parameters", "sensitivity_parameters",
                               "eligible_session", "deduplication_rule", "cooldown", "expected_information_time", "filter_ladder", "indicator")},
        "C_direction": spec["direction_definition"],
        "D_raw_event_frequency": {"events": b["n_events"], "model_eligible": b["n_model_eligible"], "trading_weeks": b["trading_weeks"],
                                  "per_week": b["raw_event_frequency_per_week"], "flag": b["flag"],
                                  "target_timestamp_ineligible_removed": b["target_timestamp_ineligible"]},
        "E_data_period": {"partitions": bundle["partitions"], "development_bars": b["development_bars"], "first_bar": b["first_bar"],
                          "last_bar": b["last_bar"], "rows_removed_before_research_code": b["rows_removed_before_research"],
                          "train_period": bundle["train_period"], "development_cv_period": bundle["validation_period"],
                          "is_data_fingerprint": bundle["is_data_fingerprint"]},
        "F_selection_trial_count": {"experiment": 24, "campaign_revealed": n_rev, "campaign_max": cap},
        "G_all_24_trials": [{k: (None if (isinstance(v, float) and np.isnan(v)) else v) for k, v in r.items()} for r in rows],
        "H_multiplicity": {"experiment_bonferroni_universe": 24, "campaign_bonferroni_universe": n_rev,
                           "formulas": {"experiment_bonferroni_p": "min(raw_p * 24, 1)", "campaign_bonferroni_p": "min(raw_p * (24*E), 1)",
                                        "BH": "Benjamini-Hochberg over ALL trials of the family (never only survivors)"}},
        "I_top_configurations": {"ranking_rule": "std uplift DESC, campaign_bonferroni_p ASC, selected frequency DESC, trial_id ASC",
                                 "eligible_trials_ranked": [r["trial_id"] for r in top_trials], "top_groups": top_groups},
        "J_model_agreement": {f"{t}|{s}": {"models_eligible": sorted(r["model"] for r in rows if r["target"] == t and r["state"] == s and r["decision"] == SHORTLIST),
                                           "models_provisional": sorted(r["model"] for r in rows if r["target"] == t and r["state"] == s and r["decision"] == PROVISIONAL)}
                              for t in sorted({r["target"] for r in rows}) for s in ("UPPER_HALF", "LOWER_HALF")},
        "K_calendar_years": {f"{r['trial_id']}": bundle["panels"][f"{r['target']}|{r['model']}"]["stats"][r["state"]]["yearly"] for r in rows},
        "L_development_cv_folds": {f"{r['trial_id']}": {"folds": bundle["panels"][f"{r['target']}|{r['model']}"]["stats"][r["state"]]["folds"],
                                                       "fold_records": bundle["development_cv_folds"][f"{r['target']}|{r['model']}"]} for r in rows},
        "R_feature_diagnostics": {**bundle["feature_diagnostics"], "label": DIAG_BANNER},
        "S_filter_ladder": bundle["ladder"] or {"note": "no filter_ladder declared in EVENT_SPEC"},
        "T_sensitivity": {"status": bundle["sensitivity"]["status"], "verdicts": sens, "detail": bundle["sensitivity"]["groups"]},
        "external_verification": ver, "external_verification_overall": exp["research_verification"],
        "W_observations": [{k: r[k] for k in ("observation_id", "category", "description")} for _, r in my_obs.iterrows()],
        "X_hashes": {"manifest_sha256": sha256_file(d / MANIFEST), "manifest_hash": manifest["manifest_hash"],
                     "event_hash": manifest["event_hash"], "event_py": manifest["hashes"]["event_py"], "event_spec": manifest["hashes"]["event_spec"],
                     "partitions_hash": manifest["partitions_hash"], "frozen_bundle_hash": manifest["hashes"]["frozen_bundle_hash"],
                     "engine_code_hash": manifest["hashes"]["engine_code_hash"], "engine_version": manifest["engine_version"],
                     "trial_ledger_hash": exp["trial_ledger_hash"], "is_data_fingerprint": bundle["is_data_fingerprint"],
                     "results_sha256": sha256_file(d / "results" / "results.json"),
                     "verifier_pin": load_yaml(CODE_ROOT / "frozen/v1/VERIFIER_PIN.yaml")["commit"]},
        "Y_oos_status": status,
        "is_status": exp["is_status"], "lifecycle_status": exp["status"],
    }
    # ---------------------------------------------------------------- narrative helpers
    def group_trials(t, s):
        return [r for r in rows if r["target"] == t and r["state"] == s]

    L: list[str] = []
    L.append(f"# IS REPORT — {experiment_id}\n")
    L.append(f"**EXPERIMENT SELECTION TRIALS: {len(trials)} / 24**\n")
    L.append(f"**CAMPAIGN REVEALED SELECTION TRIALS: {n_rev} / {cap}**\n")
    L.append(f"**Number of statistical selection opportunities exposed so far: {n_rev}** (campaign {exp['campaign_id']}; this experiment "
             f"carries selection opportunity numbers {first_opp}–{last_opp}; cumulative count when it was revealed: {cumulative}).\n")
    L.append(f"**OOS status = {status}**\n")
    L.append(f"* IS status (retroactive, as of campaign universe {n_rev}): **{exp['is_status']}**; lifecycle status: **{exp['status']}**")
    L.append(f"* external verification: **{exp['research_verification']}** (a model path counts toward 2-of-3 only if verified in strong mode)")
    L.append("* The campaign-adjusted values below are RETROACTIVE: later experiments in the campaign enlarge the multiplicity universe and may remove eligibility.\n")
    L.append("## A. Experiment hypothesis\n")
    L.append(spec["hypothesis"].strip() + "\n")
    L.append("## B. Exact event definition\n")
    L.append(f"* condition: {spec['event_condition']['description'].strip()}")
    L.append(f"* base parameters: `{json.dumps(spec['base_parameters'])}`; sensitivity parameters: {spec['sensitivity_parameters']}")
    L.append(f"* eligible session (exchange-local): {spec['eligible_session']}; deduplication: {spec['deduplication_rule']}; cooldown: {spec['cooldown']}")
    L.append(f"* information time: {spec['expected_information_time']['rule']}")
    if spec.get("filter_ladder"):
        L.append(f"* frozen filter ladder (order fixed before results): {spec['filter_ladder']}")
    L.append(f"* event.py sha256 `{manifest['hashes']['event_py']}`; EVENT_SPEC sha256 `{manifest['hashes']['event_spec']}`\n")
    L.append("## C. Direction\n")
    L.append(f"All events: **{spec['direction_definition']['values'][0]:+d}** ({spec['direction_definition']['rule']}). v1 allows one direction per experiment.\n")
    L.append("## D. Raw event frequency\n")
    L.append(_table(["quantity", "value"], [["events after session/dedup/cooldown/target-session rules", f"{b['n_events']:,}"],
        ["model-eligible events (>= 480 completed bars)", f"{b['n_model_eligible']:,}"], ["development trading weeks", b["trading_weeks"]],
        ["raw event frequency", _n(b["raw_event_frequency_per_week"], "{:.2f}") + " / week"],
        ["TARGET_TIMESTAMP_INELIGIBLE events removed (60-bar window would cross the RTH close)", b["target_timestamp_ineligible"]],
        ["declared parameters never read by event.py", ", ".join(b["unused_parameters"]) or "none"]]))
    if b["flag"]:
        L.append(f"\n**{b['flag']}** — a fixed half-state cannot realistically keep >= 1/week. The 50% threshold is NOT changed.\n")
    L.append("## E. Data period used\n")
    L.append(f"* DEVELOPMENT only: bars {b['first_bar']} … {b['last_bar']} ({b['development_bars']:,} bars). Partitions (frozen in the manifest): {bundle['partitions']}")
    L.append(f"* OOS and lockbox rows removed before research code was called: {b['rows_removed_before_research']:,}")
    L.append(f"* training history: {bundle['train_period']}; DEVELOPMENT_CV validation: {bundle['validation_period']}\n")
    L.append("## F. Exact selection trial count\n")
    L.append(f"4 targets × 3 models × 2 states = **24** pre-registered selection trials (no threshold, feature, parameter or filter search). "
             f"Campaign {exp['campaign_id']}: {n_rev} revealed of {cap} possible.\n")
    L.append("## G. All 24 trial results (M–Q: frequency, retention, parent/selected effect, uplift, CI)\n")
    L.append("All statistics are on pooled DEVELOPMENT_CV validation predictions (5 purged chronological folds). Nothing here is OOS.\n")
    L.append(_table(TRIAL_HEADER, [_trial_row(r) for r in trials.to_dict("records")]))
    L.append("## H. Multiplicity adjustments\n")
    L.append(f"* `experiment_bonferroni_p = min(raw_p × 24, 1)`; `experiment_q` = BH over all 24 trials.")
    L.append(f"* `campaign_bonferroni_p = min(raw_p × {n_rev}, 1)` (universe = 24 × {n_rev // 24} experiments); `campaign_q` = BH over all {n_rev} revealed trials, "
             f"including rejected experiments, rejected models and the opposite score side. Recomputed after every new reveal.\n")
    L.append("## I. Top configurations (deterministic ranking, no subjective choice)\n")
    L.append("Eligibility is the full hard IS gate set; ranking = standardized uplift DESC, campaign_bonferroni_p ASC, selected frequency DESC, trial_id ASC.\n")
    L.append(_table(TRIAL_HEADER, [_trial_row(r) for r in top_trials]))
    L.append("### TOP 5 IS GROUPS (the human may unlock at most 2 for OOS; each approved group runs all 3 models)\n")
    L.append(_table(["rank", "group (TARGET|SIDE)", "models eligible", "median std uplift", "median campaign Bonf p", "median sel f/wk"],
                    [[g["rank"], g["group_id"], ", ".join(g["models"]), _n(g["median_standardized_uplift"], "{:+.3f}"),
                      _n(g["median_campaign_bonferroni_p"], "{:.4f}"), _n(g["median_selected_frequency"], "{:.2f}")] for g in top_groups]))
    L.append("## J. Model agreement (>= 2 of 3 models required)\n")
    L.append(_table(["group", "eligible models", "provisional models"], [[k, ", ".join(v["models_eligible"]) or "-", ", ".join(v["models_provisional"]) or "-"]
                                                                        for k, v in J["J_model_agreement"].items()]))
    L.append("## K. All IS calendar years (every trial; eligible = >= 20 selected events)\n")
    for r in rows:
        yl = bundle["panels"][f"{r['target']}|{r['model']}"]["stats"][r["state"]]["yearly"]
        L.append(f"**{r['trial_id']} {r['target']}/{r['model']}/{r['state']}** — positive selected-effect years {int(r['positive_years'])}/{int(r['eligible_years'])}, "
                 f"positive-uplift years {int(r['positive_uplift_years'])}/{int(r['eligible_years'])}, largest-year share of total absolute uplift "
                 f"{_n(r['year_concentration_share'], '{:.2f}')}" + (" — **YEAR_CONCENTRATION_WARNING** (> 35%)" if r["year_concentration_warning"] else "") + "\n")
        L.append(_table(["year", "eligible", "N parent", "N selected", "selected f/wk", "parent effect", "selected effect", "uplift"],
                        [[y["year"], "yes" if y["eligible"] else "no", y["n_parent"], y["n_selected"], _n(y["selected_frequency"], "{:.2f}"),
                          _n(y["parent_effect"], "{:+.5f}"), _n(y["selected_effect"], "{:+.5f}"), _n(y["uplift"], "{:+.5f}")] for y in yl]))
    L.append("## L. All 5 purged DEVELOPMENT_CV folds (internal cross-validation — NOT OOS)\n")
    seen_fold_records = set()
    for r in rows:
        key = f"{r['target']}|{r['model']}"
        if key not in seen_fold_records:
            seen_fold_records.add(key)
            L.append(f"**{key}** fold records: " + "; ".join(f"fold {f['fold']}: {f['status']} (train {f['n_train']}, validation {f['n_validation']})"
                                                           for f in bundle["development_cv_folds"][key]) + "\n")
    for r in rows:
        fl = bundle["panels"][f"{r['target']}|{r['model']}"]["stats"][r["state"]]["folds"]
        L.append(f"**{r['trial_id']}** folds with evidence {len(fl)}/5" + ("" if len(fl) >= 5 else " — **INSUFFICIENT_DEVELOPMENT_FOLD_EVIDENCE**") + "\n")
        L.append(_table(["fold", "N parent", "N selected", "selected f/wk", "parent effect", "selected effect", "uplift"],
                        [[f["fold"], f["n_parent"], f["n_selected"], _n(f["selected_frequency"], "{:.2f}"), _n(f["parent_effect"], "{:+.5f}"),
                          _n(f["selected_effect"], "{:+.5f}"), _n(f["uplift"], "{:+.5f}")] for f in fl]))
    L.append("## M–Q. Frequency / retention / parent effect / selected effect / uplift / confidence intervals\n")
    L.append("See section G (one row per trial: parent and selected frequency, retention, parent and selected effect, uplift, standardized uplift, 95% weekly-block bootstrap CI).\n")
    L.append(f"## R. Feature diagnostics — {DIAG_BANNER}\n")
    fd = bundle["feature_diagnostics"]
    L.append("Feature-family importance (share of total importance), score/target decile monotonicity (Spearman), Ridge coefficient sign stability and "
             "yearly feature-mean shifts. Feature-family ablation is not implemented in v1.\n")
    L.append(_table(["panel", "family importance"], [[k, ", ".join(f"{a}:{v:.2f}" for a, v in list(fam.items())[:5])] for k, fam in fd["family_importance"].items()]))
    L.append(_table(["panel", "score↔target decile monotonicity (Spearman)"], [[k, _n(v, "{:+.2f}")] for k, v in fd["score_monotonicity"].items()]))
    for t, coefs in fd["ridge_coefficient_stability"].items():
        L.append(f"Ridge coefficient stability {t}: " + ", ".join(f"{k} ({c['mean_coef']:+.3g}, sign agreement {c['sign_agreement_across_folds']:.0%})" for k, c in coefs.items()) + "\n")
    L.append("Largest yearly feature-mean shifts (in SD): " + ", ".join(f"{r['feature']} {r['max_abs_year_mean_shift_in_sd']:.2f}" for r in fd["distribution_shift"]) + "\n")
    L.append("### Score deciles (pooled DEVELOPMENT_CV)\n")
    L.append(DECILE_NOTE + "\n")
    for key, p in sorted(bundle["panels"].items()):
        dd = p.get("deciles") or {}
        if not dd.get("deciles"):
            continue
        L.append(f"#### {key.replace('|', ' / ')} — {DIAG_BANNER}\n")
        L.append(_table(["decile", "N", "events / week", "mean target (event direction)"],
                        [[r["decile"], r["n"], _n(r["frequency_per_week"], "{:.3f}"), _n(r["mean_target"], "{:+.6f}")] for r in dd["deciles"]]))
        yrs = dd.get("by_year", {})
        if yrs:
            L.append("Year-by-year mean target by decile:\n")
            L.append(_table(["year"] + [f"D{i}" for i in range(1, 11)], [[y] + [_n(v, "{:+.5f}") for v in vals] for y, vals in sorted(yrs.items())]))
    L.append(f"### Diagnostic targets (means over model-eligible events; report only) — {DIAG_BANNER}\n")
    L.append(_table(["diagnostic target", "mean"], [[k, _n(v, "{:.6f}")] for k, v in bundle["diagnostic_targets"].items()]))
    L.append("## S. Filter / component ladder\n")
    lad = bundle["ladder"]
    if not lad:
        L.append("No `filter_ladder` declared in EVENT_SPEC.\n")
    else:
        L.append(f"{DIAG_BANNER}. Order frozen before results: {lad['order_frozen']}. The engine cannot reorder, remove, add or re-threshold steps; "
                 f"a ladder step turned into a rule is a NEW experiment (24 new selection trials).\n")
        for tname in sorted({t for st in lad["steps"] for t in st["targets"]}):
            L.append(f"#### ladder — {tname}\n")
            L.append(_table(["step", "events/week", "retention vs parent", "retention vs previous", "effect", "uplift vs parent", "uplift vs previous",
                             "pos step-over-step uplift years", "flags"],
                            [[st["step"], _n(st["frequency_per_week"], "{:.2f}"), _n(st["targets"][tname]["retention_vs_parent"], "{:.2f}"),
                              _n(st["targets"][tname]["retention_vs_previous"], "{:.2f}"), _n(st["targets"][tname]["effect"], "{:+.6f}"),
                              _n(st["targets"][tname]["uplift_vs_parent"], "{:+.6f}"), _n(st["targets"][tname]["uplift_vs_previous"], "{:+.6f}"),
                              f"{st['targets'][tname]['positive_uplift_years_vs_previous']}/{st['targets'][tname]['eligible_years']}",
                              " / ".join(st["targets"][tname]["flags"]).replace("_", " ") or "ok"] for st in lad["steps"]]))
            for st in lad["steps"]:
                yl = st["targets"][tname]["yearly"]
                L.append(f"year-by-year {st['step']}: " + ", ".join(f"{y['year']}: eff {y['effect']:+.5f}, Δparent {_n(y['uplift_vs_parent'], '{:+.5f}')}, Δprev {_n(y['uplift_vs_previous'], '{:+.5f}')}"
                                                                    f"{'' if y['eligible'] else ' (inelig.)'}" for y in yl) + "\n")
    L.append("## T. Sensitivity diagnostics\n")
    L.append(f"status {bundle['sensitivity']['status']}; verdicts per candidate group: {sens or 'none'}\n")
    for g, v in bundle["sensitivity"]["groups"].items():
        L.append(f"* {g}: **{v['verdict']}**" + "".join(f"; {p['parameter']}×{p['multiplier']}→{p['value']}: models uplift>0 {p['models_positive_uplift']}/3, freq ok {p['models_frequency_ok']}/3"
                                                   for p in v.get("probes", [])))
    L.append("\nProbes can only confirm or veto; a better probe never replaces the base parameter.\n")
    L.append("### External verification (model paths)\n")
    L.append(_table(["path", "label", "mode"], [[k, (v["label"] if isinstance(v, dict) else v), (v.get("mode") if isinstance(v, dict) else "")] for k, v in sorted(ver.items())]))
    L.append("## U. Why each shortlisted configuration was selected — how it emerged\n")
    if not top_groups:
        L.append("No group is IS-shortlist-eligible. " + ("Provisional groups exist (see section V for what is missing)." if exp["is_status"] == PROVISIONAL else "") + "\n")
    for g in top_groups:
        gt = group_trials(g["target"], g["state"])
        pas = [r for r in gt if r["decision"] == SHORTLIST]
        med = lambda k: float(np.median([float(r[k]) for r in pas]))  # noqa: E731
        L.append(f"### Rank {g['rank']}: {g['group_id']}\n")
        L.append("How this configuration emerged\n")
        L.append(f"- Base event frequency: {_n(b['raw_event_frequency_per_week'], '{:.1f}')}/week.")
        L.append(f"- {', '.join(sorted(r['model'] for r in gt))} all evaluated the same frozen 56-feature bank.")
        L.append("- No feature threshold was searched; no feature subset, lookback or horizon was searched.")
        L.append(f"- {g['state']} was predeclared before results (frozen score-state definition: train-only median).")
        L.append(f"- Selected frequency: {med('selected_frequency'):.2f}/week (retention {med('retention_ratio'):.2f}).")
        L.append(f"- Parent effect: {med('parent_effect'):+.6f}; selected effect: {med('selected_effect'):+.6f}; uplift: {med('uplift'):+.6f} "
                 f"(standardized {med('standardized_uplift'):+.3f}) — medians over the {len(pas)} eligible models.")
        for r in pas:
            L.append(f"- {r['model']}: positive uplift in {int(r['positive_uplift_years'])}/{int(r['eligible_years'])} eligible years; positive selected effect in "
                     f"{int(r['positive_years'])}/{int(r['eligible_years'])} years; positive uplift in {int(r['positive_uplift_folds'])}/{int(r['folds_evaluated'])} DEVELOPMENT_CV folds; "
                     f"bootstrap CI lower bound {r['bootstrap_ci_low']:+.5f}.")
        L.append(f"- Bonferroni adjusted p (experiment): {med('experiment_bonferroni_p'):.4g}; campaign Bonferroni adjusted p: {med('campaign_bonferroni_p'):.4g}; "
                 f"BH q experiment {med('experiment_q'):.4g}, campaign {med('campaign_q'):.4g}.")
        L.append(f"- Model agreement: {len(pas)}/3.")
        L.append(f"- Selection trial count when observed: {int(pas[0]['cumulative_campaign_selection_trials'])}.")
        concerns = []
        if any(r["year_concentration_warning"] for r in pas):
            concerns.append("YEAR_CONCENTRATION_WARNING: one calendar year carries > 35% of total absolute uplift")
        if any(r["decision"] != SHORTLIST for r in gt):
            concerns.append("not every model is eligible: " + ", ".join(f"{r['model']}={r['decision']}" for r in gt if r["decision"] != SHORTLIST))
        concerns.append("external verification: " + ", ".join(f"{r['model']}={_vlabel(ver, r)}" for r in gt))
        concerns.append("campaign-adjusted values will keep changing as more experiments are revealed")
        L.append("- CONCERNS surfaced: " + "; ".join(concerns) + ".\n")
        if spec.get("filter_ladder"):
            L.append("- This event contains a frozen filter ladder; see section S for step-by-step frequency destruction and consistency.\n")
    L.append("## V. Why every other configuration was rejected\n")
    shortlisted = {r["trial_id"] for g in top_groups for r in rows if r["target"] == g["target"] and r["state"] == g["state"] and r["decision"] == SHORTLIST}
    L.append(_table(["trial", "target/model/state", "decision", "reason"], [[r["trial_id"], f"{r['target']}/{r['model']}/{r['state']}", r["decision"], r["rejection_reason"] or "-"]
                                                                          for r in rows if r["trial_id"] not in shortlisted]))
    L.append("## W. Non-promotable interesting observations (registry/observations.csv)\n")
    L.append(f"**{DIAG_BANNER}.** Anything here can only inspire a NEW registered experiment (which adds 24 selection trials to the campaign universe).\n")
    L.append(_table(["id", "category", "description"], [[r["observation_id"], r["category"], r["description"]] for _, r in my_obs.iterrows()]))
    L.append("## X. Exact hashes\n")
    L.append(_table(["item", "sha256"], [[k, v] for k, v in J["X_hashes"].items()]))
    L.append("## Y. OOS status\n")
    L.append(f"**OOS status = {status}**\n")
    L.append("OOS requires a manual human approval file. Compute the hashes to reference with `python scripts/show_approval_hashes.py --experiment "
             f"{experiment_id}`. The LLM / scripts never create `approvals/{experiment_id}_OOS_APPROVAL.yaml`; at most 2 TARGET|SIDE groups from the "
             "top-5 list may be approved and every approved group runs all three frozen models.\n")
    md = "\n".join(L) + "\n"
    J["markdown_sha256"] = hashlib.sha256(md.encode()).hexdigest()
    return _json_safe(J), md


def write_is_report(ws: reg.Workspace, experiment_id: str) -> dict:
    """Build and store IS_REPORT.json/.md from results.json + registry; record the JSON hash in the registry."""
    frozen = load_frozen()
    d = experiment_dir(ws, experiment_id) / "results"
    bundle = json.loads((d / "results.json").read_text())
    trials = reg.experiment_trials(ws, experiment_id)
    J, md = build_is_report(ws, experiment_id, bundle, trials, reg.read_observations(ws), frozen)
    (d / "IS_REPORT.md").write_text(md)
    jtxt = json.dumps(J, indent=2, sort_keys=True)
    (d / "IS_REPORT.json").write_text(jtxt)
    reg.update_experiment(ws, experiment_id, is_report_sha256=hashlib.sha256(jtxt.encode()).hexdigest())
    return {"json": str(d / "IS_REPORT.json"), "md": str(d / "IS_REPORT.md")}
