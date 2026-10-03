"""Frozen acceptance logic for the IS (development) stage.

One model trial is IS-shortlist-eligible only if ALL hold (ACCEPTANCE_RULES.yaml):
  selected frequency >= 1.0/week; standardized uplift >= 0.10; ABSOLUTE selected effect > 0 (candidate action direction);
  bootstrap CI lower bound > 0; experiment BH q, campaign BH q, experiment Bonferroni p, campaign Bonferroni p all <= 0.05;
  >= 70% of eligible years (>= 20 selected events) with selected effect > 0 AND >= 70% with uplift > 0;
  all 5 DEVELOPMENT_CV folds evaluated, >= 4/5 with uplift > 0 and >= 4/5 with selected effect > 0.
Promotion happens at TARGET x SIDE level: >= 2 of the 3 models must be eligible, and each of those model paths must have
been externally verified (strong mode, research families PASS). Campaign-adjusted values are retroactive, so group
statuses are re-derived after every newly revealed experiment:
  IS_SHORTLIST_ELIGIBLE      >= 2 models pass every gate incl. campaign-level ones, verified, sensitivity not failed
  IS_PROVISIONAL_CANDIDATE   >= 2 models pass the experiment-level gates but the campaign universe / verification /
                             sensitivity is not (yet) satisfied  -> never permanent
  IS_NO_CANDIDATE            otherwise
Nothing here can see deciles, ladders, importances or any other diagnostic.
"""
from __future__ import annotations

import math
from collections import defaultdict

import numpy as np

SHORTLIST = "IS_SHORTLIST_ELIGIBLE"
PROVISIONAL = "IS_PROVISIONAL_CANDIDATE"
NO_CANDIDATE = "IS_NO_CANDIDATE"
LOW_FREQ = "REJECTED_LOW_FREQUENCY"
LOW_UPLIFT = "REJECTED_INSUFFICIENT_UPLIFT"
COND_IMPROVE = "DIAGNOSTIC_CONDITIONAL_IMPROVEMENT"
STAT = "REJECTED_STATISTICAL"
INSTAB = "REJECTED_INSTABILITY"
AGREE = "REJECTED_MODEL_AGREEMENT"
SENS = "REJECTED_SENSITIVITY"
VERIF = "REJECTED_VERIFICATION"
DIAG = "DIAGNOSTIC_ONLY"
FREQ_LOSS_LABEL = "REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS"
FOLD_LABEL = "INSUFFICIENT_DEVELOPMENT_FOLD_EVIDENCE"
PASSING = (SHORTLIST, PROVISIONAL)


def _f(row, key):
    v = row.get(key)
    try:
        return float(v)
    except (TypeError, ValueError):
        return float("nan")


def _nan(*vals):
    return any(math.isnan(v) for v in vals)


