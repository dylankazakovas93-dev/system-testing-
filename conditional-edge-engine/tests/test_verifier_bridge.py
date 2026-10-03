import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from engine import trial_registry as reg
from engine import verifier_bridge as vb
from engine.common import CODE_ROOT, EngineError, load_frozen, load_yaml, sha256_file
from engine.verifier_bridge import (ADAPTER_SOURCE, RESEARCH_FAMILIES, check_verifier_pin, classify, overall_label,
                                    parse_verifier_output, run_verification, stage_verification_dir, verifier_command, verifier_pin)
from tests.scenario_helpers import PARTS, fake_results, new_frozen_experiment

F = load_frozen()
MODELS = ["RIDGE", "SPLINE", "XGB"]

OUT_OK = """[UNVERIFIED] contract_provenance (mandatory)
[PASS      ] data_audit (mandatory)
[PASS      ] lockbox (mandatory)
[PASS      ] ml_leakage (mandatory)
[PASS      ] ml_static_scan (mandatory)
[UNVERIFIED] repository_health (mandatory)
[PASS      ] research_causality (mandatory)
[PASS      ] research_contract (mandatory)
[PASS      ] walkforward (mandatory)
VERDICT: INCOMPLETE / UNVERIFIED
"""


def test_parse_and_classify_exit_code_2_is_never_a_pass():
    parsed = parse_verifier_output(OUT_OK)
    assert parsed["verdict"] == "INCOMPLETE / UNVERIFIED" and parsed["family_status"]["walkforward"] == "PASS"
    res = classify(2, parsed)
    assert res["label"] == "RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE" and res["label"] != "VERIFIED"
    assert res["other_families"]["contract_provenance"] == "UNVERIFIED"                # reported separately
    assert res["research_results_valid"] is True
    assert classify(0, parsed)["label"] == "VERIFIED"
    assert classify(1, parsed)["label"] == "FAILED"


def test_failed_research_family_invalidates_results():
    bad = OUT_OK.replace("[PASS      ] research_causality", "[FAIL      ] research_causality")
    res = classify(1, parse_verifier_output(bad))
    assert res["label"] == "FAILED" and res["research_results_valid"] is False
    res2 = classify(2, parse_verifier_output(OUT_OK.replace("[PASS      ] ml_leakage", "[UNVERIFIED] ml_leakage")))
    assert res2["label"] == "INCOMPLETE" and res2["research_results_valid"] is False
    res3 = classify(2, parse_verifier_output(OUT_OK.replace("[PASS      ] lockbox (mandatory)\n", "")))
    assert res3["label"] == "INCOMPLETE" and res3["research_families"]["lockbox"] == "MISSING"
    assert overall_label([{"label": "VERIFIED"}, {"label": "FAILED"}]) == "FAILED"
    assert overall_label([{"label": "RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE"}, {"label": "INCOMPLETE"}]) == "INCOMPLETE"
    assert overall_label([{"label": "RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE"}] * 2) == "RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE"


def test_command_contains_the_required_verifier_flags():
    cmd = verifier_command(Path("/v"), Path("/stage/adapter_XGB.py"), Path("/stage"), "/d/NQ.parquet", target="DIR_RETURN_60", horizon_bars=60,
                           lockbox_start="2025-01-01", mode="strong", bar_interval="1min", timestamp_col="timestamp",
                           report_prefix=Path("/r/x"))
    assert cmd[1].endswith("scripts/verify_research.py")
    flags = dict(zip(cmd[2::2], cmd[3::2]))
    assert flags["--bar-interval"] == "1min" and flags["--target"] == "DIR_RETURN_60"
    assert flags["--target-horizon"] == "60bars" and flags["--lockbox-start"] == "2025-01-01" and flags["--mode"] == "strong"
    assert flags["--adapter"] == "/stage/adapter_XGB.py" and flags["--data"] == "/d/NQ.parquet" and flags["--seed"] == "1729"


