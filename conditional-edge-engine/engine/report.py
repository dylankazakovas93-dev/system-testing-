"""Markdown report: every result is shown, rejected or not. Nothing is silently discarded."""
from __future__ import annotations

import math

import pandas as pd

from engine import trial_registry as reg
from engine.common import Frozen

DECILE_NOTE = ("These bins were not selection trials and cannot promote a candidate.\n"
               "Using them to construct a rule requires a new registered experiment.")
DIAG_BANNER = "DIAGNOSTIC — NOT ELIGIBLE FOR PROMOTION"


def _n(x, fmt="{:.4f}"):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "n/a"
    return "n/a" if math.isnan(x) else fmt.format(x)


def _sigma(x):
    return _n(x, "{:+.4f}σ")


def _table(header: list[str], rows: list[list]) -> str:
    if not rows:
        return "_none_\n"
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out) + "\n"


def _trial_row(r) -> list:
    return [r["trial_id"], r["target"], r["model"], r["state"], int(r["n_selected_events"]),
            _n(r["parent_frequency"], "{:.2f}"), _n(r["selected_frequency"], "{:.2f}"), _n(r["retention_ratio"], "{:.2f}"),
            _n(r["parent_effect"], "{:+.5f}"), _n(r["selected_effect"], "{:+.5f}"), _n(r["uplift"], "{:+.5f}"),
            _n(r["standardized_uplift"], "{:+.3f}"),
            f"[{_n(r['bootstrap_ci_low'], '{:+.5f}')}, {_n(r['bootstrap_ci_high'], '{:+.5f}')}]",
            _n(r["raw_p"], "{:.4f}"), _n(r["experiment_q"], "{:.4f}"), _n(r["campaign_q"], "{:.4f}"),
            f"{int(r['positive_years']) if not math.isnan(r['positive_years']) else 0}/"
            f"{int(r['eligible_years']) if not math.isnan(r['eligible_years']) else 0}", r["decision"]]


TRIAL_HEADER = ["trial", "target", "model", "state", "N sel", "parent f/wk", "sel f/wk", "retention", "parent effect",
                "selected effect", "uplift", "std uplift", "95% block-boot CI (uplift)", "raw p", "exp q", "camp q",
                "pos/elig years", "decision"]


def _freq_destruction_block(r) -> str:
    return (f"Parent: {_n(r['parent_frequency'], '{:.2f}')}/week\n"
            f"Selected: {_n(r['selected_frequency'], '{:.2f}')}/week (retention {_n(r['retention_ratio'], '{:.2f}')})\n"
            f"Parent effect: {_sigma(r['parent_effect'] / r['target_sd']) if r['target_sd'] else 'n/a'}\n"
            f"Selected effect: {_sigma(r['selected_effect'] / r['target_sd']) if r['target_sd'] else 'n/a'}\n"
            f"Uplift: {_sigma(r['standardized_uplift'])}\n"
            f"STATUS: {r['decision']}" +
            (" / REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS" if "FREQUENCY_LOSS" in str(r["rejection_reason"]) else ""))


