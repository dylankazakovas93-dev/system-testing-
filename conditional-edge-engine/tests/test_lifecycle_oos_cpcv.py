"""IS -> human approval -> one-shot OOS -> CPCV lifecycle on table-level synthetic data with KNOWN structure.

The test code plays the HUMAN when it writes approval files (production code never does). Strong-mode verification and the
sensitivity verdict are injected via the registry (the real verifier/probes are exercised elsewhere)."""
import copy
import json
import os
import shutil
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest
import yaml

from engine import cpcv as C
from engine import trial_registry as reg
from engine.common import CODE_ROOT, EngineError, load_frozen
from engine.experiment_lifecycle import experiment_dir, verify_manifest
from engine.is_report import NOT_ACCESSED, ReportSealedError, oos_status_label, write_is_report
from engine.oos_stage import (ApprovalError, OOSContaminated, freeze_campaign_oos, approval_hashes, approval_path, group_verdicts, mark_contamination_if_mutated,
                              oos_confirmations, validate_approval)
from engine.multiplicity import benjamini_hochberg
from tests.scenario_helpers import (LIFE_PARTS, human_approval, lifecycle_workspace, run_cpcv_stage, slice_tables, spend_oos, top_group_ids)

F = load_frozen()
STABLE = dict(signal="linear", slope=0.35)
CURVEFIT = dict(signal="linear", slope=0.0, slope_by_year={**{y: 0.6 for y in range(2015, 2020)}, **{y: -0.3 for y in range(2020, 2023)}})
# one bad year (2019) inside development: IS tolerates it (4/5 years, 4/5 folds), but every CPCV split that holds the 2019 group out nets negative -> 10/15 < 12/15
UNSTABLE_CPCV = dict(signal="linear", slope=0.0, slope_by_year={**{y: 1.0 for y in (2015, 2016, 2017, 2018, 2020, 2021, 2022)}, 2019: -1.6})


def clone(ws, tmp_path, name="copy"):
    dst = tmp_path / name
    shutil.copytree(ws.root, dst)
    return reg.Workspace(dst)


