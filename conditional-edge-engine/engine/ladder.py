"""Frozen filter / component ladder (explanatory, DEVELOPMENT-ONLY diagnostics).

EVENT_SPEC.filter_ladder freezes the step order BEFORE results (BASE_TRIGGER ... FINAL_EVENT). For every step the engine
reports, per primary target (event direction; single-direction v1 experiments):
  event frequency, retention vs parent (BASE_TRIGGER) and vs previous step, effect = mean target, uplift vs parent and vs
  previous step, and year-by-year effect / uplift over eligible years (>= 20 step events in the year).
The engine can NOT reorder, remove, add or re-threshold steps, and never deletes a bad filter: these rows are
DIAGNOSTIC ONLY - NOT A SELECTION TRIAL (a ladder step turned into a rule is a NEW experiment with 24 new trials).
Flags (no new numeric thresholds; the 70% year fraction is the frozen year-consistency constant):
  NO_CONSISTENT_IMPROVEMENT       positive step-over-step uplift in < 70% of eligible years
  FREQUENCY_DESTRUCTION           retention vs previous step < 1 while NO_CONSISTENT_IMPROVEMENT
(A step whose event set is identical to the previous step - e.g. FINAL_EVENT after the last condition - is marked identical and carries no flag.)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.common import Frozen, primary_target_names
from engine.event_contract import ladder_event_sets
from engine.statistics import weeks_in_intervals
from engine.target_engine import compute_primary_targets
from engine.walkforward import INT64_MAX


def evaluate_ladder(module, spec: dict, bars_dev: pd.DataFrame, frozen: Frozen) -> dict:
    ladder = spec.get("filter_ladder")
    if not ladder:
        return {}
    acc = frozen.acceptance["year_consistency"]
    min_ev, frac = acc["min_selected_events_for_eligible_year"], acc["min_positive_uplift_year_fraction"]
    sets = ladder_event_sets(module, bars_dev, spec, frozen)
    weeks = weeks_in_intervals(bars_dev.index, [(-INT64_MAX, INT64_MAX)], frozen.tz)["total"]
    per_step = {}
    for step in ladder:
        ev = sets[step]
        tg = compute_primary_targets(bars_dev, ev, frozen) if len(ev) else {}
        per_step[step] = {"events": ev, "targets": tg}
    steps_out = []
    base_name = ladder[0]
    for i, step in enumerate(ladder):
        ev = per_step[step]["events"]
        rec = {"step": step, "n_events": int(len(ev)), "frequency_per_week": len(ev) / weeks if weeks else float("nan"), "targets": {}}
        for tname in primary_target_names(frozen):
            def table(s):
                t = per_step[s]["targets"].get(tname)
                if t is None or not len(t):
                    return pd.DataFrame({"year": [], "y": []})
                years = pd.DatetimeIndex(t["target_start"]).year
                return pd.DataFrame({"year": years.to_numpy(), "y": t["value"].to_numpy()})
            cur, base = table(step), table(base_name)
            prev = table(ladder[i - 1]) if i else cur
            eff = float(cur["y"].mean()) if len(cur) else float("nan")
            base_eff = float(base["y"].mean()) if len(base) else float("nan")
            prev_eff = float(prev["y"].mean()) if len(prev) else float("nan")
            yearly = []
            for yr in sorted(set(cur["year"])):
                c = cur[cur["year"] == yr]["y"]
                b = base[base["year"] == yr]["y"]
                pv = prev[prev["year"] == yr]["y"]
                yearly.append({"year": int(yr), "n": int(len(c)), "effect": float(c.mean()),
                               "uplift_vs_parent": float(c.mean() - b.mean()) if len(b) else float("nan"),
                               "uplift_vs_previous": float(c.mean() - pv.mean()) if len(pv) else float("nan"),
                               "eligible": len(c) >= min_ev})
            el = [y for y in yearly if y["eligible"]]
            pos_prev = sum(1 for y in el if y["uplift_vs_previous"] > 0)
            pos_par = sum(1 for y in el if y["uplift_vs_parent"] > 0)
            consistent_prev = bool(el) and pos_prev / len(el) >= frac
            consistent_par = bool(el) and pos_par / len(el) >= frac
            flags = []
            identical = bool(i and len(ev) == len(per_step[ladder[i - 1]]["events"]) and
                             (ev["event_time"].to_numpy() == per_step[ladder[i - 1]]["events"]["event_time"].to_numpy()).all())
            if i and not identical:
                if not consistent_prev:
                    flags.append("NO_CONSISTENT_IMPROVEMENT")
                    if len(ev) < int(len(per_step[ladder[i - 1]]["events"])):
                        flags.insert(0, "FREQUENCY_DESTRUCTION")
            rec["targets"][tname] = {
                "effect": eff, "uplift_vs_parent": eff - base_eff, "uplift_vs_previous": eff - prev_eff,
                "retention_vs_parent": len(ev) / len(per_step[base_name]["events"]) if len(per_step[base_name]["events"]) else float("nan"),
                "retention_vs_previous": len(ev) / len(per_step[ladder[i - 1]]["events"]) if i and len(per_step[ladder[i - 1]]["events"]) else 1.0,
                "eligible_years": len(el), "positive_uplift_years_vs_previous": pos_prev, "positive_uplift_years_vs_parent": pos_par,
                "identical_to_previous_step": identical,
                "steady_improvement_vs_previous": consistent_prev if (i and not identical) else None,
                "steady_improvement_vs_parent": consistent_par if i else None,
                "yearly": yearly, "flags": flags}
        steps_out.append(rec)
    return {"label": "DIAGNOSTIC ONLY — NOT A SELECTION TRIAL", "order_frozen": list(ladder), "steps": steps_out}
