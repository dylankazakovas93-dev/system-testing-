"""Bar-level end-to-end runs (synthetic 1-minute NQ-like bars through the REAL pipeline and the REAL CLIs).

Lifecycle covered at bar level: freeze -> IS run (stops at the human gate; near-tie analysis) -> [test code playing the human] approval ->
one-shot campaign SELECTION HOLDOUT (selection data) -> [human] final config -> automatic CPCV; and the direct path (holdout skipped, never read). The strong-mode external verification of the three model paths is injected here with the test-only
helper ``prepare_for_approval`` (the real verifier is exercised in test_verifier_bridge.py and in the reported verifier runs).
"""
import json
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pandas as pd
import pytest
import yaml

from engine import trial_registry as reg
from engine.common import CODE_ROOT, load_frozen
from engine.event_contract import EventContractError, EventSpecError
from engine.experiment_lifecycle import MutationDetected, create_experiment, experiment_dir, freeze, verify_manifest
from engine.experiment_runner import run_experiment
from engine.selection_holdout_stage import ApprovalError, validate_approval
from engine.synthetic import make_bars
from tests.scenario_helpers import (campaign_open_approval, human_approval, human_final_selection, prepare_for_approval, proposable, top_group_ids)

F = load_frozen()
PARTS = {"development_end": "2018-01-01", "selection_holdout_end": "2019-01-01", "lockbox_start": "2019-01-01"}
PART_ARGS = ["--development-end", PARTS["development_end"], "--selection-holdout-years", "1"]
N_DAYS = 820                                      # 2016-01-04 .. 2019-02: development 2016-17, SELECTION HOLDOUT 2018H1, gap, lockbox 2018-10 on
REPORT_SECTIONS = ["A. Experiment hypothesis", "B. Exact event definition", "C. Direction", "D. Raw event frequency", "E. Data period used",
                   "F. Exact selection trial count", "G. All 24 trial results", "H. Multiplicity adjustments", "I. Top configurations",
                   "J. Model agreement", "K. All IS calendar years", "L. All 5 purged DEVELOPMENT_CV folds", "M–Q.", "R. Feature diagnostics",
                   "S. Filter / component ladder", "T. Sensitivity diagnostics", "U. Why each shortlisted configuration was selected",
                   "V. Why every other configuration was rejected", "NT. CONFIGURATION UNCERTAINTY / NEAR-TIES", "W. Non-promotable interesting observations", "X. Exact hashes", "Y. SELECTION HOLDOUT status"]


def force_near_tie(ws, exp, mp):
    """TEST DOUBLE (disclosed): planted AR(1) bars give no natural near-tie (different horizons have different uplifts). Declare the engine's top-2
    same-side groups a near-tie cluster by patching the DIAGNOSTIC `near_tie.detect`; the holdout, final-config and CPCV stages then run for real."""
    from engine import near_tie
    j = json.loads((experiment_dir(ws, exp) / "results/IS_REPORT.json").read_text())
    groups = j["I_top_configurations"]["top_groups"]
    first = groups[0]
    second = next(g for g in groups[1:] if g["state"] == first["state"])
    members = [f"{exp}|{first['group_id']}", f"{exp}|{second['group_id']}"]
    cluster = {"cluster_id": "NEAR_TIE_CLUSTER_01", "side": first["state"], "members": members, "proposable_for_holdout": members,
               "is_ranks": {members[0]: first["rank"], members[1]: second["rank"]}, "pairs": []}
    real = near_tie.detect
    mp.setattr(near_tie, "detect", lambda w, e, f=None: {**real(w, e, f), "clusters": [cluster]})
    reg.set_status(ws, exp, "NEAR_TIE_REVIEW_REQUIRED", "test double: forced near-tie cluster")
    return members


def cli(*args, check=True):
    p = subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, cwd=str(CODE_ROOT))
    if check and p.returncode != 0:
        raise AssertionError(f"{args}\n{p.stdout}\n{p.stderr}")
    return p


def write_parquet(path, **kw):
    make_bars(N_DAYS, seed=7, **kw).reset_index().rename(columns={"index": "timestamp"}).to_parquet(path)


# ============================ the TradingView template, driven entirely through the CLI (no planted effect) ====================
@pytest.fixture(scope="module")
def golden(tmp_path_factory):
    base = tmp_path_factory.mktemp("golden")
    data = base / "NQ_synth.parquet"
    write_parquet(data)                                                       # includes SELECTION HOLDOUT AND lockbox rows: the CLI must discard them
    ws = base / "ws"
    cli("scripts/new_experiment.py", "--new-campaign", "C001", *PART_ARGS, "--workspace", ws)
    spec = ws / "experiments/EXP_0001/EVENT_SPEC.yaml"
    spec.write_text(spec.read_text().replace("TODO: one or two sentences.", "A confirmed pivot is followed by a path."))
    cli("scripts/freeze_experiment.py", "--experiment", "EXP_0001", "--workspace", ws)
    run = cli("scripts/run_experiment.py", "--experiment", "EXP_0001", "--data", data, "--workspace", ws)
    return {"ws": ws, "data": data, "run_stdout": run.stdout}


def test_run_experiment_prints_the_counters_and_stops(golden):
    out = golden["run_stdout"]
    assert "EXPERIMENT SELECTION TRIALS: 24 / 24" in out and "CAMPAIGN REVEALED SELECTION TRIALS: 24 / 480" in out
    assert "SELECTION HOLDOUT NOT ACCESSED" in out and "stopped for human review" in out


