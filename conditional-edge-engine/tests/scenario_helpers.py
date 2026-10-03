"""Run a table-level synthetic scenario through the REAL pipeline:
freeze -> DEVELOPMENT_CV panels -> 24 trials -> statistics -> acceptance -> registry -> IS report.

Table-level runs have no bars: they call ``finish_is`` with module=None (no ladder, no sensitivity run, no event causality
pre-check). Verification / sensitivity verdicts that the bar-level pipeline would obtain from the real verifier and the real
probes are injected explicitly through the registry API in the tests that need them (the real verifier is exercised in
test_verifier_bridge.py and in the reported end-to-end run)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine import trial_registry as reg
from engine.common import load_frozen, model_names, primary_target_names
from engine.event_contract import load_spec
from engine.experiment_lifecycle import create_experiment, experiment_dir, freeze, verify_manifest
from engine.experiment_runner import finish_is, run_panels
from engine.partitions import parse_partitions
from engine.synthetic import make_event_tables

FROZEN = load_frozen()
PARTS = {"development_end": "2023-01-01", "selection_holdout_end": "2024-01-01", "lockbox_start": "2024-01-01"}


def new_frozen_experiment(ws, campaign="C001", partitions=None):
    if campaign not in set(reg.read_campaigns(ws)["campaign_id"]):
        exp = create_experiment(ws, new_campaign=campaign, partitions=partitions or PARTS)
    else:
        exp = create_experiment(ws, campaign_id=campaign)
    p = experiment_dir(ws, exp) / "EVENT_SPEC.yaml"
    p.write_text(p.read_text().replace("TODO: one or two sentences.", "A confirmed pivot is followed by a path."))
    freeze(ws, exp)
    return exp


def slice_tables(tables, end_ts):
    """Rows whose events are before ``end_ts`` and whose primary targets resolved before it (what a partition would give)."""
    events, features, eligible, targets, calendar = tables
    end = pd.Timestamp(end_ts)
    end = end.tz_localize("UTC") if end.tzinfo is None else end.tz_convert("UTC")
    keep = np.asarray(pd.DatetimeIndex(events["event_time"]) < end)
    ev = events[keep].reset_index(drop=True)
    ft = features[keep].reset_index(drop=True)
    ft.attrs = dict(features.attrs)
    tg = {k: v[(pd.DatetimeIndex(v["effective_target_end"]) <= end) & v["event_id"].isin(set(ev["event_id"]))].reset_index(drop=True)
          for k, v in targets.items()}
    return ev, ft, np.asarray(eligible)[keep], tg, calendar[calendar < end]


def base_info(events, calendar):
    weeks = len(set(calendar.strftime("%G-%V")))
    return {"n_events": int(len(events)), "n_model_eligible": int(len(events)), "trading_weeks": weeks,
            "raw_event_frequency_per_week": len(events) / weeks, "direction": 1, "flag": "", "unused_parameters": [],
            "target_timestamp_ineligible": 0, "development_bars": 0, "first_bar": str(calendar[0]), "last_bar": str(calendar[-1]),
            "rows_removed_before_research": 0, "forward_windows_crossing_gaps": 0}


def run_is_tables(ws, tables, campaign="C001", partitions=None, exp=None):
    """IS stage on DEVELOPMENT-only tables. Returns (exp_id, trials_df, panels)."""
    exp = exp or new_frozen_experiment(ws, campaign, partitions)
    d = experiment_dir(ws, exp)
    spec = load_spec(d / "EVENT_SPEC.yaml")
    parts = parse_partitions(spec["partitions"])
    dev = slice_tables(tables, parts.development_end)
    events, features, eligible, targets, calendar = dev
    panels = run_panels(events, features, targets, eligible, calendar, FROZEN)
    finish_is(ws, exp, panels, events, features, eligible, FROZEN, spec=spec, base=base_info(events, calendar),
              causality={"cutoffs": 0}, verified=verify_manifest(ws, exp), data_label="synthetic-tables", parts=parts,
              run_sensitivity_stage=False)
    return exp, reg.experiment_trials(ws, exp), panels


def run_scenario(ws, tables, campaign="C001"):
    return run_is_tables(ws, tables, campaign)


def pass_all_paths(ws, exp):
    """Test-only injection of 'strong-mode research families PASS' for all 12 model paths (see module docstring)."""
    paths = {f"{t}|{m}": {"label": "RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE", "mode": "strong"}
             for t in primary_target_names(FROZEN) for m in model_names(FROZEN)}
    reg.set_verification(ws, exp, paths, "RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE", FROZEN)


def pass_sensitivity(ws, exp):
    """Test-only injection of sensitivity PASSED for every target|side group."""
    groups = {f"{t}|{s}": "PASSED" for t in primary_target_names(FROZEN) for s in FROZEN.trial_policy["states"]}
    return reg.set_sensitivity(ws, exp, groups, FROZEN)


def fake_results(ws, exp, p_by_pair=None, default_p=0.9, good=True, **over):
    """Crafted result dicts for registry-level multiplicity tests (no modelling)."""
    p_by_pair = p_by_pair or {}
    out = {}
    for _, r in reg.experiment_trials(ws, exp).iterrows():
        p = p_by_pair.get((r["target"], r["model"]), default_p)
        row = dict(n_parent=2000, n_selected=1000, parent_frequency=4.0, selected_frequency=2.0, retention_ratio=0.5,
                   parent_effect=0.0, selected_effect=0.2, uplift=0.2, target_sd=1.0, standardized_uplift=0.2 if good else 0.0,
                   bootstrap_ci_low=0.05, bootstrap_ci_high=0.3, raw_p=p, positive_years=5, positive_uplift_years=5,
                   eligible_years=5, folds_evaluated=5, positive_effect_folds=5, positive_uplift_folds=5,
                   year_concentration_share=0.25, year_concentration_warning=False, n_cv_weeks=500.0)
        row.update(over)
        out[r["trial_id"]] = row
    return out


# ============================ lifecycle helpers (IS -> human approval -> SELECTION HOLDOUT -> CPCV) ============================
LIFE_PARTS = {"development_end": "2020-01-01", "selection_holdout_end": "2021-01-01", "lockbox_start": "2021-01-01"}


def prepare_for_approval(ws, exp):
    """Inject strong-mode verification of all paths + sensitivity PASSED (test-only), then regenerate the IS report."""
    from engine.is_report import write_is_report
    pass_all_paths(ws, exp)
    pass_sensitivity(ws, exp)
    write_is_report(ws, exp)
    return reg.experiment_row(ws, exp)


def top_group_ids(ws, exp):
    import json
    j = json.loads((experiment_dir(ws, exp) / "results" / "IS_REPORT.json").read_text())
    return [g["group_id"] for g in j["I_top_configurations"]["top_groups"]]


def cluster_of(ws, exp, config_id):
    """The IS-report near-tie cluster id containing ``config_id`` (read from the report the human saw)."""
    import json
    j = json.loads((experiment_dir(ws, exp) / "results" / "IS_REPORT.json").read_text())
    return next((c["cluster_id"] for c in j["NT_configuration_uncertainty"]["clusters"] if config_id in c["members"]), None)


def proposable(ws, exp, cluster_index=0):
    """The (up to 2) configs the IS report allows to be proposed for the selection holdout, from the cluster_index-th near-tie cluster."""
    import json
    j = json.loads((experiment_dir(ws, exp) / "results" / "IS_REPORT.json").read_text())
    return list(j["NT_configuration_uncertainty"]["clusters"][cluster_index]["proposable_for_holdout"])


def human_approval(ws, exp, configs, **override):
    """TEST CODE PLAYING THE HUMAN: writes approvals/EXP_xxxx_SELECTION_HOLDOUT_APPROVAL.yaml for the exact frozen state.
    (No production script or LLM may do this - AGENTS.md rule 1.)  ``configs`` are config ids '<exp>|<TARGET>|<STATE>'."""
    import yaml

    from engine.selection_holdout_stage import approval_hashes, approval_path
    h = approval_hashes(ws, exp)
    doc = {"experiment_id": exp, "campaign_id": reg.experiment_row(ws, exp)["campaign_id"],
           "manifest_sha256": h["manifest_sha256"], "is_report_sha256": h["is_report_sha256"],
           "near_tie_cluster_id": cluster_of(ws, exp, list(configs)[0]) if configs else None,
           "approved": True, "approved_by": "HUMAN_USER", "approved_configs": list(configs),
           "approval_note": "test: human approves the near-tied configs for the one-shot SELECTION HOLDOUT"}
    doc.update(override)
    ws.approvals.mkdir(parents=True, exist_ok=True)
    p = approval_path(ws, exp)
    p.write_text(yaml.safe_dump(doc))
    return p


def human_final_selection(ws, exp, config, **override):
    """TEST CODE PLAYING THE HUMAN: writes approvals/EXP_xxxx_FINAL_CONFIG_SELECTION.yaml (exactly one config or DECLINE)."""
    import yaml

    from engine.selection_holdout_stage import approval_hashes, final_selection_path
    h = approval_hashes(ws, exp)
    doc = {"experiment_id": exp, "campaign_id": reg.experiment_row(ws, exp)["campaign_id"], "manifest_sha256": h["manifest_sha256"],
           "is_report_sha256": h["is_report_sha256"], "selection_holdout_report_sha256": h.get("selection_holdout_report_sha256"),
           "selected_config_id": config, "selected_by": "HUMAN_USER", "selection_note": "test: the human chooses exactly one configuration"}
    doc.update(override)
    ws.approvals.mkdir(parents=True, exist_ok=True)
    p = final_selection_path(ws, exp)
    p.write_text(yaml.safe_dump(doc))
    return p


def campaign_open_approval(ws, campaign_id, /, **override):
    """TEST CODE PLAYING THE HUMAN: writes approvals/CAMPAIGN_xxxx_SELECTION_HOLDOUT_OPEN_APPROVAL.yaml citing the exact freeze hash."""
    import yaml

    from engine.selection_holdout_stage import campaign_approval_path
    doc = {"campaign_id": campaign_id, "selection_holdout_freeze_sha256": reg.campaign_row(ws, campaign_id)["selection_holdout_freeze_hash"],
           "approved_by": "HUMAN_USER", "approved": True, "approval_note": "test: human opens the shared campaign SELECTION HOLDOUT once"}
    doc.update(override)
    ws.approvals.mkdir(parents=True, exist_ok=True)
    p = campaign_approval_path(ws, campaign_id)
    p.write_text(yaml.safe_dump(doc))
    return p


def open_campaign_selection_holdout(ws, campaign_id, tables_by_exp, parts=LIFE_PARTS, *, freeze=True):
    """Freeze (optional; the experiments' human approvals must already exist) and open the campaign SELECTION HOLDOUT from table-level data.
    ``tables_by_exp`` = {experiment_id: tables}. Returns the campaign result dict (per-experiment reports under 'reports')."""
    from engine.selection_holdout_stage import execute_campaign_selection_holdout, freeze_campaign_selection_holdout, validate_campaign_open
    from engine.selection_holdout_stage import campaign_approval_path
    if freeze and reg.campaign_row(ws, campaign_id)["status"] == "OPEN":
        freeze_campaign_selection_holdout(ws, campaign_id)
    if not campaign_approval_path(ws, campaign_id).exists():
        campaign_open_approval(ws, campaign_id)
    doc, cap, aps = validate_campaign_open(ws, campaign_id)
    items = []
    for e, ap in aps.items():
        ev, ft, el, tg, cal = slice_tables(tables_by_exp[e], parts["selection_holdout_end"])
        items.append((e, ap, (lambda ev=ev, ft=ft, el=el, tg=tg: (ev, ft, el, tg)), cal, None))
    return execute_campaign_selection_holdout(ws, campaign_id, cap, items, "fingerprint-synthetic", verbose=False)


def spend_selection_holdout(ws, exp, tables, parts=LIFE_PARTS):
    """Single-experiment campaign convenience: freeze + open the experiment's campaign. Returns that experiment's SELECTION HOLDOUT report."""
    r = open_campaign_selection_holdout(ws, reg.experiment_row(ws, exp)["campaign_id"], {exp: tables}, parts)
    return r["reports"][exp]


def run_cpcv_stage(ws, exp, tables):
    """The automatic CPCV on table-level data: exactly the data CPCV would load (development [+ selection holdout]); never the lockbox."""
    from engine.cpcv import cpcv_cutoff, execute_cpcv
    cutoff, _ = cpcv_cutoff(ws, exp)
    ev, ft, el, tg, cal = slice_tables(tables, cutoff)
    return execute_cpcv(ws, exp, ev, ft, tg, el, cal, verbose=False)


def finalize_config(ws, exp, tables, config, *, run_cpcv=True, **override):
    """The human writes the final-config file; the engine validates + freezes it; fixed CPCV then runs automatically (no approval)."""
    from engine.selection_holdout_stage import freeze_final_config
    human_final_selection(ws, exp, config, **override)
    info = freeze_final_config(ws, exp)
    return info, (run_cpcv_stage(ws, exp, tables) if run_cpcv and not info["decline"] else None)


# table fixtures: which targets carry the planted relation (target_scale) -------------------------------------------------------------------------
CLEAR_WINNER = dict(signal="linear", slope=0.35, target_scale={"DIR_RETURN_15": 0.0, "DIR_RETURN_60": 0.0, "DIR_PATH_SKEW_60": 0.0})   # only DIR_RETURN_30 eligible
NEAR_TIE_PAIR = dict(signal="linear", slope=0.35, target_scale={"DIR_RETURN_30": 0.0, "DIR_PATH_SKEW_60": 0.0})                         # 15 and 60 near-tie per side


def make_tie_tables(**kw):
    """Event tables where DIR_RETURN_15 and DIR_RETURN_60 carry the same planted relation AND the same noise (60's labels are 15's): the pair is
    near-tied on both sides by construction, for any seed. DIR_RETURN_30 / path-skew carry no effect."""
    kw.setdefault("signal", "linear")
    kw["target_scale"] = {"DIR_RETURN_30": 0.0, "DIR_PATH_SKEW_60": 0.0}
    events, features, eligible, targets, cal = make_event_tables(**kw)
    targets = {k: v.copy() for k, v in targets.items()}
    targets["DIR_RETURN_60"]["value"] = targets["DIR_RETURN_15"]["value"].to_numpy().copy()
    return events, features, eligible, targets, cal


def weaken(tables, target, years, frac, slope=0.35, feature="ER_60"):
    """Test-only: remove ``frac`` of the planted relation of ``target`` for events of ``years`` (used to shape SELECTION HOLDOUT outcomes)."""
    events, features, eligible, targets, cal = tables
    tg = {k: v.copy() for k, v in targets.items()}
    yrs = pd.DatetimeIndex(events["event_time"]).year
    m = np.isin(yrs, list(years))
    v = tg[target]["value"].to_numpy().copy()
    v[m] = v[m] - frac * slope * features[feature].to_numpy()[m]
    tg[target]["value"] = v
    return events, features, eligible, tg, cal


def lifecycle_workspace(root, **table_kw):
    """Fresh workspace + IS stage on DEVELOPMENT-only tables, prepared for human approval. Returns (ws, exp, tables)."""
    ws = reg.Workspace(root).init()
    tables = make_event_tables(**table_kw)
    exp, trials, panels = run_is_tables(ws, tables, partitions=LIFE_PARTS)
    prepare_for_approval(ws, exp)
    return ws, exp, tables