# ===================================================== stable effect: IS -> OOS -> CPCV ==========================================
class TestStableEffect:
    @pytest.fixture(scope="class")
    def life(self, tmp_path_factory):
        ws, exp, tables = lifecycle_workspace(tmp_path_factory.mktemp("stable"), **STABLE)
        return ws, exp, tables

    # ---- IS stops and presents everything to the human
    def test_is_stops_at_awaiting_human_oos_approval_with_oos_not_accessed(self, life):
        ws, exp, tables = life
        row = reg.experiment_row(ws, exp)
        assert row["status"] == "AWAITING_HUMAN_OOS_APPROVAL" and row["is_status"] == "IS_SHORTLIST_ELIGIBLE"
        r = experiment_dir(ws, exp) / "results"
        assert (r / "IS_REPORT.md").exists() and (r / "IS_REPORT.json").exists()
        assert not (r / "OOS_REPORT.json").exists() and not reg.oos_spent(ws, exp) and not approval_path(ws, exp).exists()
        md = (r / "IS_REPORT.md").read_text()
        assert "**OOS status = NOT ACCESSED**" in md and oos_status_label(ws, exp) == NOT_ACCESSED
        assert "EXPERIMENT SELECTION TRIALS: 24 / 24" in md and "CAMPAIGN REVEALED SELECTION TRIALS: 24 / 480" in md
        assert "Number of statistical selection opportunities exposed so far: 24" in md
        assert len(top_group_ids(ws, exp)) == 5                       # TOP 5 IS GROUPS, the human unlocks at most 2

    def test_is_report_has_every_required_section_and_narrative(self, life):
        ws, exp, tables = life
        md = (experiment_dir(ws, exp) / "results" / "IS_REPORT.md").read_text()
        for h in ["## A. Experiment hypothesis", "## B. Exact event definition", "## C. Direction", "## D. Raw event frequency",
                  "## E. Data period used", "## F. Exact selection trial count", "## G. All 24 trial results", "## H. Multiplicity adjustments",
                  "## I. Top configurations", "## J. Model agreement", "## K. All IS calendar years", "## L. All 5 purged DEVELOPMENT_CV folds",
                  "## M–Q.", "## R. Feature diagnostics", "## S. Filter / component ladder", "## T. Sensitivity diagnostics",
                  "## U. Why each shortlisted configuration was selected", "## V. Why every other configuration was rejected",
                  "## W. Non-promotable interesting observations", "## X. Exact hashes", "## Y. OOS status"]:
            assert h in md, h
        assert "How this configuration emerged" in md and "No feature threshold was searched" in md
        assert "Selection trial count when observed: 24" in md and "Bonferroni adjusted p (experiment)" in md
        assert "campaign Bonferroni adjusted p" in md and "Model agreement: 3/3" in md and "DIAGNOSTIC ONLY — NOT A SELECTION TRIAL" in md
        assert "internal cross-validation — NOT OOS" in md and "DEVELOPMENT_CV" in md
        j = json.loads((experiment_dir(ws, exp) / "results" / "IS_REPORT.json").read_text())
        assert j["Y_oos_status"] == "NOT ACCESSED" and len(j["G_all_24_trials"]) == 24 and len(j["K_calendar_years"]) == 24 and len(j["L_development_cv_folds"]) == 24
        assert j["counters"]["experiment_selection_trials"] == "24 / 24" and len(j["X_hashes"]["manifest_sha256"]) == 64
        assert j["markdown_sha256"] == __import__("hashlib").sha256((experiment_dir(ws, exp) / "results" / "IS_REPORT.md").read_bytes()).hexdigest()

    # ---- the human gate
    def test_oos_cannot_run_without_a_human_approval_file(self, life, tmp_path):
        ws = clone(life[0], tmp_path)
        exp = life[1]
        assert not approval_path(ws, exp).exists()
        with pytest.raises(ApprovalError, match="no human approval file"):
            validate_approval(ws, exp)
        cid = reg.experiment_row(ws, exp)["campaign_id"]
        p = subprocess.run([sys.executable, str(CODE_ROOT / "scripts/run_campaign_oos.py"), "--campaign", cid, "--data", "/nonexistent.parquet",
                            "--workspace", str(ws.root)], capture_output=True, text=True)
        assert p.returncode != 0 and "must first be frozen" in (p.stderr + p.stdout)               # fails BEFORE reading any data
        assert not reg.oos_spent(ws, exp) and reg.read_oos_access(ws).empty
        with pytest.raises(EngineError, match="nothing to freeze"):                                 # and a freeze needs a valid positive human approval
            freeze_campaign_oos(ws, cid)
        assert reg.campaign_row(ws, cid)["status"] == "OPEN"

    def test_the_scripts_do_not_generate_the_approval_file(self, life, tmp_path):
        ws = clone(life[0], tmp_path)
        exp = life[1]
        for script in ("show_approval_hashes.py", "make_report.py", "campaign_status.py"):
            args = [sys.executable, str(CODE_ROOT / "scripts" / script), "--workspace", str(ws.root)]
            if script != "campaign_status.py":
                args += ["--experiment", exp]
            subprocess.run(args, capture_output=True, text=True)
        assert not approval_path(ws, exp).exists() and not list(ws.approvals.glob("*"))

    @pytest.mark.parametrize("name,override,needle", [
        ("wrong_is_hash", {"is_report_sha256": "0" * 64}, "is_report_sha256 does not match"),
        ("wrong_manifest_hash", {"experiment_manifest_sha256": "f" * 64}, "experiment_manifest_sha256 does not match"),
        ("not_human", {"approved_by": "CLAUDE"}, "approved_by must be exactly HUMAN_USER"),
        ("approved_not_bool", {"approved": "yes"}, "approved must be the boolean true"),
        ("empty_note", {"approval_note": "  "}, "approval_note must be non-empty"),
        ("wrong_experiment", {"experiment_id": "EXP_9999"}, "experiment_id mismatch"),
        ("wrong_campaign", {"campaign_id": "C999"}, "campaign_id mismatch"),
        ("no_groups", {"approved_target_side_groups": []}, "non-empty list"),
        ("duplicate_groups", {"approved_target_side_groups": ["DIR_RETURN_30|UPPER_HALF"] * 2}, "duplicate approved groups"),
        ("not_in_shortlist", {"approved_target_side_groups": ["DIR_PATH_SKEW_60|LOWER_HALF"]}, "not in the frozen IS shortlist"),
    ])
    def test_invalid_approval_files_are_refused(self, life, tmp_path, name, override, needle):
        ws = clone(life[0], tmp_path, name)
        exp = life[1]
        groups = override.pop("approved_target_side_groups", top_group_ids(ws, exp)[:1])
        human_approval(ws, exp, groups, **override)
        with pytest.raises(ApprovalError, match=needle):
            validate_approval(ws, exp)
        assert not reg.oos_spent(ws, exp)

    def test_more_than_two_oos_target_side_groups_fails(self, life, tmp_path):
        ws = clone(life[0], tmp_path)
        exp = life[1]
        three = top_group_ids(ws, exp)[:3]
        assert len(three) == 3
        human_approval(ws, exp, three)
        with pytest.raises(ApprovalError, match="MAX_OOS_GROUPS_PER_EXPERIMENT = 2"):
            validate_approval(ws, exp)
        human_approval(ws, exp, three[:2])
        assert validate_approval(ws, exp)["approved_target_side_groups"] == three[:2]              # exactly 2 is fine

    def test_human_declining_is_recorded_as_oos_not_approved(self, life, tmp_path):
        ws = clone(life[0], tmp_path)
        exp = life[1]
        human_approval(ws, exp, top_group_ids(ws, exp)[:1], approved=False)
        with pytest.raises(ApprovalError, match="OOS_NOT_APPROVED"):
            validate_approval(ws, exp)
        assert reg.experiment_row(ws, exp)["status"] == "OOS_NOT_APPROVED" and not reg.oos_spent(ws, exp)

    def test_valid_approval_passes_and_binds_the_exact_hashes(self, life, tmp_path):
        ws = clone(life[0], tmp_path)
        exp = life[1]
        human_approval(ws, exp, top_group_ids(ws, exp)[:1])
        ap = validate_approval(ws, exp)
        h = approval_hashes(ws, exp)
        assert ap["experiment_manifest_sha256"] == h["experiment_manifest_sha256"] and ap["is_report_sha256"] == h["is_report_sha256"]
        assert set(h["allowed_target_side_groups"]) == set(top_group_ids(ws, exp))

    def test_changed_event_spec_frozen_specs_partitions_or_is_results_invalidate_the_approval(self, life, tmp_path):
        import engine.experiment_lifecycle as lc
        exp = life[1]
        def fresh(name):
            ws = clone(life[0], tmp_path, name)
            human_approval(ws, exp, top_group_ids(ws, exp)[:1])
            validate_approval(ws, exp)                                                                  # valid before the change
            return ws, experiment_dir(ws, exp)
        ws, d = fresh("event")                                                                          # (1) event.py changed after approval
        os.chmod(d / "event.py", 0o644); (d / "event.py").write_text((d / "event.py").read_text() + "\n# tweak\n")
        with pytest.raises(ApprovalError, match="event.py changed after freeze"):
            validate_approval(ws, exp)
        ws, d = fresh("spec")                                                                           # (2) EVENT_SPEC.yaml changed
        os.chmod(d / "EVENT_SPEC.yaml", 0o644)
        (d / "EVENT_SPEC.yaml").write_text((d / "EVENT_SPEC.yaml").read_text().replace("pivot_left: 30", "pivot_left: 31", 1))
        with pytest.raises(ApprovalError, match="EVENT_SPEC.yaml changed after freeze"):
            validate_approval(ws, exp)
        ws, d = fresh("partitions")                                                                     # (3) a partition boundary moved
        os.chmod(d / "EVENT_SPEC.yaml", 0o644)
        (d / "EVENT_SPEC.yaml").write_text((d / "EVENT_SPEC.yaml").read_text().replace('oos_end: "2021-01-01"', 'oos_end: "2020-11-01"'))
        with pytest.raises(ApprovalError, match="partitions changed after freeze"):
            validate_approval(ws, exp)
        ws, d = fresh("frozen")                                                                         # (4) a frozen spec changed
        real = lc.sha256_file
        from pathlib import Path
        import pytest as _p
        mp = _p.MonkeyPatch()
        mp.setattr(lc, "sha256_file", lambda p: "0" * 64 if Path(p).name == "ACCEPTANCE_RULES.yaml" else real(p))
        try:
            with pytest.raises(ApprovalError, match="frozen specification changed after freeze"):
                validate_approval(ws, exp)
        finally:
            mp.undo()
        ws, d = fresh("results")                                                                        # (5) IS results changed
        (d / "results" / "results.json").write_text((d / "results" / "results.json").read_text().replace('"experiment_id"', '"experiment_id" ', 1))
        with pytest.raises(ApprovalError, match="IS results.json changed"):
            validate_approval(ws, exp)
        ws, d = fresh("report_md")                                                                      # (6) IS_REPORT.md edited
        (d / "results" / "IS_REPORT.md").write_text((d / "results" / "IS_REPORT.md").read_text() + "\nI looked at OOS.\n")
        with pytest.raises(ApprovalError, match="IS_REPORT.md was edited"):
            validate_approval(ws, exp)
        ws, d = fresh("new_report")                                                                     # (7) report regenerated with new content
        reg.set_verification(ws, exp, {f"DIR_RETURN_30|XGB": {"label": "FAILED", "mode": "strong"}}, "FAILED", F)
        write_is_report(ws, exp)
        with pytest.raises(ApprovalError):
            validate_approval(ws, exp)                                                                  # new report hash != approved hash

    def test_unverified_model_path_blocks_the_unlock(self, life, tmp_path):
        ws = clone(life[0], tmp_path)
        exp = life[1]
        row = reg.experiment_row(ws, exp)
        ver = json.loads(row["verification_json"])
        ver["DIR_RETURN_30|XGB"] = {"label": "RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE", "mode": "fast"}      # not strong -> not final
        reg.update_experiment(ws, exp, verification_json=json.dumps(ver))
        write_is_report(ws, exp)
        human_approval(ws, exp, ["DIR_RETURN_30|UPPER_HALF"])
        with pytest.raises(ApprovalError, match="not externally verified"):
            validate_approval(ws, exp)

    # ---- one-shot OOS (1 group)
    @pytest.fixture(scope="class")
    def spent(self, life, tmp_path_factory):
        ws = clone(life[0], tmp_path_factory.mktemp("spent"), "ws")
        exp = life[1]
        groups = top_group_ids(ws, exp)[:1]
        human_approval(ws, exp, groups)
        report = spend_oos(ws, exp, life[2])
        return ws, exp, groups, report

    def test_oos_confirms_the_stable_effect_and_logs_the_unlock_permanently(self, spent):
        ws, exp, groups, r = spent
        assert r["status"] == "OOS_CONFIRMED" and reg.experiment_row(ws, exp)["status"] == "OOS_CONFIRMED"
        assert r["group_verdicts"][groups[0]]["confirmed"] and r["group_verdicts"][groups[0]]["models_passing"] == 3
        led = reg.read_oos_access(ws)
        assert len(led) == 1 and led.iloc[0]["campaign_id"] == "C001" and reg.verify_oos_ledger(ws) == 1
        row = led.iloc[0]
        assert row["experiments"] == exp and row["approved_experiment_groups"] == f"{exp}:{groups[0]}" and row["n_oos_confirmations"] == "3"
        assert row["oos_start"] == "2020-01-01" and row["oos_end"] == "2021-01-01"
        assert row["freeze_hash"] == reg.campaign_row(ws, "C001")["oos_freeze_hash"] and reg.campaign_row(ws, "C001")["status"] == "OOS_SPENT"
        assert row["unlock_timestamp"] and len(row["code_hash"]) == 64

    def test_oos_can_only_be_unlocked_once(self, spent):
        ws, exp, groups, _ = spent
        with pytest.raises(OOSContaminated, match="CAMPAIGN OOS HAS BEEN SPENT"):
            validate_approval(ws, exp)
        human_approval(ws, exp, groups)                                                                 # even a fresh human approval cannot re-open it
        with pytest.raises(OOSContaminated, match="CAMPAIGN OOS HAS BEEN SPENT"):
            validate_approval(ws, exp)
        with pytest.raises(EngineError, match="CAMPAIGN OOS HAS BEEN SPENT"):
            reg.append_oos_access(ws, campaign_id="C001")
        assert len(reg.read_oos_access(ws)) == 1

    def test_is_report_is_sealed_and_cannot_claim_not_accessed_after_oos(self, spent):
        ws, exp, groups, _ = spent
        assert oos_status_label(ws, exp) != NOT_ACCESSED and "SPENT" in oos_status_label(ws, exp)
        with pytest.raises(ReportSealedError):
            write_is_report(ws, exp)
        md = (experiment_dir(ws, exp) / "results" / "IS_REPORT.md").read_text()                       # the sealed (pre-OOS) report is unchanged
        assert "OOS status = NOT ACCESSED" in md                                                         # it was true when written; cannot be regenerated

    def test_oos_report_lists_every_approved_model_confirmation_and_the_family_corrections(self, spent):
        ws, exp, groups, r = spent
        assert r["oos_model_confirmations"] == 3 and r["family_size_for_multiple_testing"] == 3
        rows = reg.read_oos_trials(ws)
        assert len(rows) == 3 and set(rows["model"]) == {"RIDGE", "SPLINE", "XGB"}
        p = rows["raw_p"].astype(float).to_numpy()
        assert np.allclose(rows["oos_bonferroni_p"].astype(float), np.minimum(p * 3, 1.0))
        assert np.allclose(rows["oos_q"].astype(float), benjamini_hochberg(p))
        assert (experiment_dir(ws, exp) / "results" / "OOS_REPORT.md").read_text().count("| DIR_RETURN_30|UPPER_HALF |") == 3

    def test_lineage_child_cannot_claim_the_same_oos_untouched(self, spent):
        ws, exp, groups, _ = spent
        with pytest.raises(OOSContaminated, match="CAMPAIGN OOS HAS BEEN SPENT"):
            reg.register_experiment(ws, reg.experiment_row(ws, exp)["campaign_id"], lineage_parent=exp)

    def test_changing_the_experiment_after_oos_marks_it_contaminated(self, spent, tmp_path):
        ws = clone(spent[0], tmp_path)
        exp = spent[1]
        assert mark_contamination_if_mutated(ws, exp) is False
        d = experiment_dir(ws, exp)
        os.chmod(d / "event.py", 0o644); (d / "event.py").write_text((d / "event.py").read_text() + "\n# after seeing OOS\n")
        assert mark_contamination_if_mutated(ws, exp) is True
        assert reg.experiment_row(ws, exp)["status"] == "OOS_CONTAMINATED"
        with pytest.raises(EngineError, match="OOS_CONTAMINATED"):
            C.precheck_cpcv(ws, exp)

    def test_oos_phase_never_touches_the_final_lockbox(self):
        import inspect

        from engine import cpcv as cpcv_mod
        from engine import oos_stage
        from engine.partitions import oos_view, parse_partitions
        parts = parse_partitions(LIFE_PARTS)
        idx = pd.date_range("2019-06-01", "2021-03-01", freq="1D", tz="UTC")
        bars = pd.DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0}, index=idx)
        poisoned = bars.copy()
        poisoned.loc[poisoned.index >= parts.lockbox_start, ["open", "high", "low", "close"]] = 9e9
        a, b = oos_view(bars, parts), oos_view(poisoned, parts)
        assert a.equals(b) and a.index.max() < parts.oos_end                                              # lockbox poison is invisible
        # both OOS-touching entry points cut the bars with oos_view BEFORE any table is built or any stage executes
        for fn, later in ((oos_stage.run_campaign_oos, ("build_event_tables(", "execute_campaign_oos(")), (cpcv_mod.run_cpcv, ("build_event_tables(", "execute_cpcv(", "run_cpcv_tables("))):
            src = inspect.getsource(fn)
            cut = src.index("oos_view(bars")
            assert all(src.index(tok) > cut for tok in later if tok in src), fn.__name__
            assert "del bars" in src[cut:], fn.__name__                                                   # the uncut frame is dropped immediately

    # ---- OOS multiple testing across 2 approved groups (3 x G = 6 confirmations)
    def test_oos_multiple_testing_includes_all_approved_model_trials(self, life, tmp_path):
        ws = clone(life[0], tmp_path)
        exp = life[1]
        groups = top_group_ids(ws, exp)[:2]
        human_approval(ws, exp, groups)
        r = spend_oos(ws, exp, life[2])
        rows = reg.read_oos_trials(ws)
        assert len(rows) == 6 == r["oos_model_confirmations"] == r["family_size_for_multiple_testing"]
        p = rows["raw_p"].astype(float).to_numpy()
        assert np.allclose(rows["oos_bonferroni_p"].astype(float), np.minimum(p * 6, 1.0))               # Bonferroni universe = 3 x 2
        assert np.allclose(rows["oos_q"].astype(float), benjamini_hochberg(p))                           # BH over all 6, not just winners
        assert set(rows["group_id"]) == set(groups) and (rows.groupby("group_id").size() == 3).all()
        assert set(r["group_verdicts"]) == set(groups) and "formulas" in r

    # ---- CPCV after confirmed OOS
    def test_cpcv_confirms_the_stable_effect_and_stops_awaiting_final_lockbox(self, spent, life):
        ws, exp, groups, _ = spent
        rep = run_cpcv_stage(ws, exp, life[2])
        assert rep["n_splits"] == 15 and rep["cpcv_confirmed_groups"] == groups
        row = reg.experiment_row(ws, exp)
        assert row["status"] == "AWAITING_FINAL_LOCKBOX"
        hist = [h[0] for h in json.loads(row["status_history"])]
        assert hist[-3:] == ["OOS_CONFIRMED", "CPCV_CONFIRMED", "AWAITING_FINAL_LOCKBOX"]
        for m in ("RIDGE", "SPLINE", "XGB"):
            s = rep["summary"][f"{groups[0]}|{m}"]
            assert s["n_valid_splits"] == 15 and s["cpcv_pass"] and s["n_effect_positive"] >= 12 and s["n_uplift_positive"] >= 12
            assert s["median_effect"] > 0 and s["median_uplift"] > 0 and s["p10_uplift"] <= s["median_uplift"] <= s["p90_uplift"]
            assert s["worst_split"] is not None and s["best_split"] is not None
        assert rep["pbo_diagnostic"]["status"] == "COMPUTED" and 0.0 <= rep["pbo_diagnostic"]["pbo"] <= 1.0
        cp = reg.read_cpcv(ws)
        assert len(cp) == 3 and (cp["group_cpcv_pass"] == "True").all()
        assert len(reg.read_oos_access(ws)) == 1                                                          # the lockbox / OOS were not touched again
        assert "not implemented" in (CODE_ROOT / "scripts/confirm_lockbox.py").read_text()
        p = subprocess.run([sys.executable, str(CODE_ROOT / "scripts/confirm_lockbox.py")], capture_output=True, text=True)
        assert p.returncode != 0 and "not implemented" in (p.stderr + p.stdout)