def test_verifier_is_pinned_to_an_exact_commit_not_main(tmp_path):
    pin = verifier_pin()
    assert len(pin["commit"]) == 40 and pin["required_models"] == MODELS and pin["required_mode"] == "strong"
    repo = tmp_path / "engine-verification-"
    (repo / "scripts").mkdir(parents=True)
    (repo / "scripts" / "verify_research.py").write_text("print('fake')\n")
    run = lambda *a: subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, check=True)  # noqa: E731
    run("init", "-q"); run("config", "user.email", "t@t"); run("config", "user.name", "t"); run("add", "-A"); run("commit", "-qm", "x")
    with pytest.raises(EngineError, match="pins"):
        check_verifier_pin(repo)                                      # an arbitrary commit/main is refused
    ws = reg.Workspace(tmp_path / "w").init()
    exp = new_frozen_experiment(ws)
    with pytest.raises(EngineError, match="pins"):
        run_verification(ws, exp, repo, "x.parquet")                  # run_verification enforces it before anything else
    real = _verifier_repo()
    if real is not None:
        assert check_verifier_pin(real) == pin["commit"]
        (real / "UNTRACKED_TEST_FILE").write_text("x")
        try:
            with pytest.raises(EngineError, match="local modifications"):
                check_verifier_pin(real)
        finally:
            (real / "UNTRACKED_TEST_FILE").unlink()


def test_missing_verifier_script_is_reported_not_faked(tmp_path):
    ws = reg.Workspace(tmp_path / "w").init()
    exp = new_frozen_experiment(ws)
    empty = tmp_path / "engine-verification-"
    (empty / "scripts").mkdir(parents=True)
    with pytest.raises(EngineError, match="verify_research.py not found"):
        run_verification(ws, exp, empty, "x.parquet")


def test_stage_writes_one_hash_verified_adapter_per_frozen_model(tmp_path):
    ws = reg.Workspace(tmp_path / "w").init()
    exp = new_frozen_experiment(ws)
    stage = stage_verification_dir(ws, exp)
    man = json.loads((ws.experiments / exp / "FROZEN_MANIFEST.json").read_text())
    assert sha256_file(stage / "event.py") == man["hashes"]["event_py"]
    for rel, h in man["hashes"]["frozen_files"].items():
        assert sha256_file(stage / rel) == h
    assert (stage / "engine" / "feature_engine.py").exists() and (stage / "features" / "hurst.py").exists()
    for m in MODELS:
        src = (stage / f"adapter_{m}.py").read_text()
        compile(src, f"adapter_{m}.py", "exec")
        assert f'MODEL = "{m}"' in src
    # each adapter exposes the verifier contract, binds its own model and imports ONLY from its staged copy
    for m in MODELS:
        code = ("import importlib.util;"
                f"s=importlib.util.spec_from_file_location('a',r'{stage / f'adapter_{m}.py'}');mod=importlib.util.module_from_spec(s);s.loader.exec_module(mod);"
                "import engine;print([n for n in ('events','features','targets','fit_predict_fold') if hasattr(mod,n)]);print(mod.MODEL);print(engine.__file__)")
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=str(tmp_path))
        assert out.returncode == 0, out.stderr
        lines = out.stdout.splitlines()
        assert lines[0] == "['events', 'features', 'targets', 'fit_predict_fold']" and lines[1] == m and str(stage) in lines[2]


def test_stage_refuses_a_mutated_experiment(tmp_path):
    from engine.experiment_lifecycle import MutationDetected
    ws = reg.Workspace(tmp_path / "w").init()
    exp = new_frozen_experiment(ws)
    ev = ws.experiments / exp / "event.py"
    os.chmod(ev, 0o644)
    ev.write_text(ev.read_text() + "\n# changed\n")
    with pytest.raises(MutationDetected):
        stage_verification_dir(ws, exp)


def test_adapter_template_declares_the_frozen_model_fit_path():
    assert "FrozenModel(MODEL, FROZEN)" in ADAPTER_SOURCE and "event_time" not in ADAPTER_SOURCE.split("def fit_predict_fold")[1]


def make_fake_verifier(tmp_path):
    repo = tmp_path / "engine-verification-"
    (repo / "scripts").mkdir(parents=True)
    (repo / "scripts" / "verify_research.py").write_text("# fake\n")
    return repo


