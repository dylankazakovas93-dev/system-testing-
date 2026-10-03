"""Path / bracket diagnostics of the SELECTION HOLDOUT (SELECTION DATA — NOT FINAL CONFIRMATION).

Unlike the IS diagnostics, the human MAY inspect these when choosing among the configurations that were frozen before the holdout opened.
They cannot create a new config, change a threshold, add a bracket to the final config or alter a model parameter, and they do not enter the
deterministic holdout preference (engine/holdout_preference.py). Only holdout events (development_end <= event_time < selection_holdout_end);
bars passed in are already cut at selection_holdout_end, so no lockbox row is read.
"""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd

from engine import path_diagnostics as pdx
from engine.common import Frozen, utc_ns
from engine.path_engine import sigma_ref
from engine.statistics import weeks_in_intervals


def holdout_path_diagnostics(bars: pd.DataFrame, events: pd.DataFrame, features: pd.DataFrame, eligible: np.ndarray, selected: dict[str, set],
                             parts, frozen: Frozen) -> dict:
    """``selected['<config_id>|<MODEL>']`` = set of holdout event_ids put in that config's state by that model."""
    spec = frozen.path_diagnostics
    ev = events.assign(_el=np.asarray(eligible, dtype=bool), _sigma=sigma_ref(features["RV_60"].to_numpy()))
    et = pd.DatetimeIndex(ev["event_time"]).tz_convert("UTC")
    ev = ev[ev["_el"] & (et >= parts.development_end) & (et < parts.selection_holdout_end)].sort_values(["event_time", "event_id"], kind="stable").reset_index(drop=True)
    if not len(ev):
        return {"status": "NO_HOLDOUT_EVENTS"}
    T = pdx.make_paths(bars, ev, ev["_sigma"].to_numpy(), frozen)
    etime = pd.DatetimeIndex(ev["event_time"]).tz_convert("UTC")
    years = etime.year.to_numpy()
    folds = np.zeros(len(ev), dtype=int)
    wk = weeks_in_intervals(bars.index, [(int(parts.development_end.value), int(parts.selection_holdout_end.value))], frozen.tz)
    pos = {e: i for i, e in enumerate(ev["event_id"])}
    ctx = {"ALL_HOLDOUT_EVENTS": {"mask": np.ones(len(ev), dtype=bool), "weeks_total": wk["total"], "weeks_by_year": wk["by_year"]}}
    for name, ids in sorted(selected.items()):
        m = np.zeros(len(ev), dtype=bool)
        for eid in ids:
            if eid in pos:
                m[pos[eid]] = True
        ctx[name] = {"mask": m, "weeks_total": wk["total"], "weeks_by_year": wk["by_year"]}
    surfaces = pdx.bracket_surface(T, ctx, years, folds, spec)
    contexts = {}
    for name, c in ctx.items():
        payload = pdx._ctx_payload(T, c["mask"], years, folds, c["weeks_total"], c["weeks_by_year"], {}, frozen, spec)
        payload["bracket_surface"] = surfaces[name]
        contexts[name] = payload
    return {"status": "COMPUTED", "label": "SELECTION DATA — USED TO CHOOSE FINAL CONFIGURATION / NOT FINAL CONFIRMATION",
            "diagnostic_statement": " ".join(spec["diagnostic_statement"].split()),
            "use_rule": "may inform the HUMAN's choice among configs frozen before the holdout opened; cannot create a config, change a threshold, add a bracket to the final config or alter a model parameter",
            "cost_banner": spec["bracket_surface"]["cost_banner"], "selection_banner": spec["bracket_surface"]["selection_banner"],
            "n_bracket_cells": len(pdx.bracket_cell_defs(spec)), "sigma_ref_formula": spec["sigma_ref"]["formula"],
            "n_holdout_events": int(len(ev)), "contexts": contexts}


def compact(rep: dict, name: str) -> dict:
    """Small per-config/model digest for the report (full detail stays in the JSON file)."""
    c = (rep.get("contexts") or {}).get(name)
    if not c:
        return {}
    cells = c["bracket_surface"]
    npos = sum(1 for x in cells if x.get("mean_gross_points") is not None and x["mean_gross_points"] > 0)
    h = c["continuation"].get(60) or c["continuation"].get("60")
    ex = c["excursions"].get(60) or c["excursions"].get("60")
    return {"n_events": c["n_events"], "continuation_60": h["continuation"], "reversal_60": h["reversal"],
            "median_MFE_points_60": ex["MFE"]["points"]["median"], "median_abs_MAE_points_60": ex["ADVERSE_ABS_MAE"]["points"]["median"],
            "bracket_cells_positive_mean_gross": npos, "bracket_cells": len(cells)}


def sha(txt: str) -> str:
    return hashlib.sha256(txt.encode()).hexdigest()
