"""OOS-only inference clustered by trading week.

* weekly-block bootstrap: trading weeks are resampled with replacement (2000 reps, seed 1729);
* blocked permutation: COMPLETE trading-week outcome blocks are permuted relative to the frozen
  score/state assignments (2000 reps, seed 1729). No event-level IID resampling anywhere.

For a state with sign s (+1 UPPER_HALF, -1 LOWER_HALF) the evaluated outcome is s*y:
  parent effect   = mean(s*y over ALL OOS events)
  selected effect = mean(s*y over events in the state)
  uplift          = selected - parent ;  standardized uplift = uplift / SD(y over OOS parent events)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.score_calibration import LOWER, UPPER

SIGN = {UPPER: 1.0, LOWER: -1.0}


def week_key(event_time, tz: str) -> np.ndarray:
    """ISO year-week of the event's local (exchange) date, e.g. '2020-W03'."""
    local = pd.DatetimeIndex(event_time).tz_convert(tz)
    iso = local.isocalendar()
    return (iso["year"].astype(str) + "-W" + iso["week"].astype(str).str.zfill(2)).to_numpy()


def eligible_weeks(bar_index: pd.DatetimeIndex, oos_years, tz: str) -> int:
    """Distinct trading weeks that have bars inside the OOS years (from bars, NOT from events)."""
    if len(oos_years) == 0:
        return 0
    utc = bar_index.tz_convert("UTC")
    mask = np.isin(utc.year.to_numpy(), list(oos_years))
    return int(len(set(week_key(bar_index[mask], tz))))


def permute_week_blocks(blocks: list[np.ndarray], rng: np.random.Generator) -> np.ndarray:
    """Concatenate COMPLETE trading-week outcome blocks in a random order (within-week order kept)."""
    return np.concatenate([blocks[i] for i in rng.permutation(len(blocks))])


