
import numpy as np
import pandas as pd


def detect_events(bars, params):
    step = int(params["every_n_bars"])
    flip = int(params["direction_period"])
    interval = pd.Timedelta(bars.attrs["bar_interval"])
    keep = np.arange(len(bars)) % step == 0
    n = int(keep.sum())
    direction = np.where(np.arange(n) % flip == 0, 1, -1) if flip > 1 else np.full(n, int(params["direction"]))
    return pd.DataFrame({"event_time": bars.index[keep] + interval, "direction": direction})