def test_is_report_has_sections_A_to_Y_and_the_sealed_selection_holdout_status(golden):
    ws = golden["ws"]
    text = (ws / "experiments/EXP_0001/results/IS_REPORT.md").read_text()
    for s in REPORT_SECTIONS:
        assert f"## {s}" in text, s
    assert "SELECTION HOLDOUT status = NOT ACCESSED" in text and "DIAGNOSTIC ONLY — NOT A SELECTION TRIAL" in text
    assert "NOT SELECTION HOLDOUT" in text and "4 targets × 3 models × 2 states = **24**" in text
    assert text.count("EXP_0001_T") >= 24 and "EXP_0001_T24" in text
    j = json.loads((ws / "experiments/EXP_0001/results/IS_REPORT.json").read_text())
    assert j["markdown_sha256"] and j["X_hashes"]["manifest_sha256"] and j["Y_selection_holdout_status"] == "NOT ACCESSED"


def test_registry_has_exactly_24_revealed_trials_and_no_selection_holdout_activity(golden):
    ws = reg.Workspace(golden["ws"])
    chk = reg.integrity_check(ws)
    assert chk["selection_trials"] == 24 and chk["revealed_trials"] == 24
    t = reg.experiment_trials(ws, "EXP_0001")
    assert len(t) == 24 and (t["status"] == "REVEALED").all()
    for col in ("experiment_bonferroni_p", "campaign_bonferroni_p", "experiment_q", "campaign_q"):
        assert t[col].notna().all(), col
    assert not t["decision"].isin(["IS_SHORTLIST_ELIGIBLE", "IS_PROVISIONAL_CANDIDATE"]).any()      # null data: nothing may survive
    assert reg.experiment_row(ws, "EXP_0001")["status"] == "IS_REJECTED"
    assert len(reg.read_selection_holdout_access(ws)) == 0 and not list(Path(golden["ws"], "approvals").glob("*.yaml"))
    res = json.loads((golden["ws"] / "experiments/EXP_0001/results/results.json").read_text())
    file_ts = pd.to_datetime(pd.read_parquet(golden["data"])["timestamp"], utc=True)
    n_dev = int((file_ts < pd.Timestamp(PARTS["development_end"], tz="UTC")).sum())
    assert len(file_ts) > n_dev                                                                   # the data file DID contain SELECTION HOLDOUT + lockbox rows ...
    assert res["base_event"]["development_bars"] == n_dev                                         # ... and exactly the development rows were used
    assert res["base_event"]["rows_removed_before_research"] == 0                                 # (the CLI loader never materialised the rest)
    assert pd.Timestamp(res["base_event"]["last_bar"]) < pd.Timestamp(PARTS["development_end"], tz="UTC")
    assert not list((golden["ws"] / "experiments/EXP_0001/results").glob("selection_holdout_*")) and not (golden["ws"] / "experiments/EXP_0001/results/SELECTION_HOLDOUT_REPORT.json").exists()
    man = json.loads((golden["ws"] / "experiments/EXP_0001/FROZEN_MANIFEST.json").read_text())
    assert man["partitions"] == PARTS and man["partitions_hash"]


def test_rerun_of_revealed_experiment_is_refused(golden):
    p = cli("scripts/run_experiment.py", "--experiment", "EXP_0001", "--data", golden["data"], "--workspace", golden["ws"], check=False)
    assert p.returncode != 0 and "already revealed" in (p.stderr + p.stdout)


def test_run_campaign_selection_holdout_refuses_without_a_human_approval_and_spends_nothing(golden):
    p = cli("scripts/run_campaign_selection_holdout.py", "--campaign", "C001", "--data", golden["data"], "--workspace", golden["ws"], check=False)
    assert p.returncode != 0 and "frozen" in (p.stderr + p.stdout).lower()
    ws = reg.Workspace(golden["ws"])
    assert len(reg.read_selection_holdout_access(ws)) == 0 and not list(Path(golden["ws"], "approvals").glob("*.yaml"))
    c = cli("scripts/run_cpcv.py", "--experiment", "EXP_0001", "--data", golden["data"], "--workspace", golden["ws"], check=False)
    assert c.returncode != 0 and len(reg.read_selection_holdout_access(ws)) == 0


def test_campaign_status_reports_counters_and_statuses(golden):
    out = cli("scripts/campaign_status.py", "--workspace", golden["ws"]).stdout
    assert "registry integrity" in out
    assert "CAMPAIGN REVEALED SELECTION TRIALS    : 24 / 480" in out and "experiments used                      : 1 / 20" in out
    assert "statistical selection opportunities exposed so far: 24" in out and "IS_REJECTED" in out


def test_make_report_rebuilds_the_is_report_from_stored_results(golden, tmp_path):
    ws_dir = tmp_path / "ws"
    shutil.copytree(golden["ws"], ws_dir)
    ws = reg.Workspace(ws_dir)
    before = reg.experiment_trials(ws, "EXP_0001").to_csv()
    cli("scripts/make_report.py", "--experiment", "EXP_0001", "--workspace", ws_dir)
    text = (ws_dir / "experiments/EXP_0001/results/IS_REPORT.md").read_text()
    for s in REPORT_SECTIONS:
        assert f"## {s}" in text
    assert reg.experiment_trials(ws, "EXP_0001").to_csv() == before