def classify_trial(row: dict, acc: dict, campaign: bool = True) -> tuple[bool, str, str]:
    """(passes_own_gates, decision_class, reason). ``campaign=False`` skips the campaign-level adjusted p/q gates."""
    n_sel = _f(row, "n_selected_events")
    freq, su, se = _f(row, "selected_frequency"), _f(row, "standardized_uplift"), _f(row, "selected_effect")
    ci_low, qe, be = _f(row, "bootstrap_ci_low"), _f(row, "experiment_q"), _f(row, "experiment_bonferroni_p")
    qc, bc = _f(row, "campaign_q"), _f(row, "campaign_bonferroni_p")
    if not (n_sel > 0) or _nan(freq, su, se, ci_low, qe, be) or (campaign and _nan(qc, bc)):
        return False, DIAG, "NOT_EVALUABLE: no selected events or undefined statistics"
    fails: dict[str, list[str]] = defaultdict(list)
    if freq < acc["min_selected_frequency_per_week"]:
        fails[LOW_FREQ].append(f"selected frequency {freq:.3f}/week < {acc['min_selected_frequency_per_week']}")
    if su < acc["min_standardized_uplift"]:
        ret = _f(row, "retention_ratio")
        msg = f"standardized uplift {su:.3f} < {acc['min_standardized_uplift']}"
        if ret < 1.0:
            msg += f" at retention {ret:.2f} ({FREQ_LOSS_LABEL})"
        fails[LOW_UPLIFT].append(msg)
    elif not se > acc["selected_effect_must_exceed"]:
        fails[COND_IMPROVE].append(f"selected effect {se:+.5f} <= 0 in the candidate direction although uplift "
                                   f"{su:.3f} >= floor (less bad than the parent is not a candidate)")
    if not ci_low > acc["bootstrap_ci_lower_bound_must_exceed"]:
        fails[STAT].append(f"bootstrap CI lower bound {ci_low:.4g} <= 0")
    if qe > acc["max_experiment_q"]:
        fails[STAT].append(f"experiment_q {qe:.4f} > {acc['max_experiment_q']}")
    if be > acc["bonferroni"]["max_experiment_p"]:
        fails[STAT].append(f"experiment_bonferroni_p {be:.4f} > {acc['bonferroni']['max_experiment_p']}")
    if campaign:
        if qc > acc["max_campaign_q"]:
            fails[STAT].append(f"campaign_q {qc:.4f} > {acc['max_campaign_q']}")
        if bc > acc["bonferroni"]["max_campaign_p"]:
            fails[STAT].append(f"campaign_bonferroni_p {bc:.4f} > {acc['bonferroni']['max_campaign_p']}")
    yc, fc = acc["year_consistency"], acc["fold_consistency"]
    elig = _f(row, "eligible_years")
    pe, pu = _f(row, "positive_years"), _f(row, "positive_uplift_years")
    if not (elig > 0):
        fails[INSTAB].append(f"no eligible development year (>= {yc['min_selected_events_for_eligible_year']} selected events)")
    else:
        if pe / elig < yc["min_positive_effect_year_fraction"]:
            fails[INSTAB].append(f"positive selected-effect years {int(pe)}/{int(elig)} < {yc['min_positive_effect_year_fraction']:.0%}")
        if pu / elig < yc["min_positive_uplift_year_fraction"]:
            fails[INSTAB].append(f"positive-uplift years {int(pu)}/{int(elig)} < {yc['min_positive_uplift_year_fraction']:.0%}")
    nf = _f(row, "folds_evaluated")
    if not nf >= fc["required_folds"]:
        fails[INSTAB].append(f"{FOLD_LABEL}: {0 if math.isnan(nf) else int(nf)} of {fc['required_folds']} DEVELOPMENT_CV folds evaluated")
    else:
        if _f(row, "positive_uplift_folds") < fc["min_folds_positive_uplift"]:
            fails[INSTAB].append(f"positive-uplift DEVELOPMENT_CV folds {int(_f(row, 'positive_uplift_folds'))}/5 < {fc['min_folds_positive_uplift']}")
        if _f(row, "positive_effect_folds") < fc["min_folds_positive_effect"]:
            fails[INSTAB].append(f"positive selected-effect DEVELOPMENT_CV folds {int(_f(row, 'positive_effect_folds'))}/5 < {fc['min_folds_positive_effect']}")
    if not fails:
        return True, SHORTLIST, ""
    primary = next(c for c in acc["decision_priority"] if c in fails)
    return False, primary, "; ".join(f"[{c}] " + ", ".join(m) for c, m in fails.items())


def path_verification(verification: dict, row: dict, acc: dict) -> str:
    """'PASS' (strong, research families pass) | 'FAIL' (research family failure) | 'PENDING' (absent / not final)."""
    v = (verification or {}).get(f"{row['target']}|{row['model']}")
    if not v:
        return "PENDING"
    label = v["label"] if isinstance(v, dict) else v
    mode = v.get("mode") if isinstance(v, dict) else None
    if label in ("FAILED", "INCOMPLETE"):
        return "FAIL"
    if label in acc["verification"]["accepted_labels"] and mode == acc["verification"]["required_mode"]:
        return "PASS"
    return "PENDING"


