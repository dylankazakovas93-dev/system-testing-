"""Event-parameter sensitivity = ROBUSTNESS, never discovery.

Runs only AFTER a development candidate (>= 2 of 3 models pass at a TARGET x SIDE) exists, using the
base event's candidate only. At most 2 designated numeric parameters x {0.75, 1.25} = at most 4 probes,
one parameter at a time. Probes cannot create a candidate, cannot choose a better parameter and cannot
replace the base parameter: they can only CONFIRM or VETO. A probe that performs better is merely reported.

Probe rules (mirroring the 2-of-3 model agreement, written in ACCEPTANCE_RULES.yaml):
  * a probe REVERSES the uplift sign if fewer than 2 of the 3 models have positive uplift in the
    candidate state;
  * a probe fails FREQUENCY if fewer than 2 of the 3 models keep selected OOS frequency >= 1.0/week.
A candidate FAILS if more than one probe reverses the sign or any probe fails frequency.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.common import EngineError, Frozen


def probe_value(base_value, multiplier: float):
    """Scale a base parameter. Integers are rounded half-up (validated >= 3 at freeze so both probes differ)."""
    v = base_value * multiplier
    if isinstance(base_value, int) and not isinstance(base_value, bool):
        return max(1, int(np.floor(v + 0.5)))
    return float(v)


def probe_grid(spec: dict, frozen: Frozen) -> list[dict]:
    params = spec["base_parameters"]
    names = list(spec.get("sensitivity_parameters") or [])
    if len(names) > frozen.trial_policy["sensitivity"]["max_parameters"]:
        raise EngineError("too many sensitivity parameters")
    mults = frozen.trial_policy["sensitivity"]["multipliers"]
    grid = []
    for n in names:
        for m in mults:
            grid.append({"parameter": n, "multiplier": m, "base": params[n], "value": probe_value(params[n], m)})
    assert len(grid) <= frozen.trial_policy["sensitivity"]["max_probes"]
    return grid


def judge_group(probes: list[dict], acc: dict) -> dict:
    s = acc["sensitivity"]
    reversing = [p for p in probes if p["models_positive_uplift"] < acc["model_agreement"]["min_models_passing"]]
    freq_fail = [p for p in probes if p["models_frequency_ok"] < acc["model_agreement"]["min_models_passing"]]
    failed = len(reversing) > s["max_reversing_probes"] or len(freq_fail) > 0
    return {"verdict": "FAILED" if failed else "PASSED", "n_reversing_probes": len(reversing),
            "n_frequency_failures": len(freq_fail), "probes": probes}


def run_sensitivity(module, spec: dict, bars_dev: pd.DataFrame, frozen: Frozen, pending_rows: pd.DataFrame) -> dict:
    """pending_rows: trial rows of candidate groups awaiting sensitivity (decision PROMOTABLE_PENDING_SENSITIVITY)."""
    from engine.experiment_runner import build_event_tables, run_panels
    groups = sorted({(r.target, r.state) for r in pending_rows.itertuples()})
    grid = probe_grid(spec, frozen)
    if not grid:
        return {"status": "SKIPPED_NO_PARAMETERS",
                "groups": {f"{t}|{s}": {"verdict": "SKIPPED_NO_PARAMETERS", "probes": []} for t, s in groups}}
    by_group: dict[tuple, list[dict]] = {g: [] for g in groups}
    targets_needed = sorted({t for t, _ in groups})
    for probe in grid:
        params = dict(spec["base_parameters"])
        params[probe["parameter"]] = probe["value"]
        events, features, eligible, targets, _ = build_event_tables(module, spec, bars_dev, frozen, params)
        panels = run_panels(events, features, targets, eligible, bars_dev.index, frozen,
                            target_names=targets_needed, point_only=True) if eligible.any() else {}
        for (target, state) in groups:
            per_model = []
            for m in ("RIDGE", "SPLINE", "XGB"):
                p = panels.get((target, m))
                st = p.stats[state] if p else None
                per_model.append({"model": m,
                                  "uplift": float(st["uplift"]) if st else float("nan"),
                                  "standardized_uplift": float(st["standardized_uplift"]) if st else float("nan"),
                                  "selected_frequency": float(st["selected_frequency"]) if st else float("nan"),
                                  "n_selected": int(st["n_selected"]) if st else 0})
            by_group[(target, state)].append({
                **probe, "n_events": int(len(events)),
                "models": per_model,
                "models_positive_uplift": int(sum(1 for x in per_model if np.isfinite(x["uplift"]) and x["uplift"] > 0)),
                "models_frequency_ok": int(sum(1 for x in per_model if np.isfinite(x["selected_frequency"])
                                               and x["selected_frequency"] >= frozen.acceptance["sensitivity"]["min_probe_frequency_per_week"]))})
    return {"status": "RUN", "groups": {f"{t}|{s}": judge_group(pr, frozen.acceptance) for (t, s), pr in by_group.items()}}
