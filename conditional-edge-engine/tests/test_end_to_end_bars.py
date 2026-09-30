"""Bar-level end-to-end runs (synthetic 1-minute NQ-like bars through the REAL pipeline)."""
import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pandas as pd
import pytest

from engine import trial_registry as reg
from engine.common import CODE_ROOT, load_frozen
from engine.experiment_lifecycle import MutationDetected, create_experiment, experiment_dir, freeze, verify_manifest
from engine.experiment_runner import run_experiment
from engine.synthetic import make_bars

F = load_frozen()
REPORT_SECTIONS = ["BASE EVENT", "PROMOTED DEVELOPMENT CANDIDATES", "REJECTED — LOW FREQUENCY",
                   "REJECTED — INSUFFICIENT UPLIFT", "REJECTED — STATISTICAL", "REJECTED — INSTABILITY",
                   "REJECTED — SENSITIVITY", "DIAGNOSTIC / NON-PROMOTABLE OBSERVATIONS", "ALL 24 SELECTION TRIALS"]


def cli(*args, check=True):
    p = subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, cwd=str(CODE_ROOT))
    if check and p.returncode != 0:
        raise AssertionError(f"{args}\n{p.stdout}\n{p.stderr}")
    return p


# ============================ 11. TradingView template, driven entirely through the CLI ====================
@pytest.fixture(scope="module")
def golden(tmp_path_factory):
    base = tmp_path_factory.mktemp("golden")
    data = base / "NQ_synth.parquet"
    make_bars(1100, seed=7).reset_index().rename(columns={"index": "timestamp"}).to_parquet(data)
    ws = base / "ws"
    cli("scripts/new_experiment.py", "--new-campaign", "C001", "--lockbox-start", "2020-01-01", "--workspace", ws)
    spec = ws / "experiments/EXP_0001/EVENT_SPEC.yaml"
    spec.write_text(spec.read_text().replace("TODO: one or two sentences.", "A confirmed pivot is followed by a path."))
    cli("scripts/freeze_experiment.py", "--experiment", "EXP_0001", "--workspace", ws)
    run = cli("scripts/run_experiment.py", "--experiment", "EXP_0001", "--data", data, "--workspace", ws)
    return {"ws": ws, "data": data, "run_stdout": run.stdout}


def test_template_experiment_report_has_every_required_section(golden):
    text = (golden["ws"] / "experiments/EXP_0001/results/REPORT.md").read_text()
    for s in REPORT_SECTIONS:
        assert f"## {s}" in text, s
    assert "These bins were not selection trials and cannot promote a candidate." in text
    assert "Using them to construct a rule requires a new registered experiment." in text
    assert "DIAGNOSTIC — NOT ELIGIBLE FOR PROMOTION" in text
    assert "selection opportunities used by this experiment: 24 of 24" in text
    assert text.count("EXP_0001_T") >= 24 and "EXP_0001_T24" in text
    assert "score deciles" in text.lower() and "Year-by-year mean target by decile" in text


def test_template_experiment_registry_and_lockbox(golden):
    ws = reg.Workspace(golden["ws"])
    assert reg.integrity_check(ws) == {"experiments": 1, "selection_trials": 24, "revealed_trials": 24,
                                       "observations": len(reg.read_observations(ws))}
    t = reg.experiment_trials(ws, "EXP_0001")
    assert len(t) == 24 and (t["status"] == "REVEALED").all() and t["campaign_q"].notna().all()
    res = json.loads((golden["ws"] / "experiments/EXP_0001/results/results.json").read_text())
    assert res["base_event"]["lockbox_withheld_bars"] > 0 and res["base_event"]["flag"] == ""
    assert res["oos_period"].endswith("2019-12-31") and res["lockbox_start"] == "2020-01-01"
    for f in (golden["ws"] / "experiments/EXP_0001/results").glob("oos_*.csv"):
        df = pd.read_csv(f, parse_dates=["event_time"])
        assert (df["event_time"] < pd.Timestamp("2020-01-01", tz="UTC")).all(), f        # nothing from the lockbox
    assert res["sensitivity"]["status"] == "NO_DEVELOPMENT_CANDIDATE"                    # sensitivity cannot create one
    assert len(t) == 24 and not t["decision"].isin(["PROMOTABLE", "PROMOTABLE_PENDING_SENSITIVITY"]).any()


def test_rerun_of_revealed_experiment_is_refused(golden):
    p = cli("scripts/run_experiment.py", "--experiment", "EXP_0001", "--data", golden["data"], "--workspace",
            golden["ws"], check=False)
    assert p.returncode != 0 and "already revealed" in (p.stderr + p.stdout)


