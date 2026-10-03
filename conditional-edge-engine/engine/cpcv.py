"""Automatic post-selection robustness: fixed CPCV (N=6 chronological groups, k=2 held out => C(6,2)=15 splits). VETO ONLY.

Runs AUTOMATICALLY (no human approval) once the human's FINAL_CONFIG_FROZEN is valid, for exactly that ONE TARGET x SIDE configuration
(all 3 models). Data: DEVELOPMENT + SELECTION_HOLDOUT if the selection holdout was used, DEVELOPMENT only if it was skipped; the final lockbox is
never loaded. The report is labelled "POST-SELECTION ROBUSTNESS — NOT INDEPENDENT CONFIRMATION" because the configuration was chosen with the
IS (and possibly selection-holdout) data CPCV re-uses. CPCV cannot create a candidate, rescue a failed one, choose a model, target, threshold or
event parameter, and a CPCV failure ENDS the lineage: there is no fallback to a runner-up. Everything is fixed: same event, target, side,
feature bank, model, hyperparameters and score-state definition. Inside every split the preprocessing, the nested inner-OOF calibration and the
score median are TRAIN-ONLY (nothing is reused from another split or from the global fit).

Splits: groups = ~equal model-eligible event counts, chronological, boundaries snapped to exchange-local day starts (whole
trading days). TEST = the 2 held-out groups, TRAIN = the other 4 minus
  * PURGE: any training event whose label interval [event_time, effective_target_end] overlaps a held-out region;
  * EMBARGO: any training event within MAX PRIMARY TARGET HORIZON (information time) before the start or after the end of
    every held-out region (i.e. at every test/train boundary).
No shuffling, no random assignment.

PBO-style diagnostic (NOT a p-value; NEVER used to rank, select or veto; docs/CPCV_PBO.md):
  m[i,g] = mean over the CPCV splits that held out group g of config i's uplift measured on group g.
  For each split s (test groups T, train groups C): IS_i = mean_{g in C} m[i,g], SELECTION_HOLDOUT_i = mean_{g in T} m[i,g];
  n* = argmax_i IS_i; w = rank(SELECTION_HOLDOUT_{n*} among N configs, ascending)/(N+1); logit = ln(w/(1-w)); PBO = share of splits with
  logit < 0. Needs >= 2 configurations, otherwise NOT APPLICABLE.
"""
from __future__ import annotations

import itertools
import json

import numpy as np
import pandas as pd
from scipy.stats import rankdata

from engine import trial_registry as reg
from engine.common import EngineError, Frozen, load_frozen, model_names, now_utc_iso, utc_ns
from engine.event_contract import load_event_module, load_spec
from engine.experiment_lifecycle import experiment_dir
from engine.feature_engine import feature_names
from engine.model_engine import make_model_factory
from engine.partitions import development_view, parse_partitions, selection_holdout_view
from engine.score_calibration import WFConfig, assign_state, calibrate_threshold
from engine.statistics import weeks_in_intervals
from engine.target_engine import max_primary_horizon_bars
from engine.walkforward import INT64_MAX, make_blocks


def cpcv_split_ids(n_groups: int, n_test: int) -> list[tuple[int, ...]]:
    return list(itertools.combinations(range(n_groups), n_test))


def cpcv_groups(event_time, n_groups: int, tz: str) -> list[tuple[int, int]]:
    return make_blocks(event_time, n_groups, tz)


def split_masks(ev_ns: np.ndarray, eff_end_ns: np.ndarray, regions: list[tuple[int, int]], embargo_ns: int):
    """(train_mask, test_mask) for one CPCV split given the held-out regions [lo, hi)."""
    test = np.zeros(len(ev_ns), dtype=bool)
    removed = np.zeros(len(ev_ns), dtype=bool)
    for lo, hi in regions:
        inside = (ev_ns >= lo) & (ev_ns < hi)
        test |= inside
        overlap = (ev_ns < hi) & (eff_end_ns >= lo)                              # label interval touches the held-out region
        embargo = ((ev_ns >= hi) & (ev_ns < hi + embargo_ns)) | ((ev_ns >= lo - embargo_ns) & (ev_ns < lo))
        removed |= overlap | embargo
    train = ~test & ~removed
    return train, test


