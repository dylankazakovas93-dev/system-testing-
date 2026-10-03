"""Markdown / JSON rendering of the forward-path diagnostics for the IS report (NON-PROMOTABLE section).  DIAGNOSTIC ONLY."""
from __future__ import annotations

import hashlib
import json

from engine.common import EngineError


def _n(x, nd=4):
    return "n/a" if x is None else (f"{x:.{nd}f}" if isinstance(x, float) else str(x))


def _rt(r):
    return "n/a" if r is None or r["rate"] is None else f"{r['n']}/{r['denominator']} = {r['rate']:.3f}"


def _tab(header, rows):
    if not rows:
        return "_none_\n"
    return "\n".join(["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"] + ["| " + " | ".join(map(str, r)) + " |" for r in rows]) + "\n"


def load_path_file(results_dir, bundle: dict) -> dict | None:
    info = (bundle or {}).get("path_diagnostics") or {}
    if info.get("status") != "COMPUTED":
        return None
    txt = (results_dir / info["file"]).read_text()
    if hashlib.sha256(txt.encode()).hexdigest() != info["sha256"]:
        raise EngineError("PATH_DIAGNOSTICS.json was edited after the IS results were written (hash mismatch)")
    return json.loads(txt)


def compact_json(rep: dict, info: dict) -> dict:
    allc = rep["contexts"]["ALL"]
    return {"label": rep["label"], "promotion_eligible": False, "selection_trials_affected": 0,
            "diagnostic_statement": rep["diagnostic_statement"], "non_promotable_rule": rep["non_promotable_rule"],
            "human_interpretation_rule": rep["human_interpretation_rule"], "sigma_ref_formula": rep["sigma_ref_formula"], "cost_banner": rep["cost_banner"], "selection_banner": rep["selection_banner"],
            "file": info["file"], "sha256": info["sha256"], "n_bracket_cells": rep["n_bracket_cells"], "n_contexts": rep["n_contexts"],
            "counts": rep["counts"], "tick_size_points": rep["tick_size_points"], "sigma_ref": rep["sigma_ref"],
            "percentile_method": rep["percentile_method"], "bracket_canonical_order": rep["bracket_canonical_order"],
            "ALL_yearly_table": allc["yearly_table"],
            "ALL_bracket_surface_conservative": [{k: c.get(k) for k in ("expiry_bars", "stop_sigma", "target_sigma", "n", "mean_gross_points", "median_gross_points", "mean_R")}
                                                   for c in allc["bracket_surface"]]}


