"""Frozen acceptance logic: gates, decision classes, 2-of-3 model agreement, sensitivity veto.

A single model trial passes its own gates only if ALL hold:
  selected OOS frequency >= 1.0/week; standardized uplift >= 0.10; bootstrap CI lower bound > 0;
  experiment_q <= 0.05; campaign_q <= 0.05; >= 70% of eligible OOS years (>= 20 selected events)
  have selected effect > 0.
Promotion happens at TARGET x SIDE level: at least 2 of the 3 model trials must pass.
No additional thresholds exist; nothing here depends on any diagnostic.
"""
from __future__ import annotations

import math
from collections import defaultdict

PROMOTABLE = "PROMOTABLE"
LOW_FREQ = "REJECTED_LOW_FREQUENCY"
LOW_UPLIFT = "REJECTED_INSUFFICIENT_UPLIFT"
STAT = "REJECTED_STATISTICAL"
INSTAB = "REJECTED_INSTABILITY"
AGREE = "REJECTED_MODEL_AGREEMENT"
SENS = "REJECTED_SENSITIVITY"
DIAG = "DIAGNOSTIC_ONLY"
PENDING_SENS = "PROMOTABLE_PENDING_SENSITIVITY"
FREQ_LOSS_LABEL = "REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS"


def _f(row, key):
    v = row.get(key)
    try:
        v = float(v)
    except (TypeError, ValueError):
        return float("nan")
    return v


def classify_trial(row: dict, acc: dict) -> tuple[bool, str, str]:
    """(passes_own_gates, decision, rejection_reason) for one selection trial row."""
    n_sel = _f(row, "n_selected_events")
    freq, su = _f(row, "selected_frequency"), _f(row, "standardized_uplift")
    ci_low, qe, qc = _f(row, "bootstrap_ci_low"), _f(row, "experiment_q"), _f(row, "campaign_q")
    pos, elig = _f(row, "positive_years"), _f(row, "eligible_years")
    if not (n_sel > 0) or any(math.isnan(v) for v in (freq, su, ci_low, qe, qc)):
        return False, DIAG, "NOT_EVALUABLE: no selected OOS events or undefined statistics"
    fails: dict[str, list[str]] = defaultdict(list)
    if freq < acc["min_promotable_oos_frequency_per_week"]:
        fails[LOW_FREQ].append(f"selected frequency {freq:.3f}/week < {acc['min_promotable_oos_frequency_per_week']}")
    if su < acc["min_standardized_uplift"]:
        ret = _f(row, "retention_ratio")
        msg = f"standardized uplift {su:.3f} < {acc['min_standardized_uplift']}"
        if ret < 1.0:
            msg += f" at retention {ret:.2f} ({FREQ_LOSS_LABEL})"
        fails[LOW_UPLIFT].append(msg)
    if not ci_low > acc["bootstrap_ci_lower_bound_must_exceed"]:
        fails[STAT].append(f"bootstrap CI lower bound {ci_low:.4f} <= 0")
    if qe > acc["max_experiment_q"]:
        fails[STAT].append(f"experiment_q {qe:.4f} > {acc['max_experiment_q']}")
    if qc > acc["max_campaign_q"]:
        fails[STAT].append(f"campaign_q {qc:.4f} > {acc['max_campaign_q']}")
    st = acc["stability"]
    if not (elig > 0) or pos / elig < st["min_fraction_positive_years"]:
        fails[INSTAB].append(f"positive years {int(pos) if not math.isnan(pos) else 0}/{int(elig) if not math.isnan(elig) else 0}"
                             f" (need >= {st['min_fraction_positive_years']:.0%} of eligible years with "
                             f">= {st['min_selected_events_for_eligible_year']} selected events)")
    if not fails:
        return True, PROMOTABLE, ""
    primary = next(c for c in acc["decision_priority"] if c in fails)
    reason = "; ".join(f"[{cls}] " + ", ".join(msgs) for cls, msgs in fails.items())
    return False, primary, reason


def decide_experiment(rows: list[dict], acc: dict, sensitivity: dict[str, str] | None = None) -> list[dict]:
    """Apply gates + 2-of-3 agreement + sensitivity veto. Returns rows with decision/rejection_reason set.

    ``sensitivity`` maps 'TARGET|STATE' -> PASSED | FAILED | SKIPPED_NO_PARAMETERS | PENDING.
    """
    sensitivity = sensitivity or {}
    need = acc["model_agreement"]["min_models_passing"]
    results = [(r, *classify_trial(r, acc)) for r in rows]
    groups: dict[tuple, int] = defaultdict(int)
    for r, ok, _, _ in results:
        if ok:
            groups[(r["target"], r["state"])] += 1
    out = []
    for r, ok, decision, reason in results:
        r = dict(r)
        key = (r["target"], r["state"])
        if ok:
            k = groups[key]
            if k < need:
                decision, reason = AGREE, f"passes own gates but only {k} of 3 models pass (need {need})"
            else:
                s = sensitivity.get(f"{r['target']}|{r['state']}", "PENDING")
                if s == "FAILED":
                    decision, reason = SENS, "development candidate vetoed by event-parameter sensitivity"
                elif s == "PENDING":
                    decision, reason = PENDING_SENS, "candidate exists; sensitivity probes not yet run"
                else:
                    decision, reason = PROMOTABLE, ""
        r["decision"], r["rejection_reason"] = decision, reason
        out.append(r)
    return out