def pass_rule(rows: list[dict], rule: dict) -> dict:
    """Summary + CPCV_PASS for one candidate model over its splits."""
    ok = [r for r in rows if r["valid"]]
    eff = np.array([r["selected_effect"] for r in ok], dtype=float)
    up = np.array([r["uplift"] for r in ok], dtype=float)
    out = {"n_valid_splits": len(ok), "n_splits": len(rows)}
    if len(ok):
        out.update(median_effect=float(np.nanmedian(eff)) if np.isfinite(eff).any() else float("nan"),
                   median_uplift=float(np.nanmedian(up)) if np.isfinite(up).any() else float("nan"),
                   p10_uplift=float(np.nanpercentile(up, 10)) if np.isfinite(up).any() else float("nan"),
                   p90_uplift=float(np.nanpercentile(up, 90)) if np.isfinite(up).any() else float("nan"),
                   n_effect_positive=int(np.sum(eff > 0)), n_uplift_positive=int(np.sum(up > 0)),
                   fraction_effect_positive=float(np.sum(eff > 0) / len(rows)), fraction_uplift_positive=float(np.sum(up > 0) / len(rows)))
        finite = [r for r in ok if np.isfinite(r["uplift"])]
        out["worst_split"] = min(finite, key=lambda r: r["uplift"])["split"] if finite else None
        out["best_split"] = max(finite, key=lambda r: r["uplift"])["split"] if finite else None
    else:
        out.update(median_effect=float("nan"), median_uplift=float("nan"), p10_uplift=float("nan"), p90_uplift=float("nan"),
                   n_effect_positive=0, n_uplift_positive=0, fraction_effect_positive=0.0, fraction_uplift_positive=0.0,
                   worst_split=None, best_split=None)
    out["cpcv_pass"] = bool(
        len(ok) == rule["n_splits"] and out["median_effect"] > rule["median_selected_effect_must_exceed"]
        and out["median_uplift"] > rule["median_uplift_must_exceed"]
        and out["n_effect_positive"] >= rule["min_splits_positive_effect"] and out["n_uplift_positive"] >= rule["min_splits_positive_uplift"])
    return out


def pbo_diagnostic(group_uplift: dict[str, np.ndarray], splits: list[tuple[int, ...]], n_groups: int) -> dict:
    """group_uplift[config] = array (n_groups,) of m[i,g]. Returns {'pbo': float|None, ...}. Diagnostic only."""
    cfgs = sorted(group_uplift)
    if len(cfgs) < 2:
        return {"pbo": None, "status": "NOT APPLICABLE", "n_configs": len(cfgs)}
    M = np.array([np.nan_to_num(group_uplift[c], nan=0.0) for c in cfgs])           # (N, G)
    logits = []
    for test in splits:
        train = [g for g in range(n_groups) if g not in test]
        is_perf, selection_holdout_perf = M[:, train].mean(axis=1), M[:, list(test)].mean(axis=1)
        best = int(np.argmax(is_perf))
        w = rankdata(selection_holdout_perf)[best] / (len(cfgs) + 1)
        logits.append(float(np.log(w / (1 - w))))
    return {"pbo": float(np.mean(np.array(logits) < 0)), "status": "COMPUTED", "n_configs": len(cfgs), "logits": logits,
            "note": "diagnostic only; not an independent p-value; never used for selection or ranking"}


