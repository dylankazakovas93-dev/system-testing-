"""Event-parameter sensitivity = ROBUSTNESS, never discovery.

Runs only AFTER a development candidate (>= 2 of 3 models pass at a TARGET x SIDE) exists, using the
base event's candidate only. v2.3.0: EVERY probeable numeric base parameter (floats, integers >= 3) x {0.75, 1.25},
one parameter at a time. Probes cannot create a candidate, cannot choose a better parameter and cannot
replace the base parameter: they can only CONFIRM or VETO. A probe that performs better is merely reported.

Probe rules (mirroring the 2-of-3 model agreement, written in ACCEPTANCE_RULES.yaml). A model is OK at a probe when
  * its selected effect in the candidate state stays > 0,
  * its standardized uplift keeps at least ``min_retained_uplift_fraction`` (0.5) of its BASE standardized uplift, and
  * its selected frequency stays >= 1.0/week.
A probe is OK when at least 2 of the 3 models are OK. The candidate FAILS if more than ``max_failing_probes`` (0) probes are not OK.
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


def is_probeable(value) -> bool:
    """x0.75 and x1.25 give different values: floats (non-zero) and integers >= 3 (see event_contract)."""
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return value >= 3
    return value != 0


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
    need = acc["model_agreement"]["min_models_passing"]
    failing = [p for p in probes if p["models_ok"] < need]
    reversing = [p for p in probes if p["models_positive_effect"] < need]
    weakened = [p for p in probes if p["models_retained_uplift"] < need]
    freq_fail = [p for p in probes if p["models_frequency_ok"] < need]
    failed = len(failing) > s["max_failing_probes"]
    return {"verdict": "FAILED" if failed else "PASSED", "n_failing_probes": len(failing), "n_effect_not_positive": len(reversing),
            "n_uplift_below_retention": len(weakened), "n_frequency_failures": len(freq_fail), "probes": probes}


def run_sensitivity(module, spec: dict, bars_dev: pd.DataFrame, frozen: Frozen, pending_rows: pd.DataFrame) -> dict:
    """pending_rows: trial rows of candidate groups awaiting sensitivity (decision PROMOTABLE_PENDING_SENSITIVITY)."""
    from engine.experiment_runner import build_event_tables, run_panels
    groups = sorted({(r.target, r.state) for r in pending_rows.itertuples()})
    grid = probe_grid(spec, frozen)
    if not grid:
        return {"status": "SKIPPED_NO_PARAMETERS",
                "groups": {f"{t}|{s}": {"verdict": "SKIPPED_NO_PARAMETERS", "probes": []} for t, s in groups}}
    acc_s = frozen.acceptance["sensitivity"]
    base_uplift = {(r.target, r.state, r.model): float(r.standardized_uplift) for r in pending_rows.itertuples()
                   if hasattr(r, "model") and hasattr(r, "standardized_uplift")}
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
                                  "selected_effect": float(st["selected_effect"]) if st else float("nan"),
                                  "base_standardized_uplift": base_uplift.get((target, state, m), float("nan")),
                                  "uplift": float(st["uplift"]) if st else float("nan"),
                                  "standardized_uplift": float(st["standardized_uplift"]) if st else float("nan"),
                                  "selected_frequency": float(st["selected_frequency"]) if st else float("nan"),
                                  "n_selected": int(st["n_selected"]) if st else 0})
            def eff_ok(x):
                return np.isfinite(x["selected_effect"]) and x["selected_effect"] > acc_s["selected_effect_must_exceed"]

            def keep_ok(x):
                b, u = x["base_standardized_uplift"], x["standardized_uplift"]
                return bool(np.isfinite(b) and np.isfinite(u) and b > 0 and u >= acc_s["min_retained_uplift_fraction"] * b)

            def freq_ok(x):
                return np.isfinite(x["selected_frequency"]) and x["selected_frequency"] >= acc_s["min_probe_frequency_per_week"]
            by_group[(target, state)].append({
                **probe, "n_events": int(len(events)),
                "models": per_model,
                "models_positive_effect": int(sum(eff_ok(x) for x in per_model)),
                "models_retained_uplift": int(sum(keep_ok(x) for x in per_model)),
                "models_frequency_ok": int(sum(freq_ok(x) for x in per_model)),
                "models_ok": int(sum(eff_ok(x) and keep_ok(x) and freq_ok(x) for x in per_model))})
    return {"status": "RUN", "groups": {f"{t}|{s}": judge_group(pr, frozen.acceptance) for (t, s), pr in by_group.items()}}