def test_mutation_after_reveal_forces_a_new_lineage_and_never_overwrites(golden, tmp_path):
    ws_dir = tmp_path / "ws"
    shutil.copytree(golden["ws"], ws_dir)
    ws = reg.Workspace(ws_dir)
    before = reg.experiment_trials(ws, "EXP_0001").to_csv()
    ev = ws_dir / "experiments/EXP_0001/event.py"
    ev.chmod(0o644)
    ev.write_text(ev.read_text().replace("pivot_left", "pivot_left  "))        # any byte change after results were revealed
    with pytest.raises(MutationDetected):
        verify_manifest(ws, "EXP_0001")
    cli("scripts/new_experiment.py", "--campaign", "C001", "--lineage-of", "EXP_0001", "--workspace", ws_dir)
    assert (ws_dir / "experiments/EXP_0002/LINEAGE.md").exists()
    assert reg.experiment_trials(ws, "EXP_0001").to_csv() == before                # the old experiment's rows are untouched
    status = cli("scripts/campaign_status.py", "--campaign", "C001", "--workspace", ws_dir).stdout
    assert "experiments used                      : 2 / 20" in status and "lineage_of=EXP_0001" in status


def test_cli_rejects_experiment_21_and_new_campaigns_need_explicit_partitions(tmp_path):
    ws_dir = tmp_path / "ws"
    cli("scripts/new_experiment.py", "--new-campaign", "C001", *PART_ARGS, "--workspace", ws_dir)
    for _ in range(19):
        cli("scripts/new_experiment.py", "--campaign", "C001", "--workspace", ws_dir)
    p = cli("scripts/new_experiment.py", "--campaign", "C001", "--workspace", ws_dir, check=False)
    assert p.returncode != 0 and "MAX_EXPERIMENTS_PER_CAMPAIGN=20" in (p.stderr + p.stdout)
    nodates = cli("scripts/new_experiment.py", "--new-campaign", "C002", "--workspace", ws_dir, check=False)
    assert nodates.returncode != 0 and "--development-end" in (nodates.stderr + nodates.stdout)
    p2 = cli("scripts/new_experiment.py", "--new-campaign", "C002", *PART_ARGS, "--workspace", ws_dir)
    assert "EXP_0021" in p2.stdout


# ============================ a planted bar-level edge: candidate + sensitivity + human gate + SELECTION HOLDOUT + CPCV ====================
def write_custom_event(ws, exp, *, mixed: bool, hypothesis: str, spec_values=(1,)):
    d = experiment_dir(ws, exp)
    (d / "event.py").write_text(textwrap.dedent('''
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
    '''))
    s = yaml.safe_load((d / "EVENT_SPEC.yaml").read_text())
    s["hypothesis"] = hypothesis
    s["direction_definition"] = {"rule": "long only" if not mixed else "alternating (v1 forbids this)", "values": list(spec_values)}
    s["event_condition"] = {"description": "every n-th bar of the supplied history", "parameters_used": ["every_n_bars", "direction_period", "direction"]}
    s["cooldown"] = {"bars": 0}
    s["deduplication_rule"] = "keep_first_per_event_time"
    s["base_parameters"] = {"every_n_bars": 45, "direction_period": 2 if mixed else 1, "direction": 1}
    s["sensitivity_parameters"] = ["every_n_bars"]
    s["expected_information_time"] = {"rule": "completion time of the n-th bar", "confirmation_delay_bars": 0}
    for k in ("tradingview", "indicator"):
        s.pop(k, None)
    (d / "EVENT_SPEC.yaml").write_text(yaml.safe_dump(s, sort_keys=False))


@pytest.fixture(scope="module")
def planted(tmp_path_factory):
    base = tmp_path_factory.mktemp("planted")
    data = base / "NQ_planted.parquet"
    write_parquet(data, phi=0.8)                                              # planted AR(1) momentum
    ws_dir = base / "ws"
    ws = reg.Workspace(ws_dir).init()
    exp = create_experiment(ws, new_campaign="C001", partitions=PARTS)
    write_custom_event(ws, exp, mixed=False, hypothesis="Planted AR(1) momentum makes recent path informative.")
    freeze(ws, exp)
    run = cli("scripts/run_experiment.py", "--experiment", exp, "--data", data, "--workspace", ws_dir)
    return {"ws_dir": ws_dir, "ws": ws, "exp": exp, "data": data, "stdout": run.stdout,
            "results": json.loads((experiment_dir(ws, exp) / "results/results.json").read_text())}


def test_planted_momentum_yields_provisional_candidates_that_pass_every_floor(planted):
    ws, exp = planted["ws"], planted["exp"]
    t = reg.experiment_trials(ws, exp)
    cand = t[t["decision"] == "IS_PROVISIONAL_CANDIDATE"]
    assert len(cand) > 0
    for target in ("DIR_RETURN_15", "DIR_PATH_SKEW_60"):                                      # the short-memory momentum shows at 15 minutes and in the 60-minute path skew
        assert (t[t["target"] == target]["decision"] == "IS_PROVISIONAL_CANDIDATE").all(), target
    assert not t[t["target"] == "DIR_RETURN_180"]["decision"].isin(["IS_PROVISIONAL_CANDIDATE", "IS_SHORTLIST_ELIGIBLE"]).any()   # AR(1) memory has decayed by 180 minutes
    for c in ("standardized_uplift", "selected_frequency", "selected_effect", "bootstrap_ci_low", "experiment_q", "campaign_q",
              "experiment_bonferroni_p", "campaign_bonferroni_p"):
        cand = cand.assign(**{c: pd.to_numeric(cand[c])})
    assert (cand["standardized_uplift"] >= 0.01).all() and (cand["selected_frequency"] >= 1.0).all()                       # v2: the 0.01 uplift floor
    assert (cand["selected_effect"] > 0).all() and (cand["bootstrap_ci_low"] > 0).all()
    assert (cand[["experiment_q", "campaign_q"]] <= 0.05).all().all()
    assert (pd.to_numeric(cand["raw_p"]) <= 0.00135).all()                                                                 # v2.2.0: t >= 3 hurdle
    rejected = t[~t["decision"].isin(["IS_PROVISIONAL_CANDIDATE", "IS_SHORTLIST_ELIGIBLE"])]
    assert len(rejected) > 0 and (rejected["decision"] != "PENDING").all()                    # rejected trials remain visible