def run_cpcv_tables(events, features, targets, eligible, calendar_index, groups: list[str], frozen: Frozen, *,
                    models: list[str] | None = None, factory=None, progress=None) -> dict:
    """CPCV on prepared tables for the already-fixed target|side groups. Returns per (target,state,model) split records."""
    cp = frozen.trial_policy["cpcv"]
    cfg = WFConfig.from_policy(frozen.trial_policy)
    rule = frozen.acceptance["cpcv"]
    names = feature_names(frozen)
    models = models or model_names(frozen)
    splits = cpcv_split_ids(cp["n_groups"], cp["n_test_groups"])
    assert len(splits) == cp["n_splits"] == 15
    embargo_ns = max_primary_horizon_bars(frozen) * int(frozen.interval.value)
    ev = events.assign(_el=np.asarray(eligible, dtype=bool))
    ev = ev[ev["_el"]].sort_values(["event_time", "event_id"], kind="stable").reset_index(drop=True)
    regions = cpcv_groups(pd.DatetimeIndex(ev["event_time"]), cp["n_groups"], frozen.tz)
    feat = features.set_index("event_id")
    results: dict = {}
    for t in sorted({g.split("|")[0] for g in groups}):
        tdf = targets[t].set_index("event_id")
        ids = [i for i in ev["event_id"] if i in tdf.index]
        sub = ev.set_index("event_id").loc[ids]
        etime = pd.DatetimeIndex(sub["event_time"])
        ev_ns = utc_ns(etime)
        te_ns = utc_ns(pd.DatetimeIndex(tdf.loc[ids, "effective_target_end"]))
        y = tdf.loc[ids, "value"].to_numpy("float64")
        X = feat.loc[ids, names].reset_index(drop=True)
        for g in [g for g in groups if g.startswith(t + "|")]:
            state = g.split("|")[1]
            s = 1.0 if state == "UPPER_HALF" else -1.0
            for m in models:
                fac = factory(m) if factory else make_model_factory(m, frozen)
                recs = []
                for si, test_groups in enumerate(splits):
                    reg_i = [regions[k] for k in test_groups]
                    tr_mask, te_mask = split_masks(ev_ns, te_ns, reg_i, embargo_ns)
                    train, test = np.flatnonzero(tr_mask), np.flatnonzero(te_mask)
                    rec = {"split": si, "test_groups": list(test_groups), "n_train": int(len(train)), "n_test": int(len(test)),
                           "valid": False, "selected_effect": float("nan"), "uplift": float("nan")}
                    if len(train) >= cfg.min_outer_train_events and len(test):
                        thr, _, _ = calibrate_threshold(fac, X, y, ev_ns, te_ns, train, cfg)      # TRAIN-ONLY calibration
                        if thr is not None:
                            model = fac().fit(X.iloc[train], y[train])                               # TRAIN-ONLY preprocessing + fit
                            score = model.predict(X.iloc[test])
                            st = assign_state(score, thr)
                            sel = st == state
                            sv = s * y[test]
                            n_sel = int(sel.sum())
                            wk = weeks_in_intervals(calendar_index, reg_i, frozen.tz)["total"]
                            par = float(sv.mean())
                            eff = float(sv[sel].mean()) if n_sel else float("nan")
                            gu = []
                            for k in test_groups:
                                lo, hi = regions[k]
                                mg = (ev_ns[test] >= lo) & (ev_ns[test] < hi)
                                sg = sel & mg
                                gu.append(float(sv[sg].mean() - sv[mg].mean()) if sg.any() and mg.any() else float("nan"))
                            rec.update(valid=True, threshold=float(thr), n_selected=n_sel, selected_effect=eff, parent_effect=par,
                                       uplift=eff - par if n_sel else float("nan"), frequency=n_sel / wk if wk else float("nan"),
                                       retention=n_sel / len(test), group_uplift=dict(zip(test_groups, gu)))
                    recs.append(rec)
                results[(t, state, m)] = recs
                if progress:
                    progress(t, state, m)
    out = {"splits": splits, "regions": regions, "records": results, "summary": {}, "group_verdicts": {}}
    gm = {}
    for key, recs in results.items():
        out["summary"][key] = pass_rule(recs, rule)
        mat = np.full(cp["n_groups"], np.nan)
        for gi in range(cp["n_groups"]):
            vals = [r["group_uplift"][gi] for r in recs if r["valid"] and gi in r.get("group_uplift", {}) and np.isfinite(r["group_uplift"][gi])]
            if vals:
                mat[gi] = float(np.mean(vals))
        gm["|".join(map(str, key))] = mat
    for g in groups:
        t, st = g.split("|")
        npass = sum(1 for m in models if out["summary"][(t, st, m)]["cpcv_pass"])
        out["group_verdicts"][g] = {"models_passing": npass, "cpcv_pass": npass >= rule["min_models_passing"]}
    out["pbo"] = pbo_diagnostic(gm, splits, cp["n_groups"])           # diagnostic: computed AFTER and apart from every verdict
    return out


CPCV_LABEL = "POST-SELECTION ROBUSTNESS — NOT INDEPENDENT CONFIRMATION"


def _final_config(ws: reg.Workspace, experiment_id: str) -> dict:
    fc = reg.final_config_of(ws, experiment_id)
    if fc is None:
        raise EngineError(f"{experiment_id} has no FINAL_CONFIG_FROZEN ledger row: CPCV runs only for the ONE human-chosen final configuration")
    return fc


