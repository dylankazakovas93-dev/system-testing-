"""Bar-level end-to-end runs (synthetic 1-minute NQ-like bars through the REAL pipeline and the REAL CLIs).

Lifecycle covered at bar level: freeze -> IS run (stops at the human gate) -> [test code playing the human] approval ->
one-shot OOS -> CPCV. The strong-mode external verification of the three model paths is injected here with the test-only
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
from engine.oos_stage import ApprovalError, validate_approval
from engine.synthetic import make_bars
from tests.scenario_helpers import campaign_open_approval, human_approval, prepare_for_approval, top_group_ids

F = load_frozen()
PARTS = {"development_end": "2018-01-01", "oos_end": "2018-07-01", "lockbox_start": "2018-10-01"}
PART_ARGS = ["--development-end", PARTS["development_end"], "--oos-end", PARTS["oos_end"], "--lockbox-start", PARTS["lockbox_start"]]
N_DAYS = 820                                      # 2016-01-04 .. 2019-02: development 2016-17, OOS 2018H1, gap, lockbox 2018-10 on
REPORT_SECTIONS = ["A. Experiment hypothesis", "B. Exact event definition", "C. Direction", "D. Raw event frequency", "E. Data period used",
                   "F. Exact selection trial count", "G. All 24 trial results", "H. Multiplicity adjustments", "I. Top configurations",
                   "J. Model agreement", "K. All IS calendar years", "L. All 5 purged DEVELOPMENT_CV folds", "M–Q.", "R. Feature diagnostics",
                   "S. Filter / component ladder", "T. Sensitivity diagnostics", "U. Why each shortlisted configuration was selected",
                   "V. Why every other configuration was rejected", "W. Non-promotable interesting observations", "X. Exact hashes", "Y. OOS status"]


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
    write_parquet(data)                                                       # includes OOS AND lockbox rows: the CLI must discard them
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
    assert "OOS NOT ACCESSED" in out and "stopped for human review" in out


def test_is_report_has_sections_A_to_Y_and_the_sealed_oos_status(golden):
    ws = golden["ws"]
    text = (ws / "experiments/EXP_0001/results/IS_REPORT.md").read_text()
    for s in REPORT_SECTIONS:
        assert f"## {s}" in text, s
    assert "OOS status = NOT ACCESSED" in text and "DIAGNOSTIC ONLY — NOT A SELECTION TRIAL" in text
    assert "NOT OOS" in text and "4 targets × 3 models × 2 states = **24**" in text
    assert text.count("EXP_0001_T") >= 24 and "EXP_0001_T24" in text
    j = json.loads((ws / "experiments/EXP_0001/results/IS_REPORT.json").read_text())
    assert j["markdown_sha256"] and j["X_hashes"]["manifest_sha256"] and j["Y_oos_status"] == "NOT ACCESSED"


def test_registry_has_exactly_24_revealed_trials_and_no_oos_activity(golden):
    ws = reg.Workspace(golden["ws"])
    chk = reg.integrity_check(ws)
    assert chk["selection_trials"] == 24 and chk["revealed_trials"] == 24
    t = reg.experiment_trials(ws, "EXP_0001")
    assert len(t) == 24 and (t["status"] == "REVEALED").all()
    for col in ("experiment_bonferroni_p", "campaign_bonferroni_p", "experiment_q", "campaign_q"):
        assert t[col].notna().all(), col
    assert not t["decision"].isin(["IS_SHORTLIST_ELIGIBLE", "IS_PROVISIONAL_CANDIDATE"]).any()      # null data: nothing may survive
    assert reg.experiment_row(ws, "EXP_0001")["status"] == "IS_REJECTED"
    assert len(reg.read_oos_access(ws)) == 0 and not list(Path(golden["ws"], "approvals").glob("*.yaml"))
    res = json.loads((golden["ws"] / "experiments/EXP_0001/results/results.json").read_text())
    file_ts = pd.to_datetime(pd.read_parquet(golden["data"])["timestamp"], utc=True)
    n_dev = int((file_ts < pd.Timestamp(PARTS["development_end"], tz="UTC")).sum())
    assert len(file_ts) > n_dev                                                                   # the data file DID contain OOS + lockbox rows ...
    assert res["base_event"]["development_bars"] == n_dev                                         # ... and exactly the development rows were used
    assert res["base_event"]["rows_removed_before_research"] == 0                                 # (the CLI loader never materialised the rest)
    assert pd.Timestamp(res["base_event"]["last_bar"]) < pd.Timestamp(PARTS["development_end"], tz="UTC")
    assert not list((golden["ws"] / "experiments/EXP_0001/results").glob("oos_*")) and not (golden["ws"] / "experiments/EXP_0001/results/OOS_REPORT.json").exists()
    man = json.loads((golden["ws"] / "experiments/EXP_0001/FROZEN_MANIFEST.json").read_text())
    assert man["partitions"] == PARTS and man["partitions_hash"]


def test_rerun_of_revealed_experiment_is_refused(golden):
    p = cli("scripts/run_experiment.py", "--experiment", "EXP_0001", "--data", golden["data"], "--workspace", golden["ws"], check=False)
    assert p.returncode != 0 and "already revealed" in (p.stderr + p.stdout)


def test_run_campaign_oos_refuses_without_a_human_approval_and_spends_nothing(golden):
    p = cli("scripts/run_campaign_oos.py", "--campaign", "C001", "--data", golden["data"], "--workspace", golden["ws"], check=False)
    assert p.returncode != 0 and "frozen" in (p.stderr + p.stdout).lower()
    ws = reg.Workspace(golden["ws"])
    assert len(reg.read_oos_access(ws)) == 0 and not list(Path(golden["ws"], "approvals").glob("*.yaml"))
    c = cli("scripts/run_cpcv.py", "--experiment", "EXP_0001", "--data", golden["data"], "--workspace", golden["ws"], check=False)
    assert c.returncode != 0 and len(reg.read_oos_access(ws)) == 0


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


# ============================ a planted bar-level edge: candidate + sensitivity + human gate + OOS + CPCV ====================
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
    for target in ("DIR_RETURN_15", "DIR_RETURN_30"):
        assert (t[t["target"] == target]["decision"] == "IS_PROVISIONAL_CANDIDATE").all(), target
    assert (t[t["target"] == "DIR_RETURN_60"]["decision"] == "REJECTED_INSUFFICIENT_UPLIFT").all()     # std uplift 0.06-0.09 < 0.10 floor
    for c in ("standardized_uplift", "selected_frequency", "selected_effect", "bootstrap_ci_low", "experiment_q", "campaign_q",
              "experiment_bonferroni_p", "campaign_bonferroni_p"):
        cand = cand.assign(**{c: pd.to_numeric(cand[c])})
    assert (cand["standardized_uplift"] >= 0.10).all() and (cand["selected_frequency"] >= 1.0).all()
    assert (cand["selected_effect"] > 0).all() and (cand["bootstrap_ci_low"] > 0).all()
    assert (cand[["experiment_q", "campaign_q", "experiment_bonferroni_p", "campaign_bonferroni_p"]] <= 0.05).all().all()
    rejected = t[~t["decision"].isin(["IS_PROVISIONAL_CANDIDATE", "IS_SHORTLIST_ELIGIBLE"])]
    assert len(rejected) > 0 and (rejected["decision"] != "PENDING").all()                    # rejected trials remain visible


def test_candidate_without_strong_verification_is_provisional_and_cannot_be_approved(planted):
    ws, exp = planted["ws"], planted["exp"]
    assert reg.experiment_row(ws, exp)["status"] == "IS_PROVISIONAL_CANDIDATE" and reg.experiment_row(ws, exp)["research_verification"] == "NOT_RUN"
    j = json.loads((experiment_dir(ws, exp) / "results/IS_REPORT.json").read_text())
    assert j["I_top_configurations"]["top_groups"] == []                                      # only shortlist-ELIGIBLE (verified) trials are ranked
    copy = planted["ws_dir"].parent / "unverified_copy"
    shutil.copytree(planted["ws_dir"], copy)
    cws = reg.Workspace(copy)
    groups = ["DIR_RETURN_15|UPPER_HALF"]
    human_approval(cws, exp, groups)                                                          # a human could write this file ...
    with pytest.raises(ApprovalError):
        validate_approval(cws, exp)                                                           # ... but it is not valid without verification
    assert len(reg.read_oos_access(cws)) == 0


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


def test_the_planted_run_never_touched_oos_or_the_lockbox(planted):
    ws, exp = planted["ws"], planted["exp"]
    assert len(reg.read_oos_access(ws)) == 0 and not list(Path(planted["ws_dir"], "approvals").glob("*.yaml"))
    assert pd.Timestamp(planted["results"]["base_event"]["last_bar"]) < pd.Timestamp(PARTS["development_end"], tz="UTC")
    assert "OOS status = NOT ACCESSED" in (experiment_dir(ws, exp) / "results/IS_REPORT.md").read_text()


def test_path_diagnostics_are_non_promotable_content_cannot_move_ranking_but_tampering_breaks_approval_integrity(planted, tmp_path):
    """PATH DIAGNOSTICS ARE NON-PROMOTABLE: drastically rewriting PATH_DIAGNOSTICS.json (and legitimately regenerating the report)
    leaves candidate status, trial/group ranking, the top-5 list, approval eligibility and OOS group order untouched, while the
    hash-bound approval of the earlier report is invalidated."""
    from engine.acceptance import rank_groups, rank_trials
    from engine.is_report import write_is_report
    from engine.oos_stage import ApprovalError, approval_hashes, freeze_campaign_oos, validate_approval
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
    before = formal()
    assert before["status"][0] == "AWAITING_HUMAN_OOS_APPROVAL" and len(before["top5"]["top_groups"]) >= 2
    order = top_group_ids(ws, exp)[:2][::-1]                                                   # the human picks 2 eligible groups, in his own order
    human_approval(ws, exp, order)
    old_report_hash = approval_hashes(ws, exp)["is_report_sha256"]
    assert validate_approval(ws, exp)["approved_target_side_groups"] == order

    # (a) raw tampering of the frozen diagnostic artifact (no regeneration) invalidates the hash-bound approval
    d = experiment_dir(ws, exp) / "results"
    original = (d / "PATH_DIAGNOSTICS.json").read_text()
    (d / "PATH_DIAGNOSTICS.json").write_text(original.replace("\"promotion_eligible\":false", "\"promotion_eligible\":true", 1))
    with pytest.raises(ApprovalError, match="PATH_DIAGNOSTICS.json changed"):
        validate_approval(ws, exp)
    (d / "PATH_DIAGNOSTICS.json").write_text(original)
    assert validate_approval(ws, exp)["approved_target_side_groups"] == order

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
    new_hash = approval_hashes(ws, exp)["is_report_sha256"]
    assert new_hash != old_report_hash                                                         # but the artifact hash moved ...
    with pytest.raises(ApprovalError, match="is_report_sha256 does not match"):
        validate_approval(ws, exp)                                                             # ... so the OLD approval is no longer valid
    human_approval(ws, exp, order)                                                             # a NEW human approval over the new hashes accepts the SAME groups
    assert validate_approval(ws, exp)["approved_target_side_groups"] == order
    with pytest.raises(ApprovalError, match="not in the frozen IS shortlist"):                 # an attractive-looking non-eligible group is refused
        human_approval(ws, exp, ["DIR_RETURN_60|UPPER_HALF"])
        validate_approval(ws, exp)
    human_approval(ws, exp, order)
    doc = freeze_campaign_oos(ws, "C001")
    assert doc["experiments"][0]["approved_target_side_groups"] == order and doc["n_oos_confirmations"] == 6   # OOS group order = the human's order of eligible groups


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


# ---------------- bar-level human gate -> one-shot OOS -> CPCV (test code plays the human) ----------------
def approve_and_spend_oos(planted, name, data):
    ws_dir = planted["ws_dir"].parent / name
    shutil.copytree(planted["ws_dir"], ws_dir)
    ws = reg.Workspace(ws_dir)
    exp = planted["exp"]
    row = prepare_for_approval(ws, exp)                       # TEST-ONLY injection of strong verification of all 12 paths
    assert row["status"] == "AWAITING_HUMAN_OOS_APPROVAL"
    groups = top_group_ids(ws, exp)[:1]
    human_approval(ws, exp, groups)                           # TEST CODE PLAYING THE HUMAN
    cli("scripts/freeze_campaign_oos.py", "--campaign", "C001", "--workspace", ws_dir)          # closes the campaign (human-run step)
    campaign_open_approval(ws, "C001")                        # TEST CODE PLAYING THE HUMAN (second, campaign-level approval)
    run = cli("scripts/run_campaign_oos.py", "--campaign", "C001", "--data", data, "--workspace", ws_dir)
    return {"ws_dir": ws_dir, "ws": ws, "exp": exp, "groups": groups, "stdout": run.stdout, "data": data}


@pytest.fixture(scope="module")
def after_oos(planted):
    return approve_and_spend_oos(planted, "ws_oos", planted["data"])


@pytest.fixture(scope="module")
def after_oos_poisoned_lockbox(planted):
    """Same approval, same experiment - but every row at/after oos_end (gap + final lockbox) is wrecked in the data file."""
    import numpy as np
    df = pd.read_parquet(planted["data"])
    ts = pd.to_datetime(df["timestamp"], utc=True)
    late = (ts >= pd.Timestamp(PARTS["oos_end"], tz="UTC")).to_numpy()
    assert late.sum() > 10_000
    rng = np.random.default_rng(99)
    df.loc[late, ["open", "high", "low", "close"]] = rng.uniform(1, 1e6, size=(int(late.sum()), 4))
    df.loc[late, "volume"] = -5.0
    df.iloc[-50:, df.columns.get_loc("close")] = np.nan
    bad = planted["ws_dir"].parent / "NQ_poisoned.parquet"
    df.to_parquet(bad)
    return approve_and_spend_oos(planted, "ws_oos_poisoned", bad)


def test_after_human_approval_the_bar_level_oos_runs_exactly_once(after_oos):
    ws, exp = after_oos["ws"], after_oos["exp"]
    assert "OOS is now SPENT" in after_oos["stdout"] and "family of 3" in after_oos["stdout"]
    ledger = reg.read_oos_access(ws)
    assert len(ledger) == 1 and ledger["campaign_id"].iloc[0] == "C001" and ledger["experiments"].iloc[0] == exp and reg.verify_oos_ledger(ws) == 1
    rep = json.loads((experiment_dir(ws, exp) / "results/OOS_REPORT.json").read_text())
    assert rep["status"] == reg.experiment_row(ws, exp)["status"] == "OOS_CONFIRMED"           # the planted momentum persists in the OOS period
    oos_rows = reg.read_oos_trials(ws)
    assert len(oos_rows) == 3 * len(after_oos["groups"]) and set(oos_rows["model"]) == {"RIDGE", "SPLINE", "XGB"}   # an approved group runs all 3 models
    assert rep["family_size_for_multiple_testing"] == 3 and rep["oos_period"] == [PARTS["development_end"], PARTS["oos_end"]]


def test_second_oos_unlock_and_is_report_regeneration_are_refused_afterwards(after_oos):
    from engine.is_report import NOT_ACCESSED, oos_status_label
    ws, exp = after_oos["ws"], after_oos["exp"]
    p = cli("scripts/run_campaign_oos.py", "--campaign", "C001", "--data", after_oos["data"], "--workspace", after_oos["ws_dir"], check=False)
    assert p.returncode != 0 and "SPENT" in (p.stderr + p.stdout) and len(reg.read_oos_access(ws)) == 1
    m = cli("scripts/make_report.py", "--experiment", exp, "--workspace", after_oos["ws_dir"], check=False)
    assert m.returncode != 0 and "OOS SPENT" in (m.stderr + m.stdout)                          # 'NOT ACCESSED' can no longer be printed
    label = oos_status_label(ws, exp)
    assert label != NOT_ACCESSED and label.startswith("OOS SPENT")


def test_poisoned_lockbox_rows_cannot_change_a_single_oos_result(after_oos, after_oos_poisoned_lockbox):
    exp = after_oos["exp"]
    a = json.loads((experiment_dir(after_oos["ws"], exp) / "results/OOS_REPORT.json").read_text())
    b = json.loads((experiment_dir(after_oos_poisoned_lockbox["ws"], exp) / "results/OOS_REPORT.json").read_text())
    assert a["status"] == b["status"] and a["oos_bars_fingerprint"] == b["oos_bars_fingerprint"]
    assert a["confirmations"] == b["confirmations"] and a["group_verdicts"] == b["group_verdicts"]    # every OOS statistic is identical
    assert pd.Timestamp(a["oos_period"][1]) <= pd.Timestamp(PARTS["lockbox_start"])


def test_bar_level_cpcv_runs_only_after_oos_confirmation_and_only_vetoes(after_oos):
    ws, exp = after_oos["ws"], after_oos["exp"]
    cli("scripts/run_cpcv.py", "--experiment", exp, "--data", after_oos["data"], "--workspace", after_oos["ws_dir"])
    rep = json.loads((experiment_dir(ws, exp) / "results/CPCV_REPORT.json").read_text())
    cp = reg.read_cpcv(ws)
    assert len(cp) == 3 and set(cp["model"]) == {"RIDGE", "SPLINE", "XGB"}
    assert rep["n_splits"] == 15 and all(int(v["n_valid_splits"]) == 15 for v in rep["summary"].values())
    assert reg.experiment_row(ws, exp)["status"] in ("AWAITING_FINAL_LOCKBOX", "CPCV_REJECTED")
    status = reg.experiment_row(ws, exp)["status"]
    assert (status == "AWAITING_FINAL_LOCKBOX") == bool(rep["cpcv_confirmed_groups"])
    p = cli("scripts/confirm_lockbox.py", check=False)
    assert p.returncode != 0 and "not implemented" in (p.stderr + p.stdout)                    # the lockbox stays sealed (stub)