# ===================================================== IS curve-fit fails OOS =====================================================
class TestCurveFitFailsOos:
    @pytest.fixture(scope="class")
    def res(self, tmp_path_factory):
        ws, exp, tables = lifecycle_workspace(tmp_path_factory.mktemp("curvefit"), **CURVEFIT)
        groups = top_group_ids(ws, exp)[:1]
        human_approval(ws, exp, groups)
        report = spend_oos(ws, exp, tables)
        return ws, exp, tables, groups, report

    def test_is_looks_excellent_but_oos_rejects_it_and_the_lifecycle_stops(self, res):
        ws, exp, tables, groups, r = res
        t = reg.experiment_trials(ws, exp)
        assert (t["decision"] == "IS_SHORTLIST_ELIGIBLE").sum() >= 3 and t["standardized_uplift"].max() > 0.3     # a great-looking IS curve fit
        assert r["status"] == "OOS_REJECTED" and reg.experiment_row(ws, exp)["status"] == "OOS_REJECTED"
        conf = pd.DataFrame(r["confirmations"])
        assert (conf["selected_effect"] < 0).all() and not conf["gates_pass"].any()
        assert not r["group_verdicts"][groups[0]]["confirmed"]

    def test_cpcv_cannot_rescue_an_oos_failure(self, res):
        ws, exp, tables, groups, _ = res
        with pytest.raises(EngineError, match="can never rescue a failed candidate"):
            run_cpcv_stage(ws, exp, tables)
        with pytest.raises(EngineError, match="OOS_CONFIRMED"):
            C.precheck_cpcv(ws, exp)
        assert reg.read_cpcv(ws).empty and reg.experiment_row(ws, exp)["status"] == "OOS_REJECTED"

    def test_cpcv_refuses_every_non_oos_confirmed_status(self, res, tmp_path):
        ws = clone(res[0], tmp_path)
        exp = res[1]
        for status in ("IS_REJECTED", "IS_PROVISIONAL_CANDIDATE", "AWAITING_HUMAN_OOS_APPROVAL", "OOS_NOT_APPROVED", "CPCV_REJECTED"):
            reg.update_experiment(ws, exp, status=status)
            with pytest.raises(EngineError, match="CPCV runs only for OOS_CONFIRMED"):
                C.precheck_cpcv(ws, exp)