def cpcv_cutoff(ws: reg.Workspace, experiment_id: str) -> tuple[pd.Timestamp, str]:
    """(exclusive end of the data CPCV may load, which partitions it contains). The final lockbox is never included."""
    d = experiment_dir(ws, experiment_id)
    parts = parse_partitions(load_spec(d / "EVENT_SPEC.yaml")["partitions"])
    if _final_config(ws, experiment_id)["selection_holdout_used"] == "yes":
        return parts.selection_holdout_end, "DEVELOPMENT + SELECTION_HOLDOUT"
    return parts.development_end, "DEVELOPMENT only (selection holdout skipped)"


def run_cpcv(ws: reg.Workspace, experiment_id: str, bars: pd.DataFrame, *, verbose: bool = True) -> dict:
    """Automatic CPCV for a FINAL_CONFIG_FROZEN experiment. Veto only; the final lockbox is excluded."""
    from engine.experiment_runner import build_event_tables
    frozen = load_frozen()
    precheck_cpcv(ws, experiment_id)
    d = experiment_dir(ws, experiment_id)
    spec = load_spec(d / "EVENT_SPEC.yaml")
    parts = parse_partitions(spec["partitions"])
    used = _final_config(ws, experiment_id)["selection_holdout_used"] == "yes"
    cut = selection_holdout_view(bars, parts) if used else development_view(bars, parts)
    del bars
    module = load_event_module(d / "event.py")
    events, features, eligible, targets, _ = build_event_tables(module, spec, cut, frozen)
    return execute_cpcv(ws, experiment_id, events, features, targets, eligible, cut.index, verbose=verbose)


def precheck_cpcv(ws: reg.Workspace, experiment_id: str) -> None:
    from engine.selection_holdout_stage import mark_contamination_if_mutated
    if mark_contamination_if_mutated(ws, experiment_id):
        raise EngineError(f"{experiment_id} is SELECTION_HOLDOUT_CONTAMINATED (frozen experiment changed after SELECTION HOLDOUT was spent)")
    exp = reg.experiment_row(ws, experiment_id)
    if exp["status"] != "FINAL_CONFIG_FROZEN":
        raise EngineError(f"CPCV runs only for FINAL_CONFIG_FROZEN experiments (this one is {exp['status']}); it can never rescue a failed candidate")
    _final_config(ws, experiment_id)