def decide_experiment(rows: list[dict], acc: dict, sensitivity: dict[str, str] | None = None,
                      verification: dict | None = None) -> list[dict]:
    """Apply gates, 2-of-3 agreement, path verification and the sensitivity veto. Returns rows with decision/reason."""
    sensitivity, verification = sensitivity or {}, verification or {}
    need = acc["model_agreement"]["min_models_passing"]
    info = []
    for r in rows:
        ok_exp, dec_exp, why_exp = classify_trial(r, acc, campaign=False)
        ok_full, dec_full, why_full = classify_trial(r, acc, campaign=True)
        info.append((r, ok_exp, ok_full, dec_full, why_full, path_verification(verification, r, acc)))
    prov: dict[tuple, int] = defaultdict(int)
    elig: dict[tuple, int] = defaultdict(int)
    for r, ok_exp, ok_full, _, _, v in info:
        key = (r["target"], r["state"])
        if ok_exp and v != "FAIL":
            prov[key] += 1
        if ok_full and v == "PASS":
            elig[key] += 1
    out = []
    for r, ok_exp, ok_full, dec_full, why_full, v in info:
        r = dict(r)
        key = (r["target"], r["state"])
        sens = sensitivity.get(f"{r['target']}|{r['state']}", "PENDING")
        if ok_exp and v == "FAIL":
            decision, reason = VERIF, "external verifier research-family failure on this model path"
        elif not ok_exp:
            decision, reason = dec_full, why_full
        elif prov[key] < need:
            decision, reason = AGREE, f"passes own experiment-level gates but only {prov[key]} of 3 models qualify (need {need})"
        elif sens == "FAILED":
            decision, reason = SENS, "development candidate vetoed by event-parameter sensitivity"
        elif ok_full and v == "PASS" and elig[key] >= need and sens in ("PASSED", "SKIPPED_NO_PARAMETERS"):
            decision, reason = SHORTLIST, ""
        else:
            bits = []
            if not ok_full:
                bits.append(f"campaign-level gates not met at the current campaign universe: {why_full}")
            if v != "PASS":
                bits.append("external verification (strong, all research families PASS) pending for this model path")
            if elig[key] < need:
                bits.append(f"only {elig[key]} of 3 models fully eligible")
            if sens not in ("PASSED", "SKIPPED_NO_PARAMETERS"):
                bits.append(f"sensitivity {sens}")
            decision, reason = PROVISIONAL, "; ".join(bits)
        r["decision"], r["rejection_reason"] = decision, reason
        out.append(r)
    return out


def is_status_of(decisions) -> str:
    ds = set(decisions)
    if SHORTLIST in ds:
        return SHORTLIST
    if PROVISIONAL in ds:
        return PROVISIONAL
    return NO_CANDIDATE


def lifecycle_from_is_status(is_status: str) -> str:
    return {SHORTLIST: "AWAITING_HUMAN_FINAL_CONFIG_SELECTION", PROVISIONAL: "IS_PROVISIONAL_CANDIDATE",
            NO_CANDIDATE: "IS_REJECTED"}[is_status]


# ---------------------------------------------------------------------------- deterministic ranking
def rank_trials(rows: list[dict]) -> list[dict]:
    """Eligible trials only: std uplift DESC, campaign_bonferroni_p ASC, selected frequency DESC, trial_id ASC."""
    el = [r for r in rows if r["decision"] == SHORTLIST]
    return sorted(el, key=lambda r: (-float(r["standardized_uplift"]), float(r["campaign_bonferroni_p"]),
                                     -float(r["selected_frequency"]), str(r["trial_id"])))


def rank_groups(rows: list[dict], acc: dict, top: int = 5) -> list[dict]:
    """TARGET x SIDE groups with >= 2 of 3 eligible models, ranked by median standardized uplift of the passing models
    DESC, then median campaign_bonferroni_p ASC, median selected frequency DESC, group id ASC. At most ``top`` returned."""
    need = acc["model_agreement"]["min_models_passing"]
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        if r["decision"] == SHORTLIST:
            groups[(r["target"], r["state"])].append(r)
    out = []
    for (t, s), rs in groups.items():
        if len(rs) >= need:
            out.append({"group_id": f"{t}|{s}", "target": t, "state": s, "models": sorted(r["model"] for r in rs),
                        "median_standardized_uplift": float(np.median([float(r["standardized_uplift"]) for r in rs])),
                        "median_campaign_bonferroni_p": float(np.median([float(r["campaign_bonferroni_p"]) for r in rs])),
                        "median_selected_frequency": float(np.median([float(r["selected_frequency"]) for r in rs])),
                        "trial_ids": sorted(r["trial_id"] for r in rs)})
    out.sort(key=lambda g: (-g["median_standardized_uplift"], g["median_campaign_bonferroni_p"],
                            -g["median_selected_frequency"], g["group_id"]))
    for i, g in enumerate(out, 1):
        g["rank"] = i
    return out[:top]
