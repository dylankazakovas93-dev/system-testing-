import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from engine import trial_registry as reg
from engine.common import CODE_ROOT, EngineError, load_frozen, sha256_file
from engine.verifier_bridge import (ADAPTER_SOURCE, RESEARCH_FAMILIES, classify, overall_label, parse_verifier_output,
                                    run_verification, stage_verification_dir, verifier_command)
from tests.scenario_helpers import new_frozen_experiment

F = load_frozen()

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
    cmd = verifier_command(Path("/v"), Path("/stage"), "/d/NQ.parquet", target="DIR_RETURN_60", horizon_bars=60,
                           lockbox_start="2025-01-01", mode="strong", bar_interval="1min", timestamp_col="timestamp",
                           report_prefix=Path("/r/x"))
    assert cmd[1].endswith("scripts/verify_research.py")
    flags = dict(zip(cmd[2::2], cmd[3::2]))
    assert flags["--bar-interval"] == "1min" and flags["--target"] == "DIR_RETURN_60"
    assert flags["--target-horizon"] == "60bars" and flags["--lockbox-start"] == "2025-01-01" and flags["--mode"] == "strong"
    assert flags["--adapter"] == "/stage/adapter.py" and flags["--data"] == "/d/NQ.parquet" and flags["--seed"] == "1729"


def test_missing_verifier_script_is_reported_not_faked(tmp_path):
    ws = reg.Workspace(tmp_path / "w").init()
    exp = new_frozen_experiment(ws)
    empty = tmp_path / "engine-verification-"
    (empty / "scripts").mkdir(parents=True)
    with pytest.raises(EngineError, match="verify_research.py not found"):
        run_verification(ws, exp, empty, "x.parquet")


def test_stage_is_a_hash_verified_self_contained_copy_and_adapter_compiles(tmp_path):
    ws = reg.Workspace(tmp_path / "w").init()
    exp = new_frozen_experiment(ws)
    stage = stage_verification_dir(ws, exp)
    man = json.loads((ws.experiments / exp / "FROZEN_MANIFEST.json").read_text())
    assert sha256_file(stage / "event.py") == man["hashes"]["event_py"]
    assert sha256_file(stage / "EVENT_SPEC.yaml") == man["hashes"]["event_spec"]
    for rel, h in man["hashes"]["frozen_files"].items():
        assert sha256_file(stage / rel) == h
    assert (stage / "engine" / "feature_engine.py").exists() and (stage / "features" / "hurst.py").exists()
    compile((stage / "adapter.py").read_text(), "adapter.py", "exec")
    # the adapter exposes the verifier contract and imports ONLY from its own staged copy
    code = ("import importlib.util,sys;"
            f"s=importlib.util.spec_from_file_location('a',r'{stage / 'adapter.py'}');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
            "import engine;print([n for n in ('events','features','targets','fit_predict_fold') if hasattr(m,n)]);print(engine.__file__)")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=str(tmp_path))
    assert out.returncode == 0, out.stderr
    assert "['events', 'features', 'targets', 'fit_predict_fold']" in out.stdout
    assert str(stage) in out.stdout.splitlines()[-1]


def test_stage_refuses_a_mutated_experiment(tmp_path):
    from engine.experiment_lifecycle import MutationDetected
    ws = reg.Workspace(tmp_path / "w").init()
    exp = new_frozen_experiment(ws)
    ev = ws.experiments / exp / "event.py"
    os.chmod(ev, 0o644)
    ev.write_text(ev.read_text() + "\n# changed\n")
    with pytest.raises(MutationDetected):
        stage_verification_dir(ws, exp)


def test_adapter_template_declares_the_ridge_fit_path():
    assert "FrozenModel(MODEL, FROZEN)" in ADAPTER_SOURCE and "event_time" not in ADAPTER_SOURCE.split("def fit_predict_fold")[1]


# ---- real invocation of the external verifier (skipped when the checkout is unavailable) ----------------
def _verifier_repo():
    cands = [os.environ.get("CEE_VERIFIER_REPO", ""), str(CODE_ROOT.parent / "engine-verification-"),
             str(CODE_ROOT.parent.parent / "engine-verification-"), "/home/user/dylankazakovas93-dev/engine-verification-"]
    for c in cands:
        if c and (Path(c) / "scripts" / "verify_research.py").exists():
            return Path(c)
    return None


@pytest.mark.skipif(_verifier_repo() is None, reason="external verifier checkout with verify_research.py not available")
def test_real_verifier_passes_clean_engine_and_fails_injected_lookahead(tmp_path):
    from engine.synthetic import make_bars
    vr = _verifier_repo()
    bars = make_bars(n_days=820, seed=5)
    data = tmp_path / "bars.parquet"
    bars.reset_index().rename(columns={"index": "timestamp"}).to_parquet(data)
    ws = reg.Workspace(tmp_path / "w").init()
    exp = new_frozen_experiment(ws, lockbox="2019-01-01")
    summary = run_verification(ws, exp, vr, str(data), mode="fast", targets=["DIR_RETURN_15"], skip_verifier_tests=True, verbose=False)
    r = summary["results"][0]
    assert r["research_families"] == {f: "PASS" for f in RESEARCH_FAMILIES}, r["stdout_tail"]
    assert r["label"] in ("RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE", "VERIFIED")
    assert r["label"] != "VERIFIED" or r["exit_code"] == 0
    assert reg.experiment_row(ws, exp)["research_verification"] == summary["overall"]
    # negative control: a one-bar feature lookahead in the staged copy must FAIL research_causality
    stage = stage_verification_dir(ws, exp)
    p = stage / "features" / "returns.py"
    p.write_text(p.read_text().replace("closes = gather(ctx.close, pos, L + 1)",
                                       "closes = gather(ctx.close, np.minimum(pos + 1, len(ctx.close) - 1), L + 1)"))
    cmd = verifier_command(vr, stage, str(data), target="DIR_RETURN_15", horizon_bars=15, lockbox_start="2019-01-01",
                           mode="fast", bar_interval="1min", timestamp_col="timestamp", report_prefix=tmp_path / "leak",
                           skip_tests=True)
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(vr))
    res = classify(proc.returncode, parse_verifier_output(proc.stdout))
    assert res["label"] == "FAILED" and res["research_families"]["research_causality"] == "FAIL"
    assert res["research_results_valid"] is False