# ===================================================== OOS passes but CPCV is unstable ============================================
class TestCpcvVetoesAnOosConfirmedCandidate:
    @pytest.fixture(scope="class")
    def res(self, tmp_path_factory):
        ws, exp, tables = lifecycle_workspace(tmp_path_factory.mktemp("cpcvbad"), **UNSTABLE_CPCV)
        groups = top_group_ids(ws, exp)[:1]
        human_approval(ws, exp, groups)
        oos = spend_oos(ws, exp, tables)
        rep = run_cpcv_stage(ws, exp, tables) if oos["status"] == "OOS_CONFIRMED" else None
        return ws, exp, tables, groups, oos, rep

    def test_oos_confirms_but_cpcv_rejects_for_instability(self, res):
        ws, exp, tables, groups, oos, rep = res
        assert oos["status"] == "OOS_CONFIRMED" and rep is not None
        assert rep["cpcv_confirmed_groups"] == [] and reg.experiment_row(ws, exp)["status"] == "CPCV_REJECTED"
        s = rep["summary"]
        assert not any(v["cpcv_pass"] for v in s.values())
        assert all(v["n_effect_positive"] < 12 or v["n_uplift_positive"] < 12 or v["median_effect"] <= 0 for v in s.values())
        assert "AWAITING_FINAL_LOCKBOX" not in [h[0] for h in json.loads(reg.experiment_row(ws, exp)["status_history"])]

    def test_cpcv_failure_vetoes_final_confirmation_eligibility(self, res):
        ws, exp, tables, groups, oos, rep = res
        cp = reg.read_cpcv(ws)
        assert len(cp) == 3 and (cp["group_cpcv_pass"] == "False").all()
        assert reg.experiment_row(ws, exp)["status"] not in ("CPCV_CONFIRMED", "AWAITING_FINAL_LOCKBOX")
        assert rep["group_verdicts"][groups[0]]["cpcv_pass"] is False