def test_promotion_capable_targets_are_exactly_the_primary_targets():
    """Every primary target takes part in the 24 selection trials, so every one must be externally verified: 4 x 3 = 12 paths."""
    from engine.common import primary_target_names
    from engine.verifier_bridge import promotion_capable_targets
    verification_targets = promotion_capable_targets(F)
    trial_targets = {s["target"] for s in reg.trial_specs(F)}                                  # targets that can reach IS_SHORTLIST_ELIGIBLE / SELECTION HOLDOUT
    assert set(verification_targets) == set(primary_target_names(F)) == trial_targets
    assert verification_targets == ["DIR_RETURN_15", "DIR_RETURN_30", "DIR_RETURN_60", "DIR_PATH_SKEW_60"]
    assert len(verification_targets) * len(MODELS) == 12


def test_bridge_verifies_all_twelve_strong_paths_even_when_most_targets_are_rejected_at_is(tmp_path, monkeypatch):
    """Only DIR_RETURN_30 has candidate trials here, yet all 4 targets x 3 models are verified in STRONG mode: a rejected target must never
    become an unverified path later. The verifier only receives development rows."""
    from engine.common import primary_target_names
    from engine.synthetic import make_bars
    ws = reg.Workspace(tmp_path / "w").init()
    exp = new_frozen_experiment(ws, partitions={"development_end": "2017-01-01", "selection_holdout_end": "2018-01-01", "lockbox_start": "2018-01-01"})
    reg.reveal_experiment(ws, exp, fake_results(ws, exp, {("DIR_RETURN_30", m): 0.0009 for m in MODELS}),
                          train_period="a", validation_period="b", frozen=F)
    t = reg.experiment_trials(ws, exp)
    assert set(t[t["decision"].isin(["IS_PROVISIONAL_CANDIDATE", "IS_SHORTLIST_ELIGIBLE"])]["target"]) == {"DIR_RETURN_30"}
    bars = make_bars(n_days=600, seed=2)
    data = tmp_path / "bars.parquet"
    bars.reset_index().rename(columns={"index": "timestamp"}).to_parquet(data)
    repo = make_fake_verifier(tmp_path)
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        return SimpleNamespace(returncode=2, stdout=OUT_OK, stderr="")

    monkeypatch.setattr(vb, "check_verifier_pin", lambda r: verifier_pin()["commit"])
    monkeypatch.setattr(vb.subprocess, "run", fake_run)
    summary = run_verification(ws, exp, repo, str(data), verbose=False)
    assert len(calls) == 12
    flags = [{c[i]: c[i + 1] for i in range(2, len(c) - 1) if c[i].startswith("--")} for c in calls]
    adapters = [Path(dict(zip(c[2::2], c[3::2]))["--adapter"]).name for c in calls]
    assert set(summary["targets_verified"]) == set(primary_target_names(F)) and summary["models_verified"] == MODELS
    assert {(f["--target"], a) for f, a in zip(flags, adapters)} == {(tg, f"adapter_{m}.py") for tg in primary_target_names(F) for m in MODELS}
    horizons = {x["name"]: x["horizon_bars"] for x in F.target_bank["primary_targets"]}
    for f in flags:
        assert f["--mode"] == "strong" and f["--target-horizon"] == f"{horizons[f['--target']]}bars" and f["--bar-interval"] == "1min"
        assert f["--lockbox-start"] == summary["verifier_holdout_start"]                          # a holdout INSIDE the staged development span
        assert pd.Timestamp("2016-01-04") < pd.Timestamp(f["--lockbox-start"]) < pd.Timestamp("2017-01-01")
    assert len(summary["warnings"]) == 1 and "INCOMPLETE" in summary["warnings"][0]               # 1 UTC calendar year before the holdout
    assert "--skip-tests" not in calls[0] and all("--skip-tests" in c for c in calls[1:])          # repository_health once
    stage_data = pd.read_parquet(Path(dict(zip(calls[0][2::2], calls[0][3::2]))["--data"]))
    assert pd.to_datetime(stage_data["timestamp"], utc=True).max() < pd.Timestamp("2017-01-01", tz="UTC")   # no SELECTION HOLDOUT/lockbox row reaches it
    assert summary["overall"] == "RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE"
    rec = json.loads(reg.experiment_row(ws, exp)["verification_json"])
    assert set(rec) == {f"{tg}|{m}" for tg in primary_target_names(F) for m in MODELS} and len(rec) == 12 and all(v["mode"] == "strong" for v in rec.values())
    assert reg.experiment_row(ws, exp)["research_verification"] == "RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE"