def test_mutation_after_reveal_forces_a_new_lineage_and_never_overwrites(golden, tmp_path):
    ws_dir = tmp_path / "ws"
    shutil.copytree(golden["ws"], ws_dir)
    ws = reg.Workspace(ws_dir)
    before = reg.experiment_trials(ws, "EXP_0001").to_csv()
    ev = ws_dir / "experiments/EXP_0001/event.py"
    os.chmod(ev, 0o644)
    ev.write_text(ev.read_text().replace("pivot_left", "pivot_left  "))        # any byte change after results were revealed
    with pytest.raises(MutationDetected):
        verify_manifest(ws, "EXP_0001")
    cli("scripts/new_experiment.py", "--campaign", "C001", "--lineage-of", "EXP_0001", "--workspace", ws_dir)
    assert (ws_dir / "experiments/EXP_0002/LINEAGE.md").exists()
    assert reg.experiment_trials(ws, "EXP_0001").to_csv() == before                # the old experiment's rows are untouched
    status = cli("scripts/campaign_status.py", "--campaign", "C001", "--workspace", ws_dir).stdout
    assert "experiments used      : 2 / 20" in status and "lineage_of=EXP_0001" in status


def test_campaign_status_reports_the_opportunity_count(golden):
    out = cli("scripts/campaign_status.py", "--workspace", golden["ws"]).stdout
    assert "registry integrity" in out and "24 registered / 480 max; 24 revealed" in out
    assert "experiments used      : 1 / 20" in out


def test_cli_rejects_experiment_21(tmp_path):
    ws_dir = tmp_path / "ws"
    cli("scripts/new_experiment.py", "--new-campaign", "C001", "--lockbox-start", "2020-01-01", "--workspace", ws_dir)
    for _ in range(19):
        cli("scripts/new_experiment.py", "--campaign", "C001", "--workspace", ws_dir)
    p = cli("scripts/new_experiment.py", "--campaign", "C001", "--workspace", ws_dir, check=False)
    assert p.returncode != 0 and "MAX_EXPERIMENTS_PER_CAMPAIGN=20" in (p.stderr + p.stdout)
    p2 = cli("scripts/new_experiment.py", "--new-campaign", "C002", "--lockbox-start", "2021-01-01", "--workspace", ws_dir)
    assert "EXP_0021" in p2.stdout


# ============================ planted bar-level edge: candidate + sensitivity =========================
def custom_experiment(ws, *, mixed: bool, hypothesis: str):
    exp = create_experiment(ws, new_campaign="C001", lockbox_start="2020-01-01")
    d = experiment_dir(ws, exp)
    (d / "event.py").write_text(textwrap.dedent('''
        import numpy as np
        import pandas as pd


        def detect_events(bars, params):
            step = int(params["every_n_bars"])
            flip = int(params["direction_period"])
            interval = pd.Timedelta(bars.attrs["bar_interval"])
            position = np.arange(len(bars))
            keep = position % step == 0
            n = int(keep.sum())
            direction = np.where(np.arange(n) % flip == 0, 1, -1) if flip > 1 else np.ones(n, dtype=int)
            return pd.DataFrame({"event_time": bars.index[keep] + interval, "direction": direction})
    '''))
    (d / "EVENT_SPEC.yaml").write_text(textwrap.dedent(f'''
        experiment_id: {exp}
        campaign_id: C001
        hypothesis: "{hypothesis}"
        instrument: NQ_1m
        data_interval: 1min
        eligible_session: {{start: "09:31", end: "15:00"}}
        direction_definition: {{rule: "long unless direction_period alternates", values: [1, -1]}}
        event_condition: {{description: "every n-th bar of the supplied history", parameters_used: [every_n_bars, direction_period]}}
        deduplication_rule: keep_first_per_event_time
        cooldown: {{bars: 0}}
        base_parameters: {{every_n_bars: 45, direction_period: {2 if mixed else 1}}}
        sensitivity_parameters: [every_n_bars]
        expected_information_time: {{rule: "completion time of the n-th bar", confirmation_delay_bars: 0}}
    '''))
    freeze(ws, exp)
    return exp


@pytest.fixture(scope="module")
def planted(tmp_path_factory):
    ws = reg.Workspace(tmp_path_factory.mktemp("planted")).init()
    exp = custom_experiment(ws, mixed=False, hypothesis="Planted AR(1) momentum makes recent path informative.")
    out = run_experiment(ws, exp, make_bars(1100, seed=7, phi=0.8), verbose=False)
    return ws, exp, out