# ===================================================== CPCV mechanics (fast, no model fitting) ======================================
def test_cpcv_generates_exactly_15_splits_with_no_search_over_n_or_k():
    splits = C.cpcv_split_ids(6, 2)
    assert len(splits) == 15 == F.trial_policy["cpcv"]["n_splits"] and len(set(splits)) == 15
    assert all(len(s) == 2 and s == tuple(sorted(s)) for s in splits)
    assert splits[0] == (0, 1) and splits[-1] == (4, 5)                                            # deterministic order, no shuffling
    from collections import Counter
    assert set(Counter(g for s in splits for g in s).values()) == {5}                              # every group is held out in exactly 5 splits
    assert (F.trial_policy["cpcv"]["n_groups"], F.trial_policy["cpcv"]["n_test_groups"]) == (6, 2)


def test_cpcv_groups_are_chronological_equal_count_and_whole_trading_days():
    t = pd.date_range("2018-01-02 15:00", periods=1200, freq="45min", tz="UTC")
    t = t[(t.tz_convert("America/New_York").hour >= 9) & (t.tz_convert("America/New_York").hour < 16)]
    regions = C.cpcv_groups(t, 6, "America/New_York")
    assert len(regions) == 6
    ns = t.as_unit("ns").asi8
    sizes = [int(((ns >= lo) & (ns < hi)).sum()) for lo, hi in regions]
    assert sum(sizes) == len(t) and max(sizes) - min(sizes) <= len(t) // 6 * 0.35 + 8              # ~equal event counts
    for (a, b), (c, d) in zip(regions[:-1], regions[1:]):
        assert b == c and a < b                                                                      # contiguous, chronological
    for lo, _ in regions[1:]:
        loc = pd.Timestamp(lo, tz="UTC").tz_convert("America/New_York")
        assert (loc.hour, loc.minute) == (0, 0)                                                      # boundaries are trading-day starts