def test_events_late_in_the_session_are_kept_and_their_long_horizon_targets_are_truncated_and_flagged(planted):
    """v2: nothing is dropped for crossing the close; the 180-minute target of a 13:00+ event ends at the close and carries truncated=True."""
    ws, exp, d = planted["ws"], planted["exp"], experiment_dir(planted["ws"], planted["exp"]) / "results"
    res = planted["results"]["base_event"]
    assert res["target_timestamp_ineligible"] == 0                                              # no event is removed for a long window crossing the close
    cv180 = pd.read_csv(d / "cv_DIR_RETURN_180_RIDGE.csv")
    cv15 = pd.read_csv(d / "cv_DIR_RETURN_15_RIDGE.csv")
    assert cv180["truncated"].any() and (~cv180["truncated"]).any() and not cv15["truncated"].any()
    local = pd.to_datetime(cv180["event_time"], utc=True).dt.tz_convert("America/New_York")
    mins = local.dt.hour * 60 + local.dt.minute
    assert (cv180["truncated"].to_numpy() == (mins > 13 * 60).to_numpy()).all()                  # truncated exactly when fewer than 180 minutes remain before 16:00
    wm = json.loads((d / "IS_REPORT.json").read_text())["WM_where_it_works"]
    assert wm["groups"] == {} and wm["available"] is False                                      # before verification there is no top group to map


def test_candidate_without_strong_verification_is_provisional_and_cannot_be_approved(planted):
    ws, exp = planted["ws"], planted["exp"]
    assert reg.experiment_row(ws, exp)["status"] == "IS_PROVISIONAL_CANDIDATE" and reg.experiment_row(ws, exp)["research_verification"] == "NOT_RUN"
    j = json.loads((experiment_dir(ws, exp) / "results/IS_REPORT.json").read_text())
    assert j["I_top_configurations"]["top_groups"] == []                                      # only shortlist-ELIGIBLE (verified) trials are ranked
    copy = planted["ws_dir"].parent / "unverified_copy"
    shutil.copytree(planted["ws_dir"], copy)
    cws = reg.Workspace(copy)
    human_approval(cws, exp, [f"{exp}|DIR_RETURN_15|UPPER_HALF"])                              # a human could write this file ...
    with pytest.raises(ApprovalError):
        validate_approval(cws, exp)                                                           # ... but it is not valid without verification
    assert len(reg.read_selection_holdout_access(cws)) == 0


def test_sensitivity_probes_ran_and_never_replace_the_base_parameter(planted):
    ws, exp, res = planted["ws"], planted["exp"], planted["results"]
    assert res["sensitivity"]["status"] == "RUN"
    grp = res["sensitivity"]["groups"]["DIR_RETURN_15|UPPER_HALF"]
    assert grp["verdict"] == "PASSED" and [p["value"] for p in grp["probes"]] == [34, 56]      # 45 x 0.75, x 1.25
    assert all(p["models_frequency_ok"] >= 2 for p in grp["probes"])
    assert verify_manifest(ws, exp)["errors"] == []                                           # spec + event untouched by probes
    spec = yaml.safe_load((experiment_dir(ws, exp) / "EVENT_SPEC.yaml").read_text())
    assert spec["base_parameters"]["every_n_bars"] == 45
    probe_counts = {p["n_events"] for p in grp["probes"]}
    assert res["base_event"]["n_events"] not in probe_counts and len(probe_counts) == 2       # probes really ran other events
    assert reg.experiment_row(ws, exp)["sensitivity_json"] != "{}"


def test_the_planted_run_never_touched_selection_holdout_or_the_lockbox(planted):
    ws, exp = planted["ws"], planted["exp"]
    assert len(reg.read_selection_holdout_access(ws)) == 0 and not list(Path(planted["ws_dir"], "approvals").glob("*.yaml"))
    assert pd.Timestamp(planted["results"]["base_event"]["last_bar"]) < pd.Timestamp(PARTS["development_end"], tz="UTC")
    assert "SELECTION HOLDOUT status = NOT ACCESSED" in (experiment_dir(ws, exp) / "results/IS_REPORT.md").read_text()