def evaluate_panel(y, state, year, week, event_ns, n_eligible_weeks: float, *, bootstrap_reps: int,
                   permutation_reps: int, seed: int, ci_level: float, min_events_year: int) -> dict[str, dict]:
    """Full statistics for both states of one (target, model) OOS panel. Returns {state: stats}."""
    y = np.asarray(y, dtype="float64")
    state = np.asarray(state)
    year = np.asarray(year)
    order = np.argsort(np.asarray(event_ns), kind="stable")
    y, state, year, week = y[order], state[order], year[order], np.asarray(week)[order]
    n = len(y)
    out: dict[str, dict] = {}
    if n == 0 or n_eligible_weeks <= 0:
        for st in (UPPER, LOWER):
            out[st] = _empty(st)
        return out
    codes, _ = pd.factorize(week)            # chronological first-appearance order
    W = int(codes.max()) + 1
    target_sd = float(np.std(y, ddof=1)) if n > 1 else float("nan")
    ymean = float(y.mean())
    # --- bootstrap shared by both states (same resampled weeks) ---
    rng = np.random.default_rng(seed)
    counts = rng.multinomial(W, np.full(W, 1.0 / W), size=bootstrap_reps).astype("float64")
    n_par_w = np.bincount(codes, minlength=W).astype(float)
    starts = np.flatnonzero(np.r_[True, codes[1:] != codes[:-1]])
    blocks = np.split(y, starts[1:])          # contiguous weekly outcome blocks (events are time-sorted)
    # --- permutations shared by both states ---
    prng = np.random.default_rng(seed)
    sel_masks = {st: state == st for st in (UPPER, LOWER)}
    perm_stat = {st: np.empty(permutation_reps) for st in (UPPER, LOWER)}
    for b in range(permutation_reps):
        yp = permute_week_blocks(blocks, prng)
        for st in (UPPER, LOWER):
            m = sel_masks[st]
            if m.any():
                perm_stat[st][b] = SIGN[st] * (yp[m].mean() - ymean)      # mean(s*yp|sel) - mean(s*y)
            else:
                perm_stat[st][b] = np.nan
    lo_q, hi_q = (1 - ci_level) / 2 * 100, (1 + ci_level) / 2 * 100
    for st in (UPPER, LOWER):
        s = SIGN[st]
        sel = sel_masks[st]
        sv = s * y
        n_sel = int(sel.sum())
        rec = _empty(st)
        rec.update(n_parent=n, n_selected=n_sel, parent_frequency=n / n_eligible_weeks,
                   selected_frequency=n_sel / n_eligible_weeks, retention_ratio=n_sel / n,
                   parent_effect=float(sv.mean()), target_sd=target_sd, n_oos_weeks=float(n_eligible_weeks))
        if n_sel > 0:
            rec["selected_effect"] = float(sv[sel].mean())
            rec["uplift"] = rec["selected_effect"] - rec["parent_effect"]
            rec["standardized_uplift"] = rec["uplift"] / target_sd if target_sd > 0 else float("nan")
            S_sel = np.bincount(codes[sel], weights=sv[sel], minlength=W)
            n_sel_w = np.bincount(codes[sel], minlength=W).astype(float)
            S_par = np.bincount(codes, weights=sv, minlength=W)
            with np.errstate(divide="ignore", invalid="ignore"):
                up_b = (counts @ S_sel) / (counts @ n_sel_w) - (counts @ S_par) / (counts @ n_par_w)
            up_b = up_b[np.isfinite(up_b)]
            if len(up_b):
                rec["bootstrap_ci_low"], rec["bootstrap_ci_high"] = (float(np.percentile(up_b, lo_q)),
                                                                     float(np.percentile(up_b, hi_q)))
            ps = perm_stat[st]
            rec["raw_p"] = float((1 + np.sum(ps >= rec["uplift"] - 1e-15)) / (permutation_reps + 1))
        # year-by-year selected effect (in the candidate direction: > 0 is favourable)
        yearly = []
        for yr in sorted(np.unique(year)):
            m = sel & (year == yr)
            ny = int(m.sum())
            yearly.append({"year": int(yr), "n_selected": ny,
                           "selected_effect": float(sv[m].mean()) if ny else float("nan"),
                           "eligible": ny >= min_events_year})
        rec["yearly"] = yearly
        elig = [r for r in yearly if r["eligible"]]
        rec["eligible_years"] = len(elig)
        rec["positive_years"] = int(sum(1 for r in elig if r["selected_effect"] > 0))
        out[st] = rec
    return out


def _empty(state: str) -> dict:
    nan = float("nan")
    return dict(state=state, n_parent=0, n_selected=0, parent_frequency=nan, selected_frequency=nan,
                retention_ratio=nan, parent_effect=nan, selected_effect=nan, uplift=nan, target_sd=nan,
                standardized_uplift=nan, bootstrap_ci_low=nan, bootstrap_ci_high=nan, raw_p=1.0,
                n_oos_weeks=nan, yearly=[], eligible_years=0, positive_years=0)


def decile_diagnostics(score, y, year, n_eligible_weeks: float) -> dict:
    """DIAGNOSTIC ONLY. Pooled-OOS score deciles (ranks use the whole OOS pool: NOT deployable).

    These bins were not selection trials and cannot promote a candidate.
    """
    score = np.asarray(score, dtype="float64")
    y = np.asarray(y, dtype="float64")
    year = np.asarray(year)
    n = len(score)
    if n < 10:
        return {"deciles": [], "by_year": {}}
    rank = pd.Series(score).rank(method="first").to_numpy()
    dec = np.minimum(((rank - 1) * 10 // n).astype(int), 9) + 1
    rows = [{"decile": d, "n": int((dec == d).sum()),
             "frequency_per_week": float((dec == d).sum() / n_eligible_weeks),
             "mean_target": float(y[dec == d].mean())} for d in range(1, 11)]
    by_year = {}
    for yr in sorted(np.unique(year)):
        m = year == yr
        by_year[int(yr)] = [float(y[m & (dec == d)].mean()) if (m & (dec == d)).any() else float("nan")
                            for d in range(1, 11)]
    return {"deciles": rows, "by_year": by_year}