def _day(n):
    return int(pd.Timestamp("2019-01-01", tz="UTC").value) + n * 24 * 3600 * 10**9


def test_cpcv_purges_training_events_whose_label_windows_overlap_a_held_out_region():
    hour = 3600 * 10**9
    regions = [(_day(10), _day(20)), (_day(40), _day(50))]                      # two held-out groups
    ev = np.array([_day(9), _day(9) + 23 * hour, _day(5), _day(21), _day(30), _day(39), _day(60)], dtype=np.int64)
    eff = ev + np.array([2 * hour, 2 * hour, 2 * hour, 1 * hour, 1 * hour, 2 * 24 * hour, 1 * hour], dtype=np.int64)
    # event[0]: day 9 00:00, label ends day 9 02:00 (before region) -> kept ; event[1]: day 9 23:00 label ends day 10 01:00 -> OVERLAP -> purged
    # event[5]: day 39 label ends day 41 -> overlaps region 2 -> purged
    train, test = C.split_masks(ev, eff, regions, embargo_ns=0)
    assert train.tolist() == [True, False, True, True, True, False, True] and not test.any()
    ev2 = np.array([_day(12), _day(45)], dtype=np.int64)
    tr2, te2 = C.split_masks(np.r_[ev, ev2], np.r_[eff, ev2 + hour], regions, embargo_ns=0)
    assert te2[-2:].all() and not tr2[-2:].any()                                  # events inside a held-out region are TEST, never train


def test_cpcv_embargo_is_applied_at_every_held_out_boundary_on_both_sides():
    emb = 60 * 60 * 10**9                                                         # 60 bars of information time (max primary horizon)
    assert emb == C.max_primary_horizon_bars(F) * int(F.interval.value) if hasattr(C, "max_primary_horizon_bars") else True
    regions = [(_day(10), _day(20)), (_day(40), _day(50))]
    minute = 60 * 10**9
    probes = {"before_r1_inside_embargo": _day(10) - 30 * minute, "before_r1_outside": _day(10) - 61 * minute,
              "after_r1_inside_embargo": _day(20) + 30 * minute, "after_r1_outside": _day(20) + 61 * minute,
              "before_r2_inside_embargo": _day(40) - 59 * minute, "before_r2_outside": _day(40) - 61 * minute,
              "after_r2_inside_embargo": _day(50) + 59 * minute, "after_r2_outside": _day(50) + 61 * minute,
              "far": _day(30)}
    ev = np.array(list(probes.values()), dtype=np.int64)
    eff = ev + 1                                                                   # tiny labels: only the embargo can remove them
    train, _ = C.split_masks(ev, eff, regions, embargo_ns=emb)
    kept = dict(zip(probes, train.tolist()))
    for k in ("before_r1_inside_embargo", "after_r1_inside_embargo", "before_r2_inside_embargo", "after_r2_inside_embargo"):
        assert kept[k] is False, k                                                 # embargoed at EVERY boundary (4 boundaries)
    for k in ("before_r1_outside", "after_r1_outside", "before_r2_outside", "after_r2_outside", "far"):
        assert kept[k] is True, k