def test_path_diagnostics_are_non_promotable_content_cannot_move_ranking_but_tampering_breaks_approval_integrity(planted, tmp_path, monkeypatch):
    """PATH DIAGNOSTICS ARE NON-PROMOTABLE: drastically rewriting PATH_DIAGNOSTICS.json (and legitimately regenerating the report)
    leaves candidate status, trial/group ranking, the top-5 list, approval eligibility and SELECTION HOLDOUT group order untouched, while the
    hash-bound approval of the earlier report is invalidated."""
    from engine.acceptance import rank_groups, rank_trials
    from engine.is_report import write_is_report
    from engine.selection_holdout_stage import ApprovalError, approval_hashes, freeze_campaign_selection_holdout, validate_approval
    ws_dir = tmp_path / "ws"
    shutil.copytree(planted["ws_dir"], ws_dir)
    ws = reg.Workspace(ws_dir)
    exp = planted["exp"]
    prepare_for_approval(ws, exp)                                                              # test-only injection of strong verification; regenerates the report

    def formal():
        rows = reg.experiment_trials(ws, exp).to_dict("records")
        j = json.loads((experiment_dir(ws, exp) / "results/IS_REPORT.json").read_text())
        e = reg.experiment_row(ws, exp)
        return {"trials": reg.experiment_trials(ws, exp).to_csv(), "status": (e["status"], e["is_status"]),
                "trial_rank": [r["trial_id"] for r in rank_trials(rows)], "group_rank": [g["group_id"] for g in rank_groups(rows, F.acceptance, 5)],
                "top5": j["I_top_configurations"], "agreement": j["J_model_agreement"], "allowed": approval_hashes(ws, exp)["allowed_target_side_groups"],
                "eligible_ids": sorted(r["trial_id"] for r in rows if r["decision"] == "IS_SHORTLIST_ELIGIBLE")}
    pair = force_near_tie(ws, exp, monkeypatch)                                                # forced near-tie pair (test double, see force_near_tie)
    before = formal()
    assert before["status"][0] == "NEAR_TIE_REVIEW_REQUIRED" and len(before["top5"]["top_groups"]) >= 2
    human_approval(ws, exp, pair, near_tie_cluster_id="NEAR_TIE_CLUSTER_01")
    old_report_hash = approval_hashes(ws, exp)["is_report_sha256"]
    assert validate_approval(ws, exp)["approved_configs"] == pair

    # (a) raw tampering of the frozen diagnostic artifact (no regeneration) invalidates the hash-bound approval
    d = experiment_dir(ws, exp) / "results"
    original = (d / "PATH_DIAGNOSTICS.json").read_text()
    (d / "PATH_DIAGNOSTICS.json").write_text(original.replace("\"promotion_eligible\":false", "\"promotion_eligible\":true", 1))
    with pytest.raises(ApprovalError, match="PATH_DIAGNOSTICS.json changed"):
        validate_approval(ws, exp)
    (d / "PATH_DIAGNOSTICS.json").write_text(original)
    assert validate_approval(ws, exp)["approved_configs"] == pair

    # (b) drastic rewrite of every diagnostic number, consistently re-hashed and regenerated: formal results do not move
    rep = json.loads(original)
    for ctx in rep["contexts"].values():
        for cell in ctx.get("bracket_surface", []):
            cell.update(mean_gross_points=1e6, mean_R=1e3, median_gross_points=1e6, win_rate={"n": 1, "denominator": 1, "rate": 1.0})
        for h in ctx.get("continuation", {}):
            ctx["continuation"][h]["continuation"] = {"n": 1, "denominator": 1, "rate": 1.0}
    txt = json.dumps(rep, separators=(",", ":"), sort_keys=True)
    (d / "PATH_DIAGNOSTICS.json").write_text(txt)
    import hashlib
    res = json.loads((d / "results.json").read_text())
    res["path_diagnostics"]["sha256"] = hashlib.sha256(txt.encode()).hexdigest()
    (d / "results.json").write_text(json.dumps(res, indent=2, sort_keys=True))
    write_is_report(ws, exp)
    after = formal()
    assert after == before                                                                     # status, ranks, top-5, eligibility, trial rows: identical
    assert [c["members"] for c in json.loads((d / "IS_REPORT.json").read_text())["NT_configuration_uncertainty"]["clusters"]] == [pair]   # the (forced) cluster is untouched by the diagnostics rewrite
    new_hash = approval_hashes(ws, exp)["is_report_sha256"]
    assert new_hash != old_report_hash                                                         # but the artifact hash moved ...
    with pytest.raises(ApprovalError, match="is_report_sha256 does not match"):
        validate_approval(ws, exp)                                                             # ... so the OLD approval is no longer valid
    human_approval(ws, exp, pair, near_tie_cluster_id="NEAR_TIE_CLUSTER_01")                  # a NEW human approval over the new hashes accepts the SAME pair
    assert validate_approval(ws, exp)["approved_configs"] == pair
    with pytest.raises(ApprovalError, match="not one of the top-2"):                           # an attractive-looking non-proposable config is refused
        human_approval(ws, exp, [f"{exp}|DIR_RETURN_60|UPPER_HALF", pair[0]], near_tie_cluster_id="NEAR_TIE_CLUSTER_01")
        validate_approval(ws, exp)
    human_approval(ws, exp, pair, near_tie_cluster_id="NEAR_TIE_CLUSTER_01")
    doc = freeze_campaign_selection_holdout(ws, "C001")
    assert doc["experiments"][0]["approved_configs"] == pair and doc["n_holdout_evaluations"] == 6   # the holdout compares exactly the engine's near-tied pair


# ---------------- documented hard failure: mixed-direction events ----------------
def test_mixed_direction_events_are_a_hard_event_contract_failure_before_any_result(tmp_path):
    """Same planted structure, but the event alternates direction. v1 refuses it outright instead of hiding an effect."""
    ws = reg.Workspace(tmp_path).init()
    exp = create_experiment(ws, new_campaign="C001", partitions=PARTS)
    write_custom_event(ws, exp, mixed=True, hypothesis="Same planted momentum but events alternate direction.", spec_values=(1,))
    freeze(ws, exp)
    with pytest.raises(EventContractError, match="FAIL EVENT CONTRACT.*mixed-direction"):
        run_experiment(ws, exp, make_bars(N_DAYS, seed=7, phi=0.8), verbose=False)
    assert not reg.is_revealed(reg.experiment_row(ws, exp)) and reg.experiment_row(ws, exp)["status"] == "FROZEN"
    assert (reg.experiment_trials(ws, exp)["status"] == "PREREGISTERED").all()


