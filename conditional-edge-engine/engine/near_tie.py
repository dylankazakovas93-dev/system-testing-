"""Near-tie / configuration-uncertainty detection (frozen/v1/SELECTION_PROCESS.yaml).  DIAGNOSTIC for the HUMAN, never a selection trial.

Two TARGET x SIDE groups of the SAME experiment form a NEAR_TIE iff
  1. both are IS_SHORTLIST_ELIGIBLE groups (>= 2 of 3 eligible models; the existing ``rank_groups`` set),
  2. they have the same side (UPPER_HALF with UPPER_HALF, LOWER_HALF with LOWER_HALF),
  3. |median standardized uplift(A) - median standardized uplift(B)| <= 0.03,
  4. the paired weekly-block bootstrap CI (2000 repetitions, seed 1729, 95%) of  median_std_uplift(A) - median_std_uplift(B)  contains 0,
computed on the SAME DEVELOPMENT_CV validation observations (no holdout or lockbox byte). Near-tie edges form connected clusters; members are
ranked by the EXISTING frozen IS group ranking (no new ranking metric) and only the top 2 of a cluster may be proposed for the selection holdout.
Nothing here creates a selection trial, promotes a rejected configuration or changes any status/ranking: it only reports uncertainty.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine import trial_registry as reg
from engine.acceptance import rank_groups
from engine.common import Frozen, load_frozen
from engine.experiment_lifecycle import experiment_dir
from engine.statistics import week_key


def config_id(experiment_id: str, group_id: str) -> str:
    return f"{experiment_id}|{group_id}"


def split_config_id(cid: str) -> tuple[str, str]:
    exp, rest = cid.split("|", 1)
    return exp, rest


def week_arrays(week_keys: np.ndarray, y: np.ndarray, sel: np.ndarray, sign: float, weeks: np.ndarray) -> np.ndarray:
    """(W, 4) per-week [n_parent, sum_parent, n_selected, sum_selected] of the directional target (sign = +1 UPPER, -1 LOWER)."""
    idx = pd.Index(weeks).get_indexer(week_keys)
    out = np.zeros((len(weeks), 4))
    v = sign * y
    np.add.at(out[:, 0], idx, 1.0)
    np.add.at(out[:, 1], idx, v)
    np.add.at(out[:, 2], idx, sel.astype(float))
    np.add.at(out[:, 3], idx, np.where(sel, v, 0.0))
    return out


def _stat(counts: np.ndarray, sd: float) -> np.ndarray:
    """standardized uplift per replicate: counts (R, 4) of [n_par, sum_par, n_sel, sum_sel]."""
    with np.errstate(divide="ignore", invalid="ignore"):
        return (counts[:, 3] / counts[:, 2] - counts[:, 1] / counts[:, 0]) / sd


def paired_difference(series_a: list[tuple], series_b: list[tuple], *, reps: int, seed: int, ci_level: float) -> dict:
    """series_x = [(week_keys, y, selected_mask, sign, target_sd), ...] one tuple per ELIGIBLE model of group x.
    Returns the point difference of group median standardized uplifts and the paired weekly-block percentile CI."""
    all_weeks = np.array(sorted({w for s in (*series_a, *series_b) for w in set(s[0].tolist())}))
    W = len(all_weeks)
    A = [week_arrays(s[0], s[1], s[2], s[3], all_weeks) for s in series_a]
    B = [week_arrays(s[0], s[1], s[2], s[3], all_weeks) for s in series_b]
    sdA, sdB = [s[4] for s in series_a], [s[4] for s in series_b]

    def group_stat(blocks, sds, weights):                          # weights (R, W)
        stats = np.stack([_stat(weights @ b, sd) for b, sd in zip(blocks, sds)])     # (models, R)
        return np.nanmedian(stats, axis=0)
    ones = np.ones((1, W))
    point = float(group_stat(A, sdA, ones)[0] - group_stat(B, sdB, ones)[0])
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, W, size=(reps, W))
    weights = np.zeros((reps, W))
    for r in range(reps):
        weights[r] = np.bincount(draws[r], minlength=W)
    diff = group_stat(A, sdA, weights) - group_stat(B, sdB, weights)
    diff = diff[np.isfinite(diff)]
    lo, hi = np.percentile(diff, [100 * (1 - ci_level) / 2, 100 * (1 + ci_level) / 2])
    return {"difference": point, "ci_low": float(lo), "ci_high": float(hi), "ci_contains_zero": bool(lo <= 0.0 <= hi),
            "n_weeks": int(W), "repetitions": reps, "seed": seed}


def _series(ws, experiment_id: str, group: dict, rows: list[dict], frozen: Frozen) -> list[tuple]:
    d = experiment_dir(ws, experiment_id) / "results"
    sign = 1.0 if group["state"] == "UPPER_HALF" else -1.0
    out = []
    for m in group["models"]:                                       # the eligible models of the group (same set as its median)
        cv = pd.read_csv(d / f"cv_{group['target']}_{m}.csv")
        et = pd.DatetimeIndex(pd.to_datetime(cv["event_time"], utc=True))
        sd = next(float(r["target_sd"]) for r in rows if r["target"] == group["target"] and r["model"] == m and r["state"] == group["state"])
        out.append((week_key(et, frozen.tz), cv["y"].to_numpy("float64"), (cv["state"] == group["state"]).to_numpy(), sign, sd))
    return out


def detect(ws: reg.Workspace, experiment_id: str, frozen: Frozen | None = None) -> dict:
    """Deterministic near-tie pairs and clusters of the experiment's CURRENT IS-eligible groups (re-derived on demand)."""
    frozen = frozen or load_frozen()
    nt = frozen.selection_process["near_tie"]
    pb = nt["paired_bootstrap"]
    rows = reg.experiment_trials(ws, experiment_id).to_dict("records")
    ranked = rank_groups(rows, frozen.acceptance, top=10**6)
    res = {"experiment_id": experiment_id, "rule": {"max_abs_diff": nt["max_abs_diff_median_standardized_uplift"], "reps": pb["repetitions"],
                                                     "seed": pb["seed"], "ci_level": pb["ci_level"]},
           "eligible_groups": [{**g, "config_id": config_id(experiment_id, g["group_id"])} for g in ranked], "pairs": [], "clusters": [],
           "available": True}
    d = experiment_dir(ws, experiment_id) / "results"
    if len(ranked) < 2:
        return res                                                    # nothing to compare: no near tie is possible
    if not all((d / f"cv_{g['target']}_{m}.csv").exists() for g in ranked for m in g["models"]):
        res["available"] = False                                      # table-level runs without CV panels on disk
        return res
    edges = []
    for i, a in enumerate(ranked):
        for b in ranked[i + 1:]:
            if a["state"] != b["state"]:
                continue                                              # opposite sides never form a cluster
            diff = a["median_standardized_uplift"] - b["median_standardized_uplift"]
            rec = {"a": config_id(experiment_id, a["group_id"]), "b": config_id(experiment_id, b["group_id"]), "side": a["state"],
                   "uplift_a": a["median_standardized_uplift"], "uplift_b": b["median_standardized_uplift"], "abs_diff": abs(diff),
                   "near_tie": False}
            if abs(diff) <= nt["max_abs_diff_median_standardized_uplift"]:
                pd_ = paired_difference(_series(ws, experiment_id, a, rows, frozen), _series(ws, experiment_id, b, rows, frozen),
                                        reps=pb["repetitions"], seed=pb["seed"], ci_level=pb["ci_level"])
                rec.update({"paired_difference": pd_["difference"], "ci_low": pd_["ci_low"], "ci_high": pd_["ci_high"], "n_weeks": pd_["n_weeks"]})
                rec["near_tie"] = pd_["ci_contains_zero"]
                rec["reason"] = (f"|difference| {abs(diff):.4f} <= {nt['max_abs_diff_median_standardized_uplift']} and the {int(pb['ci_level'] * 100)}% paired weekly-block CI "
                                 f"[{pd_['ci_low']:+.4f}, {pd_['ci_high']:+.4f}] contains 0" if rec["near_tie"] else
                                 f"paired weekly-block CI [{pd_['ci_low']:+.4f}, {pd_['ci_high']:+.4f}] excludes 0: not a near tie")
            else:
                rec["reason"] = f"|difference| {abs(diff):.4f} > {nt['max_abs_diff_median_standardized_uplift']}: not a near tie"
            res["pairs"].append(rec)
            if rec["near_tie"]:
                edges.append((a["group_id"], b["group_id"]))
    parent = {g["group_id"]: g["group_id"] for g in ranked}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for x, y in edges:
        parent[find(x)] = find(y)
    comp: dict[str, list] = {}
    for g in ranked:                                                  # ranked order = the existing frozen IS group ranking
        comp.setdefault(find(g["group_id"]), []).append(g)
    clusters = [members for members in comp.values() if len(members) >= 2]
    clusters.sort(key=lambda ms: ms[0]["rank"])                       # deterministic: by the best member's IS rank
    for k, members in enumerate(clusters, 1):
        cid = f"NEAR_TIE_CLUSTER_{k:02d}"
        res["clusters"].append({
            "cluster_id": cid, "side": members[0]["state"],
            "members": [config_id(experiment_id, g["group_id"]) for g in members],
            "proposable_for_holdout": [config_id(experiment_id, g["group_id"]) for g in members[:nt["max_configs_proposed_per_cluster"]]],
            "is_ranks": {config_id(experiment_id, g["group_id"]): g["rank"] for g in members},
            "pairs": [p for p in res["pairs"] if p["near_tie"] and p["a"] in {config_id(experiment_id, g["group_id"]) for g in members}
                      and p["b"] in {config_id(experiment_id, g["group_id"]) for g in members}]})
    return res


def group_card(rows: list[dict], group: dict) -> dict:
    """Report facts of one eligible group (all numbers come from the frozen trial rows)."""
    rs = [r for r in rows if r["target"] == group["target"] and r["state"] == group["state"] and r["model"] in group["models"]]
    med = lambda k: float(np.median([float(r[k]) for r in rs]))        # noqa: E731
    return {"group_id": group["group_id"], "target": group["target"], "side": group["state"], "models": group["models"],
            "frequency_per_week": med("selected_frequency"), "median_standardized_uplift": group["median_standardized_uplift"],
            "median_selected_effect": med("selected_effect"), "median_campaign_q": med("campaign_q"),
            "median_campaign_bonferroni_p": group["median_campaign_bonferroni_p"],
            "positive_years": [f"{int(r['positive_years'])}/{int(r['eligible_years'])}" for r in rs],
            "positive_folds": [f"{int(r['positive_effect_folds'])}/{int(r['folds_evaluated'])}" for r in rs], "is_rank": group["rank"]}