def build_report(ws: reg.Workspace, experiment_id: str, bundle: dict, trials: pd.DataFrame,
                 observations: pd.DataFrame, frozen: Frozen) -> str:
    exp = reg.experiment_row(ws, experiment_id)
    summ = reg.campaign_summary(ws, exp["campaign_id"], frozen)
    b = bundle["base_event"]
    L: list[str] = []
    L.append(f"# Experiment report — {experiment_id}\n")
    L.append(f"* campaign: **{exp['campaign_id']}** (experiment {exp['sequence_in_campaign']} of {summ['experiments_max']}); "
             f"lockbox starts {bundle['lockbox_start']} (never evaluated here)")
    L.append(f"* engine {exp['engine_version']}; data: {bundle['data']} (fingerprint `{bundle['data_fingerprint'][:16]}…`)")
    L.append(f"* development / training period: {bundle['train_period']}; chronological OOS period: {bundle['oos_period']}")
    L.append(f"* **selection opportunities used by this experiment: {len(trials)} of 24. Campaign {exp['campaign_id']}: "
             f"{summ['selection_trials_registered']} of {summ['selection_trials_max']} registered, "
             f"{summ['selection_trials_revealed']} revealed.**")
    L.append(f"* external research verification: **{exp['research_verification']}** "
             f"(research results are not valid unless the research families pass)")
    for w in bundle["manifest_check"].get("warnings", []):
        L.append(f"* WARNING: {w}")
    L.append("")
    # ---- BASE EVENT
    L.append("## BASE EVENT\n")
    L.append(_table(["quantity", "value"], [
        ["events after session/dedup/cooldown rules", f"{b['n_events']:,}"],
        ["model-eligible events (>= 480 completed bars)", f"{b['n_model_eligible']:,}"],
        ["development trading weeks", b["trading_weeks"]],
        ["raw event frequency", _n(b["raw_event_frequency_per_week"], "{:.2f}") + " / week"],
        ["long / short events", f"{b['long_events']:,} / {b['short_events']:,}"],
        ["declared parameters never read by event.py", ", ".join(b["unused_parameters"]) or "none"],
        ["60-bar forward windows spanning a session gap", b["forward_windows_crossing_gaps"]],
        ["lockbox-withheld bars (not loaded for modelling)", f"{b['lockbox_withheld_bars']:,}"]]))
    if b["flag"]:
        L.append(f"\n**{b['flag']}** — the base event occurs < {frozen.trial_policy['base_event_frequency_floor_per_week']}/week, "
                 f"so a fixed half-state cannot realistically keep >= 1/week. The 50% state threshold is NOT changed.\n")
    folds = {}
    for key, p in bundle["panels"].items():
        for f in p["folds"]:
            folds.setdefault(f["year"], f["status"])
    L.append("\nOuter walk-forward folds: " + ", ".join(f"{y}: {s}" for y, s in sorted(folds.items())) + "\n")
    # ---- sections by decision
    def by(dec):
        return trials[trials["decision"] == dec]
    L.append("## PROMOTED DEVELOPMENT CANDIDATES\n")
    prom = pd.concat([by("PROMOTABLE"), by("PROMOTABLE_PENDING_SENSITIVITY")])
    if prom.empty:
        L.append("No development candidate. (No target × side had >= 2 of 3 models pass every gate.)\n")
    else:
        for (t, s), g in prom.groupby(["target", "state"]):
            action = "trade in event direction" if s == "UPPER_HALF" else "trade OPPOSITE to event direction (fade)"
            L.append(f"### {t} × {s} — DEVELOPMENT CANDIDATE ({len(g)} of 3 models pass; action: {action})\n")
            L.append(_table(TRIAL_HEADER, [_trial_row(r) for _, r in g.iterrows()]))
            sens = bundle["sensitivity"]["groups"].get(f"{t}|{s}")
            if sens:
                L.append(f"Event-parameter sensitivity (robustness only): **{sens['verdict']}**\n")
                rows = []
                for pr in sens.get("probes", []):
                    rows.append([pr["parameter"], pr["base"], f"x{pr['multiplier']}", pr["value"], pr["n_events"],
                                 "; ".join(f"{m['model']}:{_n(m['standardized_uplift'], '{:+.3f}')}σ@{_n(m['selected_frequency'], '{:.2f}')}/wk"
                                           for m in pr["models"]),
                                 pr["models_positive_uplift"], pr["models_frequency_ok"]])
                L.append(_table(["parameter", "base", "mult", "probe value", "events", "std uplift @ freq per model",
                                 "models uplift>0", "models freq>=1/wk"], rows))
                L.append("Probes are reported only; a better-performing probe never replaces the base parameter.\n")
            else:
                L.append(f"Sensitivity: {bundle['sensitivity']['status']}\n")
    sections = [("REJECTED — LOW FREQUENCY", "REJECTED_LOW_FREQUENCY"),
                ("REJECTED — INSUFFICIENT UPLIFT", "REJECTED_INSUFFICIENT_UPLIFT"),
                ("REJECTED — STATISTICAL", "REJECTED_STATISTICAL"),
                ("REJECTED — INSTABILITY", "REJECTED_INSTABILITY"),
                ("REJECTED — SENSITIVITY", "REJECTED_SENSITIVITY")]
    for title, dec in sections:
        L.append(f"## {title}\n")
        g = by(dec)
        L.append(_table(TRIAL_HEADER + ["reason"], [_trial_row(r) + [r["rejection_reason"]] for _, r in g.iterrows()]))
        if dec == "REJECTED_INSUFFICIENT_UPLIFT" and len(g):
            L.append("Frequency cost versus gain (shown for every such state, never hidden):\n")
            for _, r in g.iterrows():
                L.append("```\n" + f"{r['trial_id']} {r['target']}/{r['model']}/{r['state']}\n" + _freq_destruction_block(r) + "\n```\n")
    agree = by("REJECTED_MODEL_AGREEMENT")
    L.append("### Passed own gates but fewer than 2 of 3 models (not promoted)\n")
    L.append(_table(TRIAL_HEADER, [_trial_row(r) for _, r in agree.iterrows()]))
    nd = by("DIAGNOSTIC_ONLY")
    if len(nd):
        L.append("### Not evaluable (DIAGNOSTIC_ONLY)\n")
        L.append(_table(["trial", "reason"], [[r["trial_id"], r["rejection_reason"]] for _, r in nd.iterrows()]))
    # ---- diagnostics
    L.append("## DIAGNOSTIC / NON-PROMOTABLE OBSERVATIONS\n")
    L.append(f"**{DIAG_BANNER}.** Anything below may inspire a NEW registered experiment; it cannot modify this one.\n")
    L.append("### Score deciles (pooled OOS)\n")
    L.append(DECILE_NOTE + "\n")
    for key, p in sorted(bundle["panels"].items()):
        dd = p.get("deciles") or {}
        if not dd.get("deciles"):
            continue
        L.append(f"#### {key.replace('|', ' / ')}\n")
        L.append(_table(["decile", "N", "events / week", "mean target (event direction)"],
                        [[r["decile"], r["n"], _n(r["frequency_per_week"], "{:.3f}"), _n(r["mean_target"], "{:+.6f}")]
                         for r in dd["deciles"]]))
        yrs = dd.get("by_year", {})
        if yrs:
            L.append("Year-by-year mean target by decile:\n")
            L.append(_table(["year"] + [f"D{i}" for i in range(1, 11)],
                            [[y] + [_n(v, "{:+.5f}") for v in vals] for y, vals in sorted(yrs.items())]))
        imp = p.get("importances") or {}
        if imp:
            L.append("Top diagnostic feature importances: " + ", ".join(f"{k} ({v:.4g})" for k, v in list(imp.items())[:5])
                     + " — **" + DIAG_BANNER + "**\n")
    L.append("### Diagnostic targets (means over model-eligible parent events; report only)\n")
    dt = bundle.get("diagnostic_targets", {})
    L.append(_table(["diagnostic target", "mean"], [[k, _n(v, "{:.6f}")] for k, v in dt.items()]))
    L.append("### Registered observations (registry/observations.csv)\n")
    mine = observations[observations["experiment_id"] == experiment_id]
    L.append(_table(["id", "category", "description"], [[r["observation_id"], r["category"], r["description"]]
                                                          for _, r in mine.iterrows()]))
    # ---- all 24
    L.append("## ALL 24 SELECTION TRIALS\n")
    L.append(_table(TRIAL_HEADER, [_trial_row(r) for _, r in trials.iterrows()]))
    L.append("### Year-by-year selected effect (event-direction-adjusted; years with >= 20 selected events are eligible)\n")
    years = sorted({y["year"] for p in bundle["panels"].values() for st in p["stats"].values() for y in st.get("yearly", [])})
    rows = []
    idx = {(r["target"], r["model"], r["state"]): r["trial_id"] for _, r in trials.iterrows()}
    for (t, m, s), tid in idx.items():
        yl = {y["year"]: y for y in bundle["panels"][f"{t}|{m}"]["stats"][s].get("yearly", [])}
        rows.append([tid, f"{t}/{m}/{s}"] + [
            (f"{_n(yl[y]['selected_effect'], '{:+.5f}')} (n={yl[y]['n_selected']}{'' if yl[y]['eligible'] else ', inelig.'})"
             if y in yl else "–") for y in years])
    L.append(_table(["trial", "state"] + [str(y) for y in years], rows))
    return "\n".join(L) + "\n"