def test_planted_momentum_yields_a_development_candidate_that_survives_sensitivity(planted):
    ws, exp, out = planted
    t = out["trials"]
    for target in ("DIR_RETURN_15", "DIR_RETURN_30"):
        for state in ("UPPER_HALF", "LOWER_HALF"):
            g = t[(t["target"] == target) & (t["state"] == state)]
            assert (g["decision"] == "PROMOTABLE").all(), (target, state, g["decision"].tolist())
    assert out["sensitivity"]["status"] == "RUN"
    grp = out["sensitivity"]["groups"]["DIR_RETURN_15|UPPER_HALF"]
    assert grp["verdict"] == "PASSED" and [p["value"] for p in grp["probes"]] == [34, 56]      # 45 x 0.75, x 1.25
    assert all(p["models_frequency_ok"] >= 2 for p in grp["probes"])
    assert reg.experiment_row(ws, exp)["sensitivity_json"] != "{}"


def test_sensitivity_never_replaces_the_base_parameter(planted):
    ws, exp, out = planted
    assert verify_manifest(ws, exp)["errors"] == []                                     # spec + event untouched by probes
    import yaml
    assert yaml.safe_load((experiment_dir(ws, exp) / "EVENT_SPEC.yaml").read_text())["base_parameters"]["every_n_bars"] == 45
    from engine.event_contract import generate_events, load_event_module, load_spec
    from engine.experiment_runner import dev_bars
    d = experiment_dir(ws, exp)
    dev, _ = dev_bars(make_bars(1100, seed=7, phi=0.8), "2020-01-01")
    base_events, _ = generate_events(load_event_module(d / "event.py"), dev, load_spec(d / "EVENT_SPEC.yaml"), F)
    assert out["base_event"]["n_events"] == len(base_events)                            # results use the BASE parameter
    probe_counts = {p["n_events"] for p in out["sensitivity"]["groups"]["DIR_RETURN_15|UPPER_HALF"]["probes"]}
    assert len(base_events) not in probe_counts and len(probe_counts) == 2              # probes really ran other events
    text = Path(out["report_path"]).read_text()
    assert "DEVELOPMENT CANDIDATE" in text and "Event-parameter sensitivity (robustness only): **PASSED**" in text
    assert "never replaces the base parameter" in text


def test_planted_candidate_is_limited_to_what_clears_the_uplift_floor(planted):
    _, _, out = planted
    t = out["trials"]
    promoted = t[t["decision"] == "PROMOTABLE"]
    assert (promoted["standardized_uplift"] >= 0.10).all() and (promoted["selected_frequency"] >= 1.0).all()
    assert (promoted["experiment_q"] <= 0.05).all() and (promoted["campaign_q"] <= 0.05).all()
    rejected = t[t["decision"] != "PROMOTABLE"]
    assert len(rejected) > 0 and (rejected["decision"] != "PENDING").all()             # rejected trials remain visible


# ============================ documented limitation: mixed-direction events ============================
def test_mixed_direction_events_hide_a_planted_state_effect_documented_limitation(tmp_path):
    """Same planted structure as above, but directions alternate. The frozen feature bank has no direction input,
    so a direction-relative continuation effect cannot be learned (see RESEARCH_RULES.md, spec issue 3)."""
    ws = reg.Workspace(tmp_path).init()
    exp = custom_experiment(ws, mixed=True, hypothesis="Same planted momentum but events alternate direction.")
    out = run_experiment(ws, exp, make_bars(1100, seed=7, phi=0.8), verbose=False)
    t = out["trials"]
    assert not t["decision"].isin(["PROMOTABLE", "PROMOTABLE_PENDING_SENSITIVITY"]).any()
    assert t["standardized_uplift"].abs().max() < 0.10


def test_make_report_rebuilds_from_stored_results_and_shows_verification_status(golden, tmp_path):
    ws_dir = tmp_path / "ws"
    shutil.copytree(golden["ws"], ws_dir)
    ws = reg.Workspace(ws_dir)
    assert "verification: **NOT_RUN**" in (ws_dir / "experiments/EXP_0001/results/REPORT.md").read_text()
    reg.update_experiment(ws, "EXP_0001", research_verification="FAILED")
    cli("scripts/make_report.py", "--experiment", "EXP_0001", "--workspace", ws_dir)
    text = (ws_dir / "experiments/EXP_0001/results/REPORT.md").read_text()
    assert "external research verification: **FAILED**" in text
    for s in REPORT_SECTIONS:
        assert f"## {s}" in text
    assert reg.experiment_trials(ws, "EXP_0001").to_csv() == reg.experiment_trials(reg.Workspace(golden["ws"]), "EXP_0001").to_csv()