def test_a_spec_that_declares_two_directions_cannot_be_frozen(tmp_path):
    ws = reg.Workspace(tmp_path).init()
    exp = create_experiment(ws, new_campaign="C001", partitions=PARTS)
    write_custom_event(ws, exp, mixed=True, hypothesis="alternating", spec_values=(1, -1))
    with pytest.raises(EventSpecError):
        freeze(ws, exp)


# ---------------- bar-level human gate -> one-shot SELECTION HOLDOUT -> human final config -> automatic CPCV (test code plays the human) ----------------
def approve_and_spend_selection_holdout(planted, name, data):
    from engine.partitions import load_bars_before, parse_partitions
    from engine.selection_holdout_stage import freeze_campaign_selection_holdout, run_campaign_selection_holdout
    ws_dir = planted["ws_dir"].parent / name
    shutil.copytree(planted["ws_dir"], ws_dir)
    ws = reg.Workspace(ws_dir)
    exp = planted["exp"]
    prepare_for_approval(ws, exp)                             # TEST-ONLY injection of strong verification of all 12 paths
    mp = pytest.MonkeyPatch()
    try:
        cfgs = force_near_tie(ws, exp, mp)                    # disclosed test double: a near-tie cluster is declared for the top-2 same-side groups
        human_approval(ws, exp, cfgs, near_tie_cluster_id="NEAR_TIE_CLUSTER_01")                          # TEST CODE PLAYING THE HUMAN
        freeze_campaign_selection_holdout(ws, "C001")         # closes the campaign (human-run step)
        campaign_open_approval(ws, "C001")                    # TEST CODE PLAYING THE HUMAN (second, campaign-level approval)
        bars = load_bars_before(data, parse_partitions(PARTS).selection_holdout_end)                     # the loader never reads the lockbox rows
        result = run_campaign_selection_holdout(ws, "C001", bars, verbose=False)
    finally:
        mp.undo()
    return {"ws_dir": ws_dir, "ws": ws, "exp": exp, "configs": cfgs, "result": result, "data": data}


@pytest.fixture(scope="module")
def after_selection_holdout(planted):
    return approve_and_spend_selection_holdout(planted, "ws_selection_holdout", planted["data"])


@pytest.fixture(scope="module")
def after_selection_holdout_poisoned_lockbox(planted):
    """Same approval, same experiment - but every row at/after selection_holdout_end (the final lockbox) is wrecked in the data file."""
    import numpy as np
    df = pd.read_parquet(planted["data"])
    ts = pd.to_datetime(df["timestamp"], utc=True)
    late = (ts >= pd.Timestamp(PARTS["selection_holdout_end"], tz="UTC")).to_numpy()
    assert late.sum() > 10_000
    rng = np.random.default_rng(99)
    df.loc[late, ["open", "high", "low", "close"]] = rng.uniform(1, 1e6, size=(int(late.sum()), 4))
    df.loc[late, "volume"] = -5.0
    df.iloc[-50:, df.columns.get_loc("close")] = np.nan
    bad = planted["ws_dir"].parent / "NQ_poisoned.parquet"
    df.to_parquet(bad)
    return approve_and_spend_selection_holdout(planted, "ws_selection_holdout_poisoned", bad)


def holdout_report(ws, exp):
    return json.loads((experiment_dir(ws, exp) / "results/SELECTION_HOLDOUT_REPORT.json").read_text())


def test_after_human_approval_the_bar_level_selection_holdout_runs_exactly_once(after_selection_holdout):
    ws, exp = after_selection_holdout["ws"], after_selection_holdout["exp"]
    assert after_selection_holdout["result"]["family_size"] == 6 and after_selection_holdout["result"]["campaign_status"] == "SELECTION_HOLDOUT_SPENT"
    ledger = reg.read_selection_holdout_access(ws)
    assert len(ledger) == 1 and ledger["campaign_id"].iloc[0] == "C001" and ledger["experiments"].iloc[0] == exp and reg.verify_selection_holdout_ledger(ws) == 1
    rep = holdout_report(ws, exp)
    assert rep["status"] == reg.experiment_row(ws, exp)["status"] == "SELECTION_HOLDOUT_SPENT"
    assert rep["label"] == "SELECTION DATA — USED TO CHOOSE FINAL CONFIGURATION / NOT FINAL CONFIRMATION" and rep["is_independent_confirmation"] is False
    rows = reg.read_selection_holdout_trials(ws)
    assert len(rows) == 6 and set(rows["model"]) == {"RIDGE", "SPLINE", "XGB"} and set(rows["group_id"]) == {c.split("|", 1)[1] for c in after_selection_holdout["configs"]}   # all 3 models per config
    assert rep["family_size_for_multiple_testing"] == 6 and rep["selection_holdout_period"] == [PARTS["development_end"], PARTS["selection_holdout_end"]]
    assert rep["preference"]["status"] in ("HOLDOUT_PREFERRED_CONFIG", "HOLDOUT_UNRESOLVED", "NO_QUALIFYING_CONFIG")