def test_partial_target_verification_is_flagged_and_unknown_targets_are_refused(tmp_path, monkeypatch):
    from engine.synthetic import make_bars
    ws = reg.Workspace(tmp_path / "w").init()
    exp = new_frozen_experiment(ws, partitions={"development_end": "2017-01-01", "selection_holdout_end": "2018-01-01", "lockbox_start": "2018-01-01"})
    data = tmp_path / "bars.parquet"
    make_bars(n_days=400, seed=2).reset_index().rename(columns={"index": "timestamp"}).to_parquet(data)
    repo = make_fake_verifier(tmp_path)
    monkeypatch.setattr(vb, "check_verifier_pin", lambda r: verifier_pin()["commit"])
    monkeypatch.setattr(vb.subprocess, "run", lambda cmd, **kw: SimpleNamespace(returncode=2, stdout=OUT_OK, stderr=""))
    s = run_verification(ws, exp, repo, str(data), targets=["DIR_RETURN_15"], verbose=False, record=False)
    assert any("PARTIAL VERIFICATION" in w and "DIR_RETURN_60" in w and "DIR_PATH_SKEW_60" in w for w in s["warnings"])
    with pytest.raises(EngineError, match="unknown primary targets"):
        run_verification(ws, exp, repo, str(data), targets=["DIR_RETURN_999"], verbose=False, record=False)


def test_a_research_family_failure_rejects_that_model_path(tmp_path, monkeypatch):
    from engine.synthetic import make_bars
    ws = reg.Workspace(tmp_path / "w").init()
    exp = new_frozen_experiment(ws, partitions={"development_end": "2017-01-01", "selection_holdout_end": "2018-01-01", "lockbox_start": "2018-01-01"})
    reg.reveal_experiment(ws, exp, fake_results(ws, exp, {("DIR_RETURN_30", m): 0.0009 for m in MODELS}),
                          train_period="a", validation_period="b", frozen=F)
    data = tmp_path / "bars.parquet"
    make_bars(n_days=400, seed=2).reset_index().rename(columns={"index": "timestamp"}).to_parquet(data)
    repo = make_fake_verifier(tmp_path)

    def fake_run(cmd, **kw):
        xgb = "adapter_XGB.py" in " ".join(cmd)
        out = OUT_OK.replace("[PASS      ] research_causality", "[FAIL      ] research_causality") if xgb else OUT_OK
        return SimpleNamespace(returncode=1 if xgb else 2, stdout=out, stderr="")

    monkeypatch.setattr(vb, "check_verifier_pin", lambda r: verifier_pin()["commit"])
    monkeypatch.setattr(vb.subprocess, "run", fake_run)
    s = run_verification(ws, exp, repo, str(data), verbose=False)
    assert s["overall"] == "FAILED"
    t = reg.experiment_trials(ws, exp)
    up = t[(t["target"] == "DIR_RETURN_30") & (t["state"] == "UPPER_HALF")].set_index("model")
    assert up.at["XGB", "decision"] == "REJECTED_VERIFICATION"                                   # that model path is rejected
    assert up.at["RIDGE", "decision"] in ("IS_PROVISIONAL_CANDIDATE", "IS_SHORTLIST_ELIGIBLE")    # the other two keep their standing