def execute_cpcv(ws: reg.Workspace, experiment_id: str, events, features, targets, eligible, calendar_index, *, verbose: bool = True) -> dict:
    from engine.experiment_runner import _clean
    frozen = load_frozen()
    log = (lambda *a: print(*a, flush=True)) if verbose else (lambda *a: None)
    precheck_cpcv(ws, experiment_id)
    exp = reg.experiment_row(ws, experiment_id)
    d = experiment_dir(ws, experiment_id)
    fc = _final_config(ws, experiment_id)
    group = fc["selected_config_id"].split("|", 1)[1]                      # TARGET|SIDE of the single human-chosen configuration
    _, data_used = cpcv_cutoff(ws, experiment_id)
    res = run_cpcv_tables(events, features, targets, eligible, calendar_index, [group], frozen,
                          progress=lambda t, s, m: log(f"[{experiment_id}] CPCV {t}|{s} {m} done"))
    now = now_utc_iso()
    rows = []
    for (t, st, m), s in res["summary"].items():
        gid = f"{t}|{st}"
        rows.append({"campaign_id": exp["campaign_id"], "experiment_id": experiment_id, "group_id": gid, "target": t, "state": st, "model": m,
                     "n_valid_splits": s["n_valid_splits"], "median_effect": s["median_effect"], "median_uplift": s["median_uplift"],
                     "p10_uplift": s["p10_uplift"], "p90_uplift": s["p90_uplift"], "fraction_effect_positive": s["fraction_effect_positive"],
                     "fraction_uplift_positive": s["fraction_uplift_positive"], "worst_split": s["worst_split"], "best_split": s["best_split"],
                     "cpcv_pass": s["cpcv_pass"], "group_cpcv_pass": res["group_verdicts"][gid]["cpcv_pass"],
                     "pbo_diagnostic": res["pbo"]["pbo"] if res["pbo"]["pbo"] is not None else "NOT APPLICABLE", "revealed_at": now})
    reg.append_table(ws, "cpcv_results.csv", reg.CPCV_COLS, rows)
    passed = bool(res["group_verdicts"][group]["cpcv_pass"])
    report = {"label": CPCV_LABEL, "experiment_id": experiment_id, "final_config_id": fc["selected_config_id"], "data_used": data_used,
              "selection_holdout_used": fc["selection_holdout_used"] == "yes", "final_lockbox_accessed": False,
              "cpcv_passed": passed, "n_splits": len(res["splits"]), "splits": [list(s) for s in res["splits"]],
              "summary": {"|".join(k): v for k, v in res["summary"].items()}, "group_verdicts": res["group_verdicts"],
              "pbo_diagnostic": res["pbo"], "records": {"|".join(k): v for k, v in res["records"].items()},
              "note": "CPCV is a veto/robustness stage only (the configuration was chosen with this data: NOT independent confirmation). "
                      "PBO is a diagnostic, not a p-value, and influences nothing. A failure ends the lineage; there is no fallback to a runner-up."}
    (d / "results" / "CPCV_REPORT.json").write_text(json.dumps(_clean(report), indent=2, sort_keys=True))
    (d / "results" / "CPCV_REPORT.md").write_text(_cpcv_md(report))
    reg.append_final_config(ws, campaign_id=exp["campaign_id"], experiment_id=experiment_id, event="CPCV_RESULT",
                            selected_config_id=fc["selected_config_id"], is_rank=fc["is_rank"], near_tie_cluster=fc["near_tie_cluster"],
                            selection_holdout_used=fc["selection_holdout_used"], selection_holdout_rank=fc["selection_holdout_rank"],
                            human_selection_file_hash=fc["human_selection_file_hash"], manifest_hash=fc["manifest_hash"], frozen_at=now,
                            cpcv_status="CPCV_CONFIRMED" if passed else "CPCV_REJECTED")
    if passed:
        reg.set_status(ws, experiment_id, "CPCV_CONFIRMED", f"CPCV robustness passed for {fc['selected_config_id']} (post-selection, not independent)")
        reg.set_status(ws, experiment_id, "AWAITING_FINAL_LOCKBOX_APPROVAL", "stop: the human decides separately whether to spend the final lockbox")
    else:
        reg.set_status(ws, experiment_id, "CPCV_REJECTED", f"CPCV vetoed the final configuration {fc['selected_config_id']}; lineage ends, no fallback")
    log(f"[{experiment_id}] CPCV verdict {res['group_verdicts']}; status {reg.experiment_row(ws, experiment_id)['status']}")
    return report


def _cpcv_md(r: dict) -> str:
    L = [f"# CPCV — {r['experiment_id']}", "", f"**{CPCV_LABEL}**", "",
         f"Final configuration: `{r['final_config_id']}` (one configuration, all 3 models). Data: {r['data_used']}. Final lockbox accessed: NO.", "",
         f"Verdict: **{'CPCV_CONFIRMED (robustness only)' if r['cpcv_passed'] else 'CPCV_REJECTED — lineage ends, no fallback to a runner-up'}**", "",
         "| model | valid splits | median effect | median uplift | p10 uplift | splits effect>0 / uplift>0 | pass |", "|---|---|---|---|---|---|---|"]
    for k, s in sorted(r["summary"].items()):
        L.append(f"| {k.split('|')[-1]} | {s['n_valid_splits']}/{s['n_splits']} | {s['median_effect']} | {s['median_uplift']} | {s['p10_uplift']} | "
                 f"{s['n_effect_positive']} / {s['n_uplift_positive']} | {s['cpcv_pass']} |")
    L += ["", f"PBO diagnostic (not a p-value, influences nothing): {r['pbo_diagnostic'].get('pbo')}", "", r["note"], ""]
    return "\n".join(L)


def freeze_and_run_cpcv(ws: reg.Workspace, experiment_id: str, data_path, timestamp_col: str = "timestamp", *, verbose: bool = True) -> dict:
    """Validate + freeze the human's final-configuration file, then run the fixed CPCV AUTOMATICALLY (no further approval).
    Only DEVELOPMENT (+ SELECTION_HOLDOUT if used) rows are ever loaded; the final lockbox never is. A DECLINE ends the experiment with no CPCV."""
    from engine.partitions import load_bars_before
    from engine.selection_holdout_stage import freeze_final_config
    info = freeze_final_config(ws, experiment_id)
    if info["decline"]:
        return {"declined": True, **info}
    cutoff, _ = cpcv_cutoff(ws, experiment_id)
    bars = load_bars_before(data_path, cutoff, timestamp_col)
    return run_cpcv(ws, experiment_id, bars, verbose=verbose)
