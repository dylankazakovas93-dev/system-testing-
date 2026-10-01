"""EVENT DEFINITION (template): confirmed pivot translated from reference.pine. SINGLE DIRECTION per experiment.

This file is one of only four files the event-writing LLM/user may edit:
HYPOTHESIS.md, EVENT_SPEC.yaml, event.py, reference.pine.

Contract: detect_events(bars, params) -> DataFrame[event_time, direction]   (ALL rows share one direction, v1 rule)
Optional: detect_events_ladder(bars, params) -> {step: DataFrame} implementing EVENT_SPEC.filter_ladder (diagnostics only).
A bidirectional indicator becomes two experiments: params["direction"] = 1 (pivot lows -> long) and = -1 (pivot highs -> short).
  * Every numeric threshold comes from params[...] (registered in EVENT_SPEC.yaml). Literals other
    than 0 and 1 are rejected by the static scan.
  * event_time is an INFORMATION time: the completion time (open + interval) of the last bar needed
    to know the event. A pivot that needs `pivot_right` right-hand bars is only knowable once the
    `pivot_right`-th bar after the pivot bar has closed; the plotted pivot location is NOT event_time.
"""
import numpy as np
import pandas as pd


def detect_events(bars, params):
    left = int(params["pivot_left"])
    right = int(params["pivot_right"])
    side = int(params["direction"])                      # +1: confirmed pivot LOW -> long ; -1: confirmed pivot HIGH -> short
    interval = pd.Timedelta(bars.attrs["bar_interval"])
    n = len(bars)
    if n < left + right + 1:
        return pd.DataFrame({"event_time": pd.to_datetime([], utc=True), "direction": np.array([], dtype=int)})
    low = bars["low"].to_numpy(dtype=float)
    high = bars["high"].to_numpy(dtype=float)
    lo, hi = pd.Series(low), pd.Series(high)
    # trailing rolling extrema: value[j] covers bars j-window+1 .. j  (O(n), no future access by itself)
    min_left, max_left = lo.rolling(left).min().to_numpy(), hi.rolling(left).max().to_numpy()
    min_right, max_right = lo.rolling(right).min().to_numpy(), hi.rolling(right).max().to_numpy()
    i = np.arange(left, n - right)                       # candidate pivot bars with full left/right context
    # left context  = bars i-left .. i-1   -> trailing window ending at i-1
    # right context = bars i+1 .. i+right  -> trailing window ending at i+right (known only once that bar closes)
    pivot_low = (low[i] < min_left[i - 1]) & (low[i] <= min_right[i + right])      # strict left, non-strict right
    pivot_high = (high[i] > max_left[i - 1]) & (high[i] >= max_right[i + right])
    mask = pivot_low if side == 1 else pivot_high
    t = bars.index[i + right][mask] + interval           # known when the last right-hand bar CLOSES
    return pd.DataFrame({"event_time": t, "direction": np.full(int(mask.sum()), side)})