def test_stage_holdout_start_is_a_deterministic_frozen_rule_inside_the_staged_span():
    from engine.verifier_bridge import stage_holdout_start
    pin = {"stage_holdout_fraction": 0.10, "stage_holdout_min_days": 14}
    first, cut = pd.Timestamp("2016-01-04 14:30", tz="UTC"), pd.Timestamp("2019-01-01", tz="UTC")
    a = stage_holdout_start(first, cut, pin)
    assert a == stage_holdout_start(first, cut, pin) == "2018-09-13"               # span 1093.4 days x 0.10 = 109.3 days before the cutoff, floored to a day
    assert pd.Timestamp(a, tz="UTC") < cut and pd.Timestamp(a, tz="UTC") > first
    assert stage_holdout_start(first, pd.Timestamp("2016-03-04", tz="UTC"), pin) == "2016-02-19"     # 60-day span: the 14-day minimum applies
    with pytest.raises(EngineError, match="too short"):
        stage_holdout_start(first, pd.Timestamp("2016-01-10", tz="UTC"), pin)
    assert verifier_pin()["stage_holdout_fraction"] == 0.10 and verifier_pin()["stage_holdout_min_days"] == 14


def test_calendar_years_before_the_holdout_counts_utc_years_of_staged_bars():
    from engine.verifier_bridge import calendar_years_before
    idx = pd.date_range("2016-12-30", "2018-03-01", freq="1D", tz="UTC")
    assert calendar_years_before(idx, "2018-01-01") == [2016, 2017]
    assert calendar_years_before(idx, "2018-02-01") == [2016, 2017, 2018]
    assert calendar_years_before(idx, "2016-12-31") == [2016]


# ---- real invocation of the external verifier (skipped when the pinned checkout is unavailable) -----------------
def _verifier_repo():
    cands = [os.environ.get("CEE_VERIFIER_REPO", ""), str(CODE_ROOT.parent / "engine-verification-"),
             str(CODE_ROOT.parent.parent / "engine-verification-"), "/home/user/dylankazakovas93-dev/engine-verification-"]
    for c in cands:
        if c and (Path(c) / "scripts" / "verify_research.py").exists():
            return Path(c)
    return None


@pytest.mark.skipif(_verifier_repo() is None, reason="pinned external verifier checkout not available")
def test_real_verifier_passes_all_three_model_paths_and_fails_injected_lookahead(tmp_path):
    from engine.synthetic import make_bars
    vr = _verifier_repo()
    bars = make_bars(n_days=820, seed=5)
    data = tmp_path / "bars.parquet"
    bars.reset_index().rename(columns={"index": "timestamp"}).to_parquet(data)
    ws = reg.Workspace(tmp_path / "w").init()
    exp = new_frozen_experiment(ws, partitions={"development_end": "2019-01-01", "selection_holdout_end": "2020-01-01", "lockbox_start": "2020-01-01"})
    summary = run_verification(ws, exp, vr, str(data), mode="fast", targets=["DIR_RETURN_15"], skip_verifier_tests=True,
                               record=False, verbose=False)
    assert [(r["target"], r["model"]) for r in summary["results"]] == [("DIR_RETURN_15", m) for m in MODELS]
    for r in summary["results"]:
        assert r["research_families"] == {f: "PASS" for f in RESEARCH_FAMILIES}, (r["model"], r["stdout_tail"])
        assert r["label"] in ("RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE", "VERIFIED")
        assert r["label"] != "VERIFIED" or r["exit_code"] == 0
    assert summary["verifier_commit"] == verifier_pin()["commit"]
    # negative control: a one-bar feature lookahead in the staged copy must FAIL research_causality
    stage = stage_verification_dir(ws, exp)
    p = stage / "features" / "returns.py"
    p.write_text(p.read_text().replace("closes = gather(ctx.close, pos, L + 1)",
                                       "closes = gather(ctx.close, np.minimum(pos + 1, len(ctx.close) - 1), L + 1)"))
    stage_data = ws.experiments / exp / "verification" / "data_IS.parquet"
    cmd = verifier_command(vr, stage / "adapter_RIDGE.py", stage, str(stage_data), target="DIR_RETURN_15", horizon_bars=15,
                           lockbox_start=summary["verifier_holdout_start"], mode="fast", bar_interval="1min", timestamp_col="timestamp",
                           report_prefix=tmp_path / "leak", skip_tests=True)
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(vr))
    res = classify(proc.returncode, parse_verifier_output(proc.stdout))
    assert res["label"] == "FAILED" and res["research_families"]["research_causality"] == "FAIL" and res["research_results_valid"] is False