def test_cpcv_pass_rule_thresholds_are_exactly_12_of_15_and_positive_medians():
    rule = F.acceptance["cpcv"]
    def recs(n_pos_eff, n_pos_up, eff_pos=0.2, eff_neg=-0.05, n=15):
        return [{"split": i, "valid": True, "selected_effect": eff_pos if i < n_pos_eff else eff_neg,
                 "uplift": 0.1 if i < n_pos_up else -0.02} for i in range(n)]
    assert C.pass_rule(recs(15, 15), rule)["cpcv_pass"]
    assert C.pass_rule(recs(12, 12), rule)["cpcv_pass"]                              # 12/15 is the floor
    assert not C.pass_rule(recs(11, 15), rule)["cpcv_pass"] and not C.pass_rule(recs(15, 11), rule)["cpcv_pass"]
    bad_median = [{"split": i, "valid": True, "selected_effect": 5.0 if i < 12 else -50.0, "uplift": 0.1} for i in range(15)]
    assert C.pass_rule(bad_median, rule)["n_effect_positive"] == 12
    neg_med = [{"split": i, "valid": True, "selected_effect": -0.01 if i < 8 else 0.2, "uplift": 0.1} for i in range(15)]
    assert not C.pass_rule(neg_med, rule)["cpcv_pass"]
    few = recs(15, 15)[:14] + [{"split": 14, "valid": False, "selected_effect": float("nan"), "uplift": float("nan")}]
    assert not C.pass_rule(few, rule)["cpcv_pass"]                                   # an invalid split can never be waived
    s = C.pass_rule(recs(13, 14), rule)
    assert s["fraction_effect_positive"] == pytest.approx(13 / 15) and s["fraction_uplift_positive"] == pytest.approx(14 / 15)
    assert {"median_effect", "median_uplift", "p10_uplift", "p90_uplift", "worst_split", "best_split"} <= set(s)


def test_pbo_not_applicable_for_one_candidate_and_computed_from_rank_reversals():
    one = C.pbo_diagnostic({"a": np.array([0.1] * 6)}, C.cpcv_split_ids(6, 2), 6)
    assert one["pbo"] is None and one["status"] == "NOT APPLICABLE"
    splits = C.cpcv_split_ids(6, 2)
    # config A is uniformly better than B in every group -> the best IS config is always the best OOS config -> PBO = 0
    stable = C.pbo_diagnostic({"A": np.full(6, 0.3), "B": np.full(6, 0.1), "C": np.full(6, -0.1)}, splits, 6)
    assert stable["status"] == "COMPUTED" and stable["pbo"] == 0.0
    # anti-persistent configs: whichever is best in training groups is WORST in the held-out groups -> PBO high
    rng = np.random.default_rng(0)
    base = rng.normal(size=6)
    anti = C.pbo_diagnostic({"A": base, "B": -base}, splits, 6)
    assert anti["pbo"] >= 0.5 and len(anti["logits"]) == 15
    assert "not an independent p-value" in anti["note"]


def test_pbo_diagnostic_cannot_influence_verdicts_or_ranking(monkeypatch):
    import inspect
    from engine import acceptance
    src_reg = inspect.getsource(reg)
    assert "pbo" not in inspect.getsource(acceptance).lower() and "pbo" not in src_reg.replace("pbo_diagnostic", "").lower().replace("cpcv_cols", "")
    # computed AFTER and apart from every verdict: swapping it for garbage cannot change a verdict
    from engine.synthetic import make_event_tables
    tables = make_event_tables(years=range(2015, 2021), events_per_week=6, signal="linear", slope=0.4, seed=3)
    events, features, eligible, targets, calendar = tables
    groups = ["DIR_RETURN_30|UPPER_HALF"]
    a = C.run_cpcv_tables(events, features, targets, eligible, calendar, groups, F, models=["RIDGE"])
    monkeypatch.setattr(C, "pbo_diagnostic", lambda *x, **k: {"pbo": 0.999, "status": "COMPUTED", "n_configs": 99})
    b = C.run_cpcv_tables(events, features, targets, eligible, calendar, groups, F, models=["RIDGE"])
    assert a["group_verdicts"] == b["group_verdicts"] and a["summary"] == b["summary"] and a["pbo"]["pbo"] != b["pbo"]["pbo"]


class _Probe:
    """Fast deterministic stand-in model that records exactly which rows it was fitted on."""
    log: list = []

    def __init__(self):
        pass

    def fit(self, X, y):
        _Probe.log.append(("fit", X.index.to_numpy().copy(), np.asarray(y).copy()))
        x = X["ER_60"].to_numpy()
        self.b = float(np.dot(x - x.mean(), y - y.mean()) / np.dot(x - x.mean(), x - x.mean()))
        self.mx, self.my = float(x.mean()), float(y.mean())
        return self

    def predict(self, X):
        return self.my + self.b * (X["ER_60"].to_numpy() - self.mx)