def render(rep: dict | None, trials_rows: list[dict], my_obs, frozen_label: str) -> list[str]:
    L = ["", "---", "# NON-PROMOTABLE PATH DIAGNOSTICS", "",
         "Sections F–L and U–V above are the **PROMOTION EVIDENCE** (the 24 selection trials). Everything below is **NON-PROMOTABLE PATH DIAGNOSTICS**: "
         "it is not part of the 24-trial BH / Bonferroni family and cannot create, promote, rescue or rank any candidate.", "",
         "## Z. FORWARD PATH DIAGNOSTICS\n"]
    if rep is None:
        L += [f"**{frozen_label}.** Path diagnostics were not computed for this experiment (table-level run without bars).\n"]
        return L
    L += [f"**{rep['label']}** — **{rep['cost_banner']}** — **{rep['selection_banner']}**\n",
          "> " + rep["diagnostic_statement"] + "\n",
          f"**{rep['non_promotable_rule']}**\n", "**Human interpretation rule.** " + rep["human_interpretation_rule"] + "\n",
          f"Horizons {rep['horizons_bars']} bars; tick size {rep['tick_size_points']} points (instrument config); {rep['sigma_ref_formula']} ({rep['sigma_ref']}); percentiles: {rep['percentile_method']}. "
          f"Events: {rep['counts']['model_eligible_events']:,} model-eligible of {rep['counts']['events_total']:,}; PATH_TIMESTAMP_INELIGIBLE per horizon: {rep['counts']['path_ineligible_by_horizon']}. "
          f"Contexts: ALL events and UPPER/LOWER_HALF of every target × model (DEVELOPMENT_CV pooled validation events; identical event sets are grouped). Full detail: `{'results/PATH_DIAGNOSTICS.json'}`. "
          "No SELECTION HOLDOUT or lockbox row entered any number below.\n"]
    A = rep["contexts"]["ALL"]
    hs = [str(h) for h in rep["horizons_bars"]]
    L.append("### Z.1 Endpoint returns (ALL events; directional log return)\n")
    L.append(_tab(["h", "N", "mean", "median", "P25", "P75", "P5", "P95", "std", "mean raw pts", "median raw pts"],
                  [[h, A["endpoint"][h]["n"], *(_n(A["endpoint"][h]["directional_log_return"][k], 6) for k in ("mean", "median", "p25", "p75", "p5", "p95", "std")),
                    _n(A["endpoint"][h]["raw_return_points"]["mean"], 3), _n(A["endpoint"][h]["raw_return_points"]["median"], 3)] for h in hs]))
    L.append("### Z.2 Continuation / reversal (ALL events; numerator/denominator)\n")
    L.append(_tab(["h", "continuation", "reversal", "flat"], [[h, _rt(A["continuation"][h]["continuation"]), _rt(A["continuation"][h]["reversal"]), _rt(A["continuation"][h]["flat"])] for h in hs]))
    L.append("### Z.3 MFE / MAE (ALL events; MAE ≤ 0 shown as |MAE|; path dominance = MFE + MAE)\n")
    L.append(_tab(["h", "MFE mean pts", "MFE median pts", "MFE median ticks", "MFE median σ", "|MAE| mean pts", "|MAE| median pts", "|MAE| median ticks", "|MAE| median σ",
                   "dominance median", "frac > 0", "frac < 0"],
                  [[h, _n(A["excursions"][h]["MFE"]["points"]["mean"], 2), _n(A["excursions"][h]["MFE"]["points"]["median"], 2), _n(A["excursions"][h]["MFE"]["ticks"]["median"], 1),
                    _n(A["excursions"][h]["MFE"]["sigma"]["median"], 3), _n(A["excursions"][h]["ADVERSE_ABS_MAE"]["points"]["mean"], 2),
                    _n(A["excursions"][h]["ADVERSE_ABS_MAE"]["points"]["median"], 2), _n(A["excursions"][h]["ADVERSE_ABS_MAE"]["ticks"]["median"], 1),
                    _n(A["excursions"][h]["ADVERSE_ABS_MAE"]["sigma"]["median"], 3), _n(A["dominance"][h]["median"], 2),
                    _n(A["dominance"][h]["fraction_gt_0"], 3), _n(A["dominance"][h]["fraction_lt_0"], 3)] for h in hs]))
    L.append("### Z.4 Excursion percentiles (ALL events; P75 / P95, points and σ units)\n")
    L.append(_tab(["h", "MFE P75 pts", "MFE P95 pts", "MFE P75 σ", "MFE P95 σ", "|MAE| P75 pts", "|MAE| P95 pts", "|MAE| P75 σ", "|MAE| P95 σ"],
                  [[h, *(_n(A["excursions"][h][a][u][q], 2 if u == "points" else 3) for a, u in (("MFE", "points"),) for q in ("p75", "p95")),
                    *(_n(A["excursions"][h]["MFE"]["sigma"][q], 3) for q in ("p75", "p95")),
                    *(_n(A["excursions"][h]["ADVERSE_ABS_MAE"]["points"][q], 2) for q in ("p75", "p95")),
                    *(_n(A["excursions"][h]["ADVERSE_ABS_MAE"]["sigma"][q], 3) for q in ("p75", "p95"))] for h in hs]))
    L.append("### Z.5 Time to extrema (ALL events; 1-based bar of the first occurrence)\n")
    L.append(_tab(["h", "bars→MFE mean/median/P75/P95", "bars→MAE mean/median/P75/P95", "P(MFE first)", "P(MAE first)", "P(same bar)"],
                  [[h, " / ".join(_n(A["time_to_extrema"][h]["bars_to_MFE"][k], 1) for k in ("mean", "median", "p75", "p95")),
                    " / ".join(_n(A["time_to_extrema"][h]["bars_to_MAE"][k], 1) for k in ("mean", "median", "p75", "p95")),
                    _rt(A["time_to_extrema"][h]["p_mfe_before_mae"]), _rt(A["time_to_extrema"][h]["p_mae_before_mfe"]), _rt(A["time_to_extrema"][h]["p_same_bar"])] for h in hs]))
    L.append("### Z.6 First passage (ALL events; AMBIGUOUS_SAME_BAR is never assigned a winner)\n")
    rows = []
    for kind in ("symmetric", "asymmetric"):
        for case, byh in A["first_passage"][kind].items():
            for h, r in byh.items():
                rows.append([case, h, r["n"], _rt(r["confirmed_target_first"]), _rt(r["confirmed_stop_first"]), _rt(r["ambiguous_same_bar"]), _rt(r["neither"])])
    L.append(_tab(["case", "h", "N", "confirmed target first", "confirmed stop first", "ambiguous same bar", "neither"], rows))
    L.append("### Z.7 Fixed bracket surface (ALL events) — " + rep["cost_banner"] + "\n")
    L.append(f"**{rep['selection_banner']}.** 64 fixed cells in the canonical order {rep['bracket_canonical_order']} (NOT sorted by performance). Primary variant = CONSERVATIVE_RESULT "
             "(AMBIGUOUS_SAME_BAR counted as STOP); the raw-path variant and per-year/per-fold detail are in the JSON. No bracket is recommended, ranked or selected; "
             "a bracket needs its own registered monetisation study with its own multiplicity accounting.\n")
    L.append(_tab(["expiry", "stop σ", "target σ", "N", "f/wk", "target", "stop(cons)", "expiry", "ambig", "mean pts", "median pts", "mean R", "PF gross", "win", "pos yrs", "pos folds"],
                  [[c["expiry_bars"], c["stop_sigma"], c["target_sigma"], c.get("n"), _n(c.get("frequency_per_week"), 2),
                    _n((c.get("target_hit_rate") or {}).get("rate"), 3), _n((c.get("stop_hit_rate_conservative") or {}).get("rate"), 3),
                    _n((c.get("expiry_rate") or {}).get("rate"), 3), _n((c.get("same_bar_ambiguous_rate") or {}).get("rate"), 3),
                    _n(c.get("mean_gross_points"), 2), _n(c.get("median_gross_points"), 2), _n(c.get("mean_R"), 3), _n(c.get("profit_factor_gross"), 2),
                    _n((c.get("win_rate") or {}).get("rate"), 3),
                    f"{c['year_stability']['positive_years']}/{c['year_stability']['eligible_years']}" if c.get("year_stability") else "n/a",
                    _n((c.get("fold_stability") or {}).get("positive_fold_fraction"), 2)] for c in A["bracket_surface"]]))
    L.append("### Z.8 Year-by-year path stability (every eligible year; negative years are shown)\n")
    groups = [("raw base event", "ALL")]
    for r in trials_rows:
        if r["decision"] in ("IS_SHORTLIST_ELIGIBLE", "IS_PROVISIONAL_CANDIDATE"):
            groups.append((f"{r['trial_id']} {r['target']}/{r['model']}/{r['state']}", f"{r['target']}|{r['model']}|{r['state']}"))
    for title, key in groups:
        c = rep["contexts"].get(key, {})
        while "same_events_as" in c:
            c = rep["contexts"][c["same_events_as"]]
        yt = c.get("yearly_table", {"rows": [], "ineligible_years": []})
        L.append(f"**{title}**\n")
        L.append(_tab(["YEAR", "N", "events/wk", "CONT_15", "CONT_30", "CONT_60", "CONT_120", "med MFE60", "med |MAE|60", "P75 MFE60", "P75 |MAE|60", "mean ret60", "median ret60"],
                      [[r["year"], r["n"], _n(r["events_per_week"], 2), *(_rt(r[f"CONT_{h}"]) for h in (15, 30, 60, 120)), _n(r["median_MFE_60"], 2), _n(r["median_absMAE_60"], 2),
                        _n(r["P75_MFE_60"], 2), _n(r["P75_absMAE_60"], 2), _n(r["mean_return_60"], 6), _n(r["median_return_60"], 6)] for r in yt["rows"]]))
        if yt["ineligible_years"]:
            L.append(f"_years below the eligibility minimum (not shown): {yt['ineligible_years']}_\n")
    L.append("### Z.9 Development-fold path stability (ALL events, 60-bar horizon)\n")
    L.append(_tab(["fold", "N", "continuation", "median dir. log return", "MFE median pts", "|MAE| median pts"],
                  [[f, v["endpoint"]["60"]["n"], _rt(v["continuation"]["60"]["continuation"]), _n(v["endpoint"]["60"]["directional_log_return"]["median"], 6),
                    _n(v["excursions"]["60"]["MFE"]["points"]["median"], 2), _n(v["excursions"]["60"]["ADVERSE_ABS_MAE"]["points"]["median"], 2)] for f, v in sorted(A["by_fold"].items())]))
    L.append("### Z.10 Filter-ladder path effects\n")
    lad = rep.get("ladder") or {}
    if not lad.get("steps"):
        L.append("_no filter_ladder declared_\n")
    else:
        L.append(f"**{lad['label']}.** {lad['note']}\n")
        rows = []
        for st in lad["steps"]:
            for h in ("15", "60", "120"):
                co = (st.get("core") or {}).get(h)
                dl = ((st.get("delta_vs_previous_step") or {}).get("per_horizon") or {}).get(h) or {}
                rows.append([st["step"], h, st["n_events"], _n(st["frequency_per_week"], 2), _rt(co["continuation"]["continuation"]) if co else "n/a",
                             _n(co["median_MFE_points"], 2) if co else "n/a", _n(co["p75_MFE_points"], 2) if co else "n/a", _n(co["p95_MFE_points"], 2) if co else "n/a",
                             _n(co["median_adverse_points"], 2) if co else "n/a", _n(co["p75_adverse_points"], 2) if co else "n/a", _n(co["p95_adverse_points"], 2) if co else "n/a",
                             _n(dl.get("continuation_rate"), 3)])
        L.append(_tab(["step", "h", "N", "f/wk", "continuation", "med MFE", "P75 MFE", "P95 MFE", "med adv", "P75 adv", "P95 adv", "Δ cont. vs prev"], rows))
    L.append("### Z.11 Diagnostic observations (registry/observations.csv; DIAGNOSTIC_ONLY = true)\n")
    L.append(_tab(["id", "category", "description"], [[r["observation_id"], r["category"], r["description"]] for _, r in my_obs.iterrows() if str(r["category"]).startswith(("path_", "bracket_"))]))
    return L
