"""Test helpers: small hand-built bar frames and independent (pure-python) reference formulas."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from engine.common import load_frozen

FROZEN = load_frozen()


def make_bars(closes, opens=None, highs=None, lows=None, volumes=None, start="2020-01-07 14:31:00+00:00"):
    """Open-stamped 1-minute bars. Default open_i = close_(i-1) (first open = first close)."""
    closes = list(map(float, closes))
    n = len(closes)
    if opens is None:
        opens = [closes[0]] + closes[:-1]
    if highs is None:
        highs = [max(o, c) + 0.5 for o, c in zip(opens, closes)]
    if lows is None:
        lows = [min(o, c) - 0.5 for o, c in zip(opens, closes)]
    if volumes is None:
        volumes = [100.0] * n
    idx = pd.date_range(start, periods=n, freq="1min")
    return pd.DataFrame({"open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes}, index=idx)


def events_at(bars: pd.DataFrame, positions, direction=1) -> pd.DataFrame:
    """Events whose signal bar is bars[pos]; event_time = its close time (open + 1 minute)."""
    t = bars.index[list(positions)] + pd.Timedelta("1min")
    return pd.DataFrame({"event_id": [f"E{i}" for i in range(len(t))], "event_time": t,
                         "direction": direction})


# ---- independent reference implementations (plain python / math) -------------------------
def ref_ret(c, t, L):
    return math.log(c[t] / c[t - L])


def ref_rets(c, t, L):
    return [math.log(c[i] / c[i - 1]) for i in range(t - L + 1, t + 1)]


def ref_rv(c, t, L):
    return math.sqrt(sum(r * r for r in ref_rets(c, t, L)))


def ref_er(c, t, L):
    den = sum(abs(c[i] - c[i - 1]) for i in range(t - L + 1, t + 1))
    return float("nan") if den == 0 else abs(c[t] - c[t - L]) / den


def ref_disp(c, t, L):
    rs = ref_rets(c, t, L)
    den = math.sqrt(sum(r * r for r in rs))
    return float("nan") if den == 0 else sum(rs) / den


def _pvar(xs):
    m = sum(xs) / len(xs)
    return sum((x - m) ** 2 for x in xs) / len(xs)


def ref_vr(c, t, W, q):
    x = [math.log(v) for v in c[t - W + 1: t + 1]]          # W log closes
    one = [x[i] - x[i - 1] for i in range(1, W)]
    qs, end = [], W - 1
    while end - q >= 0:
        qs.append(x[end] - x[end - q])
        end -= q
    den = q * _pvar(one)
    return float("nan") if den == 0 else _pvar(qs) / den


def ref_hurst(c, t, W, lags=(1, 2, 4, 8, 16)):
    x = [math.log(v) for v in c[t - W + 1: t + 1]]
    pts = []
    for k in lags:
        d = [(x[i] - x[i - k]) ** 2 for i in range(k, W)]
        v = sum(d) / len(d)
        if v > 0:
            pts.append((math.log(k), math.log(v)))
    if len(pts) < 4:
        return float("nan")
    mx = sum(p[0] for p in pts) / len(pts)
    my = sum(p[1] for p in pts) / len(pts)
    b = sum((p[0] - mx) * (p[1] - my) for p in pts) / sum((p[0] - mx) ** 2 for p in pts)
    return b / 2.0


def ref_count_balance(o, c, t, L):
    s = 0
    for i in range(t - L + 1, t + 1):
        s += int(c[i] > o[i]) - int(c[i] < o[i])
    return s / L


def ref_body_balance(o, c, t, L):
    num = sum(c[i] - o[i] for i in range(t - L + 1, t + 1))
    den = sum(abs(c[i] - o[i]) for i in range(t - L + 1, t + 1))
    return float("nan") if den == 0 else num / den


def ref_range_pos(h, l, c, t, L):
    hi = max(h[t - L + 1: t + 1])
    lo = min(l[t - L + 1: t + 1])
    return 0.5 if hi == lo else (c[t] - lo) / (hi - lo)


def ref_tr(h, l, c, i):
    return max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))


def ref_vov(h, l, c, t, L):
    trs = [ref_tr(h, l, c, i) for i in range(t - L + 1, t + 1)]
    return math.sqrt(_pvar(trs))


def ref_signed_volume(o, c, v, t, L):
    num = sum((int(c[i] > o[i]) - int(c[i] < o[i])) * v[i] for i in range(t - L + 1, t + 1))
    den = sum(v[t - L + 1: t + 1])
    return float("nan") if den == 0 else num / den


def random_bars(n=900, seed=3, start="2020-01-07 14:31:00+00:00", vol=0.0004):
    rng = np.random.default_rng(seed)
    r = rng.normal(0, vol, n)
    close = 10000 * np.exp(np.cumsum(r))
    open_ = np.concatenate([[10000.0], close[:-1]])
    hi = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, vol / 3, n)))
    lo = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, vol / 3, n)))
    v = rng.integers(50, 500, n).astype(float)
    idx = pd.date_range(start, periods=n, freq="1min")
    return pd.DataFrame({"open": open_, "high": hi, "low": lo, "close": close, "volume": v}, index=idx)