def test_cpcv_fits_are_train_only_purged_embargoed_and_use_no_global_statistics():
    from engine.synthetic import make_event_tables
    events, features, eligible, targets, calendar = make_event_tables(years=range(2015, 2021), events_per_week=8, signal="linear", slope=0.4, seed=5)
    _Probe.log = []
    res = C.run_cpcv_tables(events, features, targets, eligible, calendar, ["DIR_RETURN_60|UPPER_HALF"], F, models=["RIDGE"],
                            factory=lambda m: _Probe)
    ev = events.sort_values(["event_time", "event_id"]).reset_index(drop=True)
    ev_ns = ev["event_time"].astype("int64").to_numpy() if ev["event_time"].dt.unit == "ns" else ev["event_time"].dt.as_unit("ns").astype("int64").to_numpy()
    tdf = targets["DIR_RETURN_60"].set_index("event_id").loc[ev["event_id"]]
    eff = pd.DatetimeIndex(tdf["effective_target_end"]).as_unit("ns").asi8
    recs = res["records"][("DIR_RETURN_60", "UPPER_HALF", "RIDGE")]
    assert len(recs) == 15 and all(r["valid"] for r in recs)
    emb = 60 * int(F.interval.value)
    # every FINAL fit of a split used exactly the legal training rows of that split (the other fits are inner OOF fits)
    finals = [l for l in _Probe.log if len(l[1]) in {r["n_train"] for r in recs}]
    for r in recs:
        tr, te = C.split_masks(ev_ns, eff, [res["regions"][k] for k in r["test_groups"]], emb)
        assert r["n_train"] == int(tr.sum()) and r["n_test"] == int(te.sum())
        assert not (tr & te).any()
        assert any(np.array_equal(l[1], np.flatnonzero(tr)) for l in finals), r["split"]       # fitted on exactly these rows
    # nothing is carried between splits: mutating ONLY test-region labels/features leaves every split's training threshold unchanged
    f2, t2 = features.copy(), {k: v.copy() for k, v in targets.items()}
    r0 = res["regions"][recs[0]["test_groups"][0]]
    in_test = ((events["event_time"].dt.as_unit("ns").astype("int64") >= r0[0]) & (events["event_time"].dt.as_unit("ns").astype("int64") < r0[1])).to_numpy()
    t2["DIR_RETURN_60"].loc[in_test, "value"] = 1e6
    f2.loc[in_test, "ER_60"] = 1e6
    res2 = C.run_cpcv_tables(events, f2, t2, eligible, calendar, ["DIR_RETURN_60|UPPER_HALF"], F, models=["RIDGE"])
    res1 = C.run_cpcv_tables(events, features, targets, eligible, calendar, ["DIR_RETURN_60|UPPER_HALF"], F, models=["RIDGE"])
    k = ("DIR_RETURN_60", "UPPER_HALF", "RIDGE")
    g0 = recs[0]["test_groups"][0]
    held_out_thr, trained_on_thr = [], []
    for a, b, sp in zip(res1["records"][k], res2["records"][k], res["splits"]):
        (held_out_thr if g0 in sp else trained_on_thr).append((a["threshold"], b["threshold"]))
    assert len(held_out_thr) == 5 and len(trained_on_thr) == 10                       # each group is held out in exactly 5 of 15 splits
    # splits that HOLD OUT the mutated group never saw those rows in training: identical thresholds
    assert all(x == y for x, y in held_out_thr), held_out_thr
    # control: splits that TRAIN on the mutated rows must react (otherwise the mutation proves nothing)
    assert any(x != y for x, y in trained_on_thr)


def test_oos_confirmation_gates_and_group_rule_unit():
    rule = F.acceptance["oos_confirmation"]
    def row(model, group="G|U", **kw):
        r = dict(group_id=group, model=model, n_selected=300, selected_frequency=2.0, standardized_uplift=0.2, selected_effect=0.1,
                 bootstrap_ci_low=0.01, raw_p=0.001)
        r.update(kw)
        return r
    rows = oos_confirmations([row("RIDGE"), row("SPLINE"), row("XGB", selected_effect=-0.01)], rule)
    assert [r["gates_pass"] for r in rows] == [True, True, False]                    # negative selected effect fails the OOS gate too
    assert rows[0]["oos_trials_in_family"] == 3 and rows[0]["oos_bonferroni_p"] == pytest.approx(0.003)
    assert group_verdicts(rows, rule)["G|U"] == {"models_passing": 2, "models": ["RIDGE", "SPLINE"], "confirmed": True}
    one = oos_confirmations([row("RIDGE"), row("SPLINE", standardized_uplift=0.05), row("XGB", selected_frequency=0.5)], rule)
    assert group_verdicts(one, rule)["G|U"]["confirmed"] is False                      # 1 of 3 is not a confirmation
    big_family = oos_confirmations([row(m, group=f"G{g}|U", raw_p=0.01) for g in range(2) for m in ("RIDGE", "SPLINE", "XGB")], rule)
    assert big_family[0]["oos_bonferroni_p"] == pytest.approx(0.06) and not big_family[0]["gates_pass"]    # 0.01 * 6 > 0.05