def test_bar_level_holdout_path_diagnostics_exist_only_for_the_frozen_configs_and_cannot_create_one(after_selection_holdout):
    """Selection-holdout path / MFE-MAE / bracket diagnostics are computed (bars are available) for the pre-frozen configs only, and may inform the human only."""
    ws, exp = after_selection_holdout["ws"], after_selection_holdout["exp"]
    rep = holdout_report(ws, exp)
    pi = rep["path_diagnostics"]
    assert pi["status"] == "COMPUTED" and pi["label"].startswith("SELECTION DATA") and "GROSS" in pi["cost_banner"] and "NO BRACKET WAS SELECTED" in pi["selection_banner"]
    approved = set(after_selection_holdout["configs"])
    assert {k.rsplit("|", 1)[0] for k in pi["per_config_model"]} == approved                       # nothing but the frozen configs
    assert {k.rsplit("|", 1)[1] for k in pi["per_config_model"]} == {"RIDGE", "SPLINE", "XGB"} and pi["all_holdout_events"]["n_events"] > 0
    for k, v in pi["per_config_model"].items():
        assert v == {} or ({"continuation_60", "reversal_60", "median_MFE_points_60", "median_abs_MAE_points_60", "bracket_cells"} <= set(v) and v["bracket_cells"] == 64)
    f = experiment_dir(ws, exp) / "results" / pi["file"]
    import hashlib
    assert hashlib.sha256(f.read_bytes()).hexdigest() == pi["sha256"]
    md = (experiment_dir(ws, exp) / "results/SELECTION_HOLDOUT_REPORT.md").read_text()
    assert "Path / bracket diagnostics of the holdout (SELECTION DATA)" in md and "may inform the HUMAN's choice among configs frozen before the holdout opened" in md
    # the diagnostics do not enter the deterministic preference: the preference module cannot see them
    import inspect

    from engine import holdout_preference
    assert "path" not in inspect.getsource(holdout_preference).lower().replace("path/bracket", "").replace("path-free", "").replace("path / bracket", "")


def test_second_selection_holdout_unlock_and_is_report_regeneration_are_refused_afterwards(after_selection_holdout):
    from engine.is_report import NOT_ACCESSED, selection_holdout_status_label
    ws, exp = after_selection_holdout["ws"], after_selection_holdout["exp"]
    p = cli("scripts/run_campaign_selection_holdout.py", "--campaign", "C001", "--data", after_selection_holdout["data"], "--workspace", after_selection_holdout["ws_dir"], check=False)
    assert p.returncode != 0 and "SPENT" in (p.stderr + p.stdout) and len(reg.read_selection_holdout_access(ws)) == 1
    m = cli("scripts/make_report.py", "--experiment", exp, "--workspace", after_selection_holdout["ws_dir"], check=False)
    assert m.returncode != 0 and "SELECTION HOLDOUT SPENT" in (m.stderr + m.stdout)                          # 'NOT ACCESSED' can no longer be printed
    label = selection_holdout_status_label(ws, exp)
    assert label != NOT_ACCESSED and label.startswith("SELECTION HOLDOUT SPENT")


def test_poisoned_lockbox_rows_cannot_change_a_single_selection_holdout_result(after_selection_holdout, after_selection_holdout_poisoned_lockbox):
    exp = after_selection_holdout["exp"]
    a = holdout_report(after_selection_holdout["ws"], exp)
    b = holdout_report(after_selection_holdout_poisoned_lockbox["ws"], exp)
    assert a["status"] == b["status"] and a["selection_holdout_bars_fingerprint"] == b["selection_holdout_bars_fingerprint"]
    assert a["evaluations"] == b["evaluations"] and a["evidence_gate_verdicts"] == b["evidence_gate_verdicts"] and a["preference"] == b["preference"]    # every statistic is identical
    assert a["path_diagnostics"]["sha256"] == b["path_diagnostics"]["sha256"] and a["path_diagnostics"]["per_config_model"] == b["path_diagnostics"]["per_config_model"]
    assert pd.Timestamp(a["selection_holdout_period"][1]) <= pd.Timestamp(PARTS["lockbox_start"])


def pick_config(rep):
    pref = rep["preference"]
    return pref.get("holdout_preferred_config") or pref.get("ranking_leader_advisory") or rep["approved_configs"][0]


@pytest.fixture(scope="module")
def after_final_config(after_selection_holdout):
    """The human chooses one frozen config (the advisory preference if there is one); the engine freezes it and runs CPCV AUTOMATICALLY."""
    ws, exp, ws_dir = after_selection_holdout["ws"], after_selection_holdout["exp"], after_selection_holdout["ws_dir"]
    pick = pick_config(holdout_report(ws, exp))
    human_final_selection(ws, exp, pick)                                     # TEST CODE PLAYING THE HUMAN
    out = cli("scripts/finalize_final_config.py", "--experiment", exp, "--data", after_selection_holdout["data"], "--workspace", ws_dir)
    return {**after_selection_holdout, "pick": pick, "stdout": out.stdout}


