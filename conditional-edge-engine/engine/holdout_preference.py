"""Deterministic, ADVISORY holdout preference between configurations frozen before the selection holdout opened.

The engine never makes the human decision. It reports HOLDOUT_PREFERRED_CONFIG, HOLDOUT_UNRESOLVED or NO_QUALIFYING_CONFIG using only the
frozen rule in SELECTION_PROCESS.yaml. This module is deliberately free of any path/bracket-diagnostic import: diagnostics never enter the preference.
"""
from __future__ import annotations

import numpy as np

from engine.common import Frozen
from engine.near_tie import paired_difference


def qualifies(model_rows: list[dict], min_freq: float) -> tuple[bool, list[str]]:
    """selected effect > 0, frequency >= 1/week (group medians) and at least 2 of 3 models with positive uplift."""
    why = []
    eff = float(np.nanmedian([r["selected_effect"] for r in model_rows])) if model_rows else float("nan")
    freq = float(np.nanmedian([r["selected_frequency"] for r in model_rows])) if model_rows else float("nan")
    npos = sum(1 for r in model_rows if r["uplift"] is not None and np.isfinite(r["uplift"]) and r["uplift"] > 0)
    if not eff > 0:
        why.append(f"median selected effect {eff:+.5f} <= 0")
    if not freq >= min_freq:
        why.append(f"median selected frequency {freq:.3f}/week < {min_freq}")
    if npos < 2:
        why.append(f"only {npos} of {len(model_rows)} models have positive uplift (need >= 2)")
    return (not why), why


def holdout_preference(configs: list[dict], frozen: Frozen, series_of=None) -> dict:
    """configs: [{config_id, is_rank, model_rows:[{model, selected_effect, selected_frequency, uplift, standardized_uplift}]}].
    ``series_of(config_id)`` -> list of (week_keys, y, selected_mask, sign, target_sd) per model (for the paired unresolved test)."""
    sp = frozen.selection_process
    nt = sp["near_tie"]
    min_freq = frozen.acceptance["selection_holdout_evidence"]["min_selected_frequency_per_week"]
    cards = []
    for c in configs:
        ok, why = qualifies(c["model_rows"], min_freq)
        cards.append({"config_id": c["config_id"], "is_rank": c["is_rank"], "qualifies": ok, "disqualified_because": why,
                      "median_standardized_uplift": float(np.nanmedian([r["standardized_uplift"] for r in c["model_rows"]])),
                      "median_selected_effect": float(np.nanmedian([r["selected_effect"] for r in c["model_rows"]])),
                      "median_selected_frequency": float(np.nanmedian([r["selected_frequency"] for r in c["model_rows"]]))})
    qual = sorted([c for c in cards if c["qualifies"]],
                  key=lambda c: (-c["median_standardized_uplift"], -c["median_selected_effect"], -c["median_selected_frequency"], c["is_rank"], c["config_id"]))
    out = {"rule": sp["holdout_preference"]["rank_by"], "cards": cards, "ranking": [c["config_id"] for c in qual], "pair_test": None}
    if not qual:
        return {**out, "status": "NO_QUALIFYING_CONFIG", "holdout_preferred_config": None,
                "note": "no frozen config meets the preference requirements in the selection holdout; the engine fabricates no winner"}
    leader = qual[0]["config_id"]
    if len(qual) >= 2 and series_of is not None:
        a, b = qual[0], qual[1]
        diff = a["median_standardized_uplift"] - b["median_standardized_uplift"]
        pair = {"a": a["config_id"], "b": b["config_id"], "abs_diff": abs(diff)}
        if abs(diff) <= nt["max_abs_diff_median_standardized_uplift"]:
            pb = nt["paired_bootstrap"]
            pd_ = paired_difference(series_of(a["config_id"]), series_of(b["config_id"]), reps=pb["repetitions"], seed=pb["seed"], ci_level=pb["ci_level"])
            pair.update({"ci_low": pd_["ci_low"], "ci_high": pd_["ci_high"], "ci_contains_zero": pd_["ci_contains_zero"], "paired_difference": pd_["difference"]})
        out["pair_test"] = pair
        if pair.get("ci_contains_zero"):
            return {**out, "status": "HOLDOUT_UNRESOLVED", "holdout_preferred_config": None, "ranking_leader_advisory": leader,
                    "note": "the two configs remain statistically close in the selection holdout (same frozen near-tie rule); no winner is fabricated"}
    return {**out, "status": "HOLDOUT_PREFERRED_CONFIG", "holdout_preferred_config": leader,
            "note": "ADVISORY: the human still chooses the final configuration (or declines)"}
