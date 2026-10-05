"""WHERE IT WORKS / WHERE IT DOES NOT: a DESCRIPTIVE map of an eligible TARGET x SIDE group's out-of-fold behaviour (v2).

Built only from the pooled DEVELOPMENT_CV validation panels (``cv_<target>_<model>.csv``, out-of-fold by construction): per bucket the
selected-half mean directional outcome minus the mean over ALL events of that bucket (the same uplift definition the trials use), median over the
group's eligible models. Buckets: calendar year, exchange-local hour of the event, and full-horizon vs session-truncated windows.

This is a REPORT, never a selection step: it creates no trial, changes no status or ranking and cannot choose a region. A region that looks
attractive can only become a NEW pre-registered experiment.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.common import Frozen
from engine.experiment_lifecycle import experiment_dir

LABEL = "DESCRIPTIVE — NOT A SELECTION TRIAL"


def _bucket_rows(df: pd.DataFrame, sign: float, state: str, key: np.ndarray, min_n: int) -> dict:
    v = sign * df["y"].to_numpy("float64")
    sel = (df["state"] == state).to_numpy()
    out = {}
    for k in sorted(set(key.tolist())):
        m = key == k
        ms = m & sel
        out[k] = {"n_events": int(m.sum()), "n_selected": int(ms.sum()),
                  "uplift": float(v[ms].mean() - v[m].mean()) if ms.any() else float("nan"),
                  "selected_effect": float(v[ms].mean()) if ms.any() else float("nan")}
    return out


def group_map(ws, experiment_id: str, group: dict, frozen: Frozen) -> dict:
    d = experiment_dir(ws, experiment_id) / "results"
    sign = 1.0 if group["state"] == "UPPER_HALF" else -1.0
    min_n = frozen.acceptance["year_consistency"]["min_selected_events_for_eligible_year"]
    per_model = {"year": [], "hour": [], "horizon": []}
    for m in group["models"]:
        cv = pd.read_csv(d / f"cv_{group['target']}_{m}.csv")
        et = pd.DatetimeIndex(pd.to_datetime(cv["event_time"], utc=True))
        trunc = cv["truncated"].astype(bool).to_numpy() if "truncated" in cv.columns else np.zeros(len(cv), dtype=bool)
        keys = {"year": et.year.astype(str).to_numpy(),
                "hour": np.asarray([f"{h:02d}:00" for h in et.tz_convert(frozen.tz).hour]),
                "horizon": np.where(trunc, "truncated_at_session_close", "full_horizon")}
        for dim in per_model:
            per_model[dim].append(_bucket_rows(cv, sign, group["state"], keys[dim], min_n))
    out = {}
    for dim, rows in per_model.items():
        buckets = sorted(set().union(*[set(r) for r in rows]))
        table = []
        for b in buckets:
            ups = [r[b]["uplift"] for r in rows if b in r and np.isfinite(r[b]["uplift"])]
            ns = [r[b]["n_selected"] for r in rows if b in r]
            up = float(np.median(ups)) if ups else float("nan")
            n = int(np.median(ns)) if ns else 0
            table.append({"bucket": b, "n_events": int(np.median([r[b]["n_events"] for r in rows if b in r])), "median_n_selected": n,
                          "median_uplift": up, "sample_ok": bool(n >= min_n),
                          "verdict": ("too few selected events" if n < min_n else "works (uplift > 0)" if up > 0 else "does NOT work (uplift <= 0)")})
        out[dim] = table
    return {"group_id": group["group_id"], "models": list(group["models"]), "label": LABEL, "min_selected_events_for_a_verdict": min_n, **out}


def build(ws, experiment_id: str, groups: list[dict], frozen: Frozen) -> dict:
    res = {"label": LABEL, "note": "Out-of-fold DEVELOPMENT_CV events only. A report, not a selection step: any region worth trading is a NEW pre-registered experiment.",
           "groups": {}}
    for g in groups:
        if all((experiment_dir(ws, experiment_id) / "results" / f"cv_{g['target']}_{m}.csv").exists() for m in g["models"]):
            res["groups"][g["group_id"]] = group_map(ws, experiment_id, g, frozen)
    res["available"] = bool(res["groups"])
    return res


def render(wm: dict, fmt) -> list[str]:
    L = [f"**{wm['label']}.** {wm['note']}\n"]
    if not wm["available"]:
        return L + ["Not available (no DEVELOPMENT_CV panels on disk for this run).\n"]
    for gid, g in wm["groups"].items():
        L.append(f"### {gid}\n")
        for dim, title in (("year", "by calendar year"), ("hour", "by exchange-local hour of the event"), ("horizon", "full horizon vs truncated at the session close")):
            L.append(f"{title}:\n")
            L.append("| bucket | events | median selected events | median uplift | verdict |")
            L.append("|---|---|---|---|---|")
            for r in g[dim]:
                L.append(f"| {r['bucket']} | {r['n_events']} | {r['median_n_selected']} | {fmt(r['median_uplift'])} | {r['verdict']} |")
            L.append("")
    return L