def test_bar_level_final_config_freezes_then_cpcv_runs_automatically_and_only_vetoes(after_final_config):
    ws, exp, pick = after_final_config["ws"], after_final_config["exp"], after_final_config["pick"]
    rep = json.loads((experiment_dir(ws, exp) / "results/CPCV_REPORT.json").read_text())
    assert "POST-SELECTION ROBUSTNESS — NOT INDEPENDENT CONFIRMATION" in after_final_config["stdout"] and rep["final_config_id"] == pick
    cp = reg.read_cpcv(ws)
    assert len(cp) == 3 and set(cp["model"]) == {"RIDGE", "SPLINE", "XGB"} and set(cp["group_id"]) == {pick.split("|", 1)[1]}     # exactly the ONE frozen config
    assert rep["n_splits"] == 15 and all(int(v["n_valid_splits"]) == 15 for v in rep["summary"].values())
    assert rep["data_used"] == "DEVELOPMENT + SELECTION_HOLDOUT" and rep["final_lockbox_accessed"] is False
    status = reg.experiment_row(ws, exp)["status"]
    assert status in ("AWAITING_FINAL_LOCKBOX_APPROVAL", "CPCV_REJECTED") and (status == "AWAITING_FINAL_LOCKBOX_APPROVAL") == rep["cpcv_passed"]
    led = reg.read_final_configs(ws)
    assert list(led["event"]) == ["FINAL_CONFIG_FROZEN", "CPCV_RESULT"] and reg.verify_final_config_ledger(ws) == 2 and set(led["selected_config_id"]) == {pick}
    assert [p.name for p in ws.approvals.glob("*")].count(f"{exp}_FINAL_CONFIG_SELECTION.yaml") == 1 and not any("CPCV" in p.name for p in ws.approvals.glob("*"))   # no CPCV approval exists
    p = cli("scripts/confirm_lockbox.py", check=False)
    assert p.returncode != 0 and "not implemented" in (p.stderr + p.stdout)                    # the lockbox stays sealed (stub)


def test_bar_level_cpcv_is_identical_when_the_lockbox_rows_are_poisoned(after_final_config, after_selection_holdout_poisoned_lockbox):
    exp = after_final_config["exp"]
    pick = after_final_config["pick"]
    ws2, dir2 = after_selection_holdout_poisoned_lockbox["ws"], after_selection_holdout_poisoned_lockbox["ws_dir"]
    human_final_selection(ws2, exp, pick)
    cli("scripts/finalize_final_config.py", "--experiment", exp, "--data", after_selection_holdout_poisoned_lockbox["data"], "--workspace", dir2)
    a = json.loads((experiment_dir(after_final_config["ws"], exp) / "results/CPCV_REPORT.json").read_text())
    b = json.loads((experiment_dir(ws2, exp) / "results/CPCV_REPORT.json").read_text())
    assert a["summary"] == b["summary"] and a["records"] == b["records"] and a["cpcv_passed"] == b["cpcv_passed"]


@pytest.fixture(scope="module")
def direct_selection(planted):
    """Direct final selection from the IS report: holdout skipped. The data file has every row at/after development_end wrecked."""
    import numpy as np
    df = pd.read_parquet(planted["data"])
    ts = pd.to_datetime(df["timestamp"], utc=True)
    late = (ts >= pd.Timestamp(PARTS["development_end"], tz="UTC")).to_numpy()
    rng = np.random.default_rng(5)
    df.loc[late, ["open", "high", "low", "close"]] = rng.uniform(1, 1e6, size=(int(late.sum()), 4))
    df.loc[late, "volume"] = -5.0
    bad = planted["ws_dir"].parent / "NQ_post_dev_poisoned.parquet"
    df.to_parquet(bad)
    out = {}
    for name, data in (("clean", planted["data"]), ("poisoned", bad)):
        ws_dir = planted["ws_dir"].parent / f"ws_direct_{name}"
        shutil.copytree(planted["ws_dir"], ws_dir)
        ws = reg.Workspace(ws_dir)
        exp = planted["exp"]
        prepare_for_approval(ws, exp)
        cfg = f"{exp}|{top_group_ids(ws, exp)[0]}"                           # one deterministic IS-eligible config, chosen directly by the human
        human_final_selection(ws, exp, cfg)
        run = cli("scripts/finalize_final_config.py", "--experiment", exp, "--data", data, "--workspace", ws_dir)
        out[name] = {"ws": ws, "ws_dir": ws_dir, "cfg": cfg, "stdout": run.stdout,
                     "cpcv": json.loads((experiment_dir(ws, exp) / "results/CPCV_REPORT.json").read_text())}
    return {"exp": planted["exp"], **out}


def test_direct_final_selection_skips_the_holdout_and_cpcv_uses_development_only(direct_selection):
    exp = direct_selection["exp"]
    for name in ("clean", "poisoned"):
        d = direct_selection[name]
        ws = d["ws"]
        assert reg.read_selection_holdout_access(ws).empty and reg.campaign_row(ws, "C001")["status"] == "OPEN"          # the unused holdout was never opened
        assert not (experiment_dir(ws, exp) / "results/SELECTION_HOLDOUT_REPORT.json").exists()
        h = [x[0] for x in json.loads(reg.experiment_row(ws, exp)["status_history"])]
        assert "SELECTION_HOLDOUT_SKIPPED" in h and h.index("SELECTION_HOLDOUT_SKIPPED") < h.index("FINAL_CONFIG_FROZEN")
        assert d["cpcv"]["data_used"].startswith("DEVELOPMENT only") and d["cpcv"]["selection_holdout_used"] is False and d["cpcv"]["final_config_id"] == d["cfg"]
        assert reg.read_final_configs(ws).iloc[0]["selection_holdout_used"] == "no"
    a, b = direct_selection["clean"]["cpcv"], direct_selection["poisoned"]["cpcv"]
    assert a["summary"] == b["summary"] and a["records"] == b["records"]    # wrecking every row after development_end changes nothing: those rows are never read
