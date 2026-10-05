"""v1.2 lifecycle on table-level synthetic data with KNOWN structure:

  IS (24 trials) -> near-tie detection -> HUMAN decision -> optional campaign SELECTION HOLDOUT -> HUMAN chooses exactly ONE final config
  -> AUTOMATIC fixed CPCV (post-selection robustness) -> AWAITING_FINAL_LOCKBOX_APPROVAL (the lockbox is never opened).

TEST CODE plays the HUMAN when it writes approval / selection files (production code never does: AGENTS.md rule 1). Strong-mode verification and the
sensitivity verdict are injected through the registry (the real verifier / probes are exercised elsewhere). Scenarios A-E at the bottom."""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from engine import cpcv as C
from engine import trial_registry as reg
from engine.common import CODE_ROOT, EngineError, load_frozen
from engine.experiment_lifecycle import experiment_dir
from engine.is_report import NOT_ACCESSED, ReportSealedError, selection_holdout_status_label, write_is_report
from engine.multiplicity import benjamini_hochberg
from engine.selection_holdout_stage import (ApprovalError, SelectionHoldoutContaminated, approval_hashes, approval_path, final_selection_path,
                                            freeze_campaign_selection_holdout, freeze_final_config, freeze_path, mark_contamination_if_mutated,
                                            validate_approval, validate_campaign_open, validate_final_selection)
from tests.scenario_helpers import (CLEAR_WINNER, LIFE_PARTS, NEAR_TIE_PAIR, campaign_open_approval, finalize_config, human_approval, human_final_selection,
                                    lifecycle_workspace, pair_60_first, proposable, run_cpcv_stage, spend_selection_holdout, top_group_ids, weaken)

F = load_frozen()
TWO_TARGETS = {"DIR_RETURN_180": 0.0, "DIR_PATH_SKEW_60": 0.0}                                              # 15 and 60 carry the same planted relation (and, via `tie`, the same noise)
TIE = {"DIR_RETURN_60": "DIR_RETURN_15"}
# one bad year (2019) inside DEVELOPMENT: IS tolerates it (4/5 years, 4/5 folds) but every CPCV split that holds the 2019 group out nets negative
UNSTABLE = dict(signal="linear", slope=0.0, slope_by_year={**{y: 1.0 for y in (2015, 2016, 2017, 2018, 2020, 2021, 2022)}, 2019: -1.6}, target_scale=TWO_TARGETS, tie=TIE)
# looks great in DEVELOPMENT, collapses in the selection holdout year
CURVEFIT = dict(signal="linear", slope=0.0, slope_by_year={**{y: 0.6 for y in range(2015, 2020)}, **{y: -0.3 for y in range(2020, 2023)}}, target_scale=TWO_TARGETS, tie=TIE)


def clone(ws, tmp_path, name="copy"):
    dst = tmp_path / name
    shutil.copytree(ws.root, dst)
    return reg.Workspace(dst)


def report_of(ws, exp):
    return json.loads((experiment_dir(ws, exp) / "results" / "SELECTION_HOLDOUT_REPORT.json").read_text())


def history(ws, exp):
    return [h[0] for h in json.loads(reg.experiment_row(ws, exp)["status_history"])]


def with_spy():
    """Spy on C.run_cpcv_tables recording the event-time window CPCV was given."""
    seen = {}
    real = C.run_cpcv_tables

    def spy(events, features, targets, eligible, calendar_index, groups, frozen, **kw):
        t = pd.DatetimeIndex(events["event_time"][np.asarray(eligible, dtype=bool)])
        seen.update(min=t.min(), max=t.max(), groups=list(groups), n=len(t))
        return real(events, features, targets, eligible, calendar_index, groups, frozen, **kw)
    return seen, spy


# ============================================================ module fixtures (each = one real table-level IS run)
@pytest.fixture(scope="module")
def near_life(tmp_path_factory):
    return lifecycle_workspace(tmp_path_factory.mktemp("near"), **NEAR_TIE_PAIR)


@pytest.fixture(scope="module")
def clear_life(tmp_path_factory):
    return lifecycle_workspace(tmp_path_factory.mktemp("clear"), **CLEAR_WINNER)


@pytest.fixture(scope="module")
def spent_b(near_life, tmp_path_factory):
    """Near tie: both near-tied configs approved, frozen together, holdout opened once. 60 loses half of its effect in the holdout year."""
    ws = clone(near_life[0], tmp_path_factory.mktemp("spent_b"), "ws")
    exp, tables = near_life[1], weaken(near_life[2], "DIR_RETURN_60", [2020], 0.5)
    cfgs = pair_60_first(proposable(ws, exp, 0))                                                         # [60, 15]
    human_approval(ws, exp, cfgs)
    rep = spend_selection_holdout(ws, exp, tables)
    return ws, exp, tables, cfgs, rep


# ============================================================ IS stage: the engine stops and shows everything
class TestIsStopsAtTheHumanDecision:
    def test_is_stops_with_selection_holdout_not_accessed_and_24_trials(self, near_life):
        ws, exp, _ = near_life
        row = reg.experiment_row(ws, exp)
        assert row["status"] == "NEAR_TIE_REVIEW_REQUIRED" and row["is_status"] == "IS_SHORTLIST_ELIGIBLE"
        r = experiment_dir(ws, exp) / "results"
        assert (r / "IS_REPORT.md").exists() and not (r / "SELECTION_HOLDOUT_REPORT.json").exists() and not reg.selection_holdout_spent(ws, exp)
        assert not list(ws.approvals.glob("*")) and reg.read_selection_holdout_access(ws).empty and reg.read_final_configs(ws).empty
        md = (r / "IS_REPORT.md").read_text()
        assert "**SELECTION HOLDOUT status = NOT ACCESSED**" in md and selection_holdout_status_label(ws, exp) == NOT_ACCESSED
        assert "EXPERIMENT SELECTION TRIALS: 24 / 24" in md and "CAMPAIGN REVEALED SELECTION TRIALS: 24 / 480" in md
        assert len(top_group_ids(ws, exp)) == 4 and reg.integrity_check(ws)["selection_trials"] == 24     # 4 eligible (15, 60 x two sides); 24 pre-registered trials

    def test_is_report_has_every_required_section(self, near_life):
        ws, exp, _ = near_life
        md = (experiment_dir(ws, exp) / "results" / "IS_REPORT.md").read_text()
        for h in ["## A. Experiment hypothesis", "## B. Exact event definition", "## C. Direction", "## D. Raw event frequency", "## E. Data period used",
                  "## F. Exact selection trial count", "## G. All 24 trial results", "## H. Multiplicity adjustments", "## I. Top configurations",
                  "## J. Model agreement", "## K. All IS calendar years", "## L. All 5 purged DEVELOPMENT_CV folds", "## M–Q.", "## R. Feature diagnostics",
                  "## S. Filter / component ladder", "## T. Sensitivity diagnostics", "## U. Why each shortlisted configuration was selected",
                  "## V. Why every other configuration was rejected", "## NT. CONFIGURATION UNCERTAINTY / NEAR-TIES", "## W. Non-promotable interesting observations",
                  "## X. Exact hashes", "## Y. SELECTION HOLDOUT status"]:
            assert h in md, h
        assert "internal cross-validation — NOT SELECTION HOLDOUT" in md and "DIAGNOSTIC ONLY — NOT A SELECTION TRIAL" in md
        j = json.loads((experiment_dir(ws, exp) / "results" / "IS_REPORT.json").read_text())
        assert j["Y_selection_holdout_status"] == "NOT ACCESSED" and len(j["G_all_24_trials"]) == 24 and j["NT_configuration_uncertainty"]["clusters"]
        assert j["markdown_sha256"] == hashlib.sha256((experiment_dir(ws, exp) / "results" / "IS_REPORT.md").read_bytes()).hexdigest()
        assert "(A) choose one configuration directly" in md and "selection holdout" in md.lower()
        rec = j["Y_selection_holdout_recommendation"]
        assert rec["available"] and rec["recommended"] and set(rec["clusters"]) == {"NEAR_TIE_CLUSTER_01", "NEAR_TIE_CLUSTER_02"}
        assert "Selection holdout available: **YES**; recommended: **YES**" in md

    def test_poisoning_every_row_after_development_leaves_is_artifacts_identical(self, near_life, tmp_path):
        """The holdout and lockbox rows (>= development_end) are wrecked in the data: IS results, trials, near-tie analysis and CV panels do not change."""
        ws0, exp0, tables0 = near_life
        events, features, eligible, targets, cal = tables0
        late = np.asarray(pd.DatetimeIndex(events["event_time"]) >= pd.Timestamp("2020-01-01", tz="UTC"))
        feats = features.copy()
        cols = [c for c in feats.columns if c not in ("event_id", "feature_asof_time")]
        feats.loc[late, cols] = 9e9
        tg = {k: v.copy() for k, v in targets.items()}
        for k in tg:
            tg[k].loc[np.asarray(pd.DatetimeIndex(tg[k]["target_start"]) >= pd.Timestamp("2020-01-01", tz="UTC")), "value"] = 9e9
        poisoned = (events, feats, eligible, tg, cal)
        ws = reg.Workspace(tmp_path / "p").init()
        from tests.scenario_helpers import prepare_for_approval, run_is_tables
        exp, trials, _ = run_is_tables(ws, poisoned, partitions=LIFE_PARTS)
        prepare_for_approval(ws, exp)
        a, b = experiment_dir(ws0, exp0) / "results", experiment_dir(ws, exp) / "results"
        assert (a / "results.json").read_bytes() == (b / "results.json").read_bytes()                             # the whole IS result bundle, byte for byte
        for f in sorted(a.glob("cv_*.csv")):
            assert f.read_bytes() == (b / f.name).read_bytes(), f.name
        ja = json.loads((a / "IS_REPORT.json").read_text())
        jb = json.loads((b / "IS_REPORT.json").read_text())
        for k in ("G_all_24_trials", "I_top_configurations", "NT_configuration_uncertainty", "K_calendar_years", "L_development_cv_folds", "J_model_agreement"):
            strip = lambda o: json.loads(re.sub(r'"(registered_at|revealed_at|manifest_hash|trial_ledger_hash)": "[^"]*"', r'"\1": ""', json.dumps(o, sort_keys=True)))  # noqa: E731
            assert strip(ja[k]) == strip(jb[k]), k


# ============================================================ the human gate for opening the selection holdout
class TestHumanGateAndCampaignFreeze:
    # 9. selection holdout requires human approval
    def test_selection_holdout_cannot_run_without_a_human_approval_file(self, near_life, tmp_path):
        ws = clone(near_life[0], tmp_path)
        exp = near_life[1]
        assert not approval_path(ws, exp).exists()
        with pytest.raises(ApprovalError, match="no human approval file"):
            validate_approval(ws, exp)
        cid = reg.experiment_row(ws, exp)["campaign_id"]
        p = subprocess.run([sys.executable, str(CODE_ROOT / "scripts/run_campaign_selection_holdout.py"), "--campaign", cid, "--data", "/nonexistent.parquet",
                            "--workspace", str(ws.root)], capture_output=True, text=True)
        assert p.returncode != 0 and "must first be frozen" in (p.stderr + p.stdout)                           # refused BEFORE any data is read
        assert not reg.selection_holdout_spent(ws, exp) and reg.read_selection_holdout_access(ws).empty
        with pytest.raises(EngineError, match="nothing to freeze"):
            freeze_campaign_selection_holdout(ws, cid)
        assert reg.campaign_row(ws, cid)["status"] == "OPEN"

    def test_the_scripts_never_generate_any_human_file(self, near_life, tmp_path):
        ws = clone(near_life[0], tmp_path)
        exp = near_life[1]
        for script in ("show_approval_hashes.py", "make_report.py", "campaign_status.py"):
            args = [sys.executable, str(CODE_ROOT / "scripts" / script), "--workspace", str(ws.root)]
            if script != "campaign_status.py":
                args += ["--experiment", exp]
            subprocess.run(args, capture_output=True, text=True)
        assert not list(ws.approvals.glob("*"))

    def test_a_config_without_a_near_tie_cannot_be_proposed_for_the_holdout(self, clear_life, tmp_path):
        ws = clone(clear_life[0], tmp_path)
        exp = clear_life[1]
        human_approval(ws, exp, [f"{exp}|{top_group_ids(ws, exp)[0]}"], near_tie_cluster_id="NEAR_TIE_CLUSTER_01")
        with pytest.raises(ApprovalError, match="not NEAR_TIE_REVIEW_REQUIRED"):
            validate_approval(ws, exp)

    @pytest.mark.parametrize("name,override,needle", [
        ("wrong_is_hash", {"is_report_sha256": "0" * 64}, "is_report_sha256 does not match"),
        ("wrong_manifest_hash", {"manifest_sha256": "f" * 64}, "manifest_sha256 does not match"),
        ("not_human", {"approved_by": "CLAUDE"}, "approved_by must be exactly HUMAN_USER"),
        ("approved_not_bool", {"approved": "yes"}, "approved must be the boolean true"),
        ("empty_note", {"approval_note": "  "}, "approval_note must be non-empty"),
        ("wrong_experiment", {"experiment_id": "EXP_9999"}, "experiment_id mismatch"),
        ("wrong_campaign", {"campaign_id": "C999"}, "campaign_id mismatch"),
        ("no_configs", {"approved_configs": []}, "non-empty list"),
        ("duplicate", {"approved_configs": ["X", "X"]}, "duplicate approved configs"),
        ("unknown_cluster", {"near_tie_cluster_id": "NEAR_TIE_CLUSTER_99"}, "does not exist"),
        ("config_of_other_experiment", {"approved_configs": ["EXP_9999|DIR_RETURN_15|LOWER_HALF", "EXP_9999|DIR_RETURN_60|LOWER_HALF"]}, "not one of the top-2"),
        ("only_one_of_the_pair", {"__one": True}, "approved_configs must be exactly"),
    ])
    def test_invalid_approval_files_are_refused(self, near_life, tmp_path, name, override, needle):
        ws = clone(near_life[0], tmp_path, name)
        exp = near_life[1]
        cfgs = proposable(ws, exp, 0)
        if override.pop("__one", False):
            cfgs = cfgs[:1]
        cfgs = override.pop("approved_configs", cfgs)
        override.setdefault("near_tie_cluster_id", "NEAR_TIE_CLUSTER_01")
        human_approval(ws, exp, cfgs, **override)
        with pytest.raises(ApprovalError, match=needle):
            validate_approval(ws, exp)
        assert not reg.selection_holdout_spent(ws, exp)

    def test_human_declining_is_recorded_and_opens_nothing(self, near_life, tmp_path):
        ws = clone(near_life[0], tmp_path)
        exp = near_life[1]
        human_approval(ws, exp, proposable(ws, exp, 0), approved=False)
        with pytest.raises(ApprovalError, match="HUMAN_DECLINED"):
            validate_approval(ws, exp)
        assert reg.experiment_row(ws, exp)["status"] == "HUMAN_DECLINED" and not reg.selection_holdout_spent(ws, exp)

    def test_valid_approval_binds_the_exact_hashes_and_the_proposed_cluster(self, near_life, tmp_path):
        ws = clone(near_life[0], tmp_path)
        exp = near_life[1]
        cfgs = proposable(ws, exp, 0)
        human_approval(ws, exp, cfgs)
        ap = validate_approval(ws, exp)
        h = approval_hashes(ws, exp)
        assert ap["manifest_sha256"] == h["manifest_sha256"] and ap["is_report_sha256"] == h["is_report_sha256"]
        assert ap["approved_configs"] == cfgs and ap["near_tie_cluster_id"] == "NEAR_TIE_CLUSTER_01"
        assert {c["cluster_id"] for c in h["near_tie_clusters"]} == {"NEAR_TIE_CLUSTER_01", "NEAR_TIE_CLUSTER_02"}

    def test_changed_event_spec_frozen_specs_partitions_or_is_results_invalidate_the_approval(self, near_life, tmp_path):
        import engine.experiment_lifecycle as lc
        exp = near_life[1]

        def fresh(name):
            ws = clone(near_life[0], tmp_path, name)
            human_approval(ws, exp, proposable(ws, exp, 0))
            validate_approval(ws, exp)                                                                        # valid before the change
            return ws, experiment_dir(ws, exp)
        ws, d = fresh("event")
        os.chmod(d / "event.py", 0o644)
        (d / "event.py").write_text((d / "event.py").read_text() + "\n# tweak\n")
        with pytest.raises(ApprovalError, match="event.py changed after freeze"):
            validate_approval(ws, exp)
        ws, d = fresh("spec")
        os.chmod(d / "EVENT_SPEC.yaml", 0o644)
        (d / "EVENT_SPEC.yaml").write_text((d / "EVENT_SPEC.yaml").read_text().replace("pivot_left: 30", "pivot_left: 31", 1))
        with pytest.raises(ApprovalError, match="EVENT_SPEC.yaml changed after freeze"):
            validate_approval(ws, exp)
        ws, d = fresh("partitions")                                                                           # a partition boundary moved (still a legal 1-year holdout)
        os.chmod(d / "EVENT_SPEC.yaml", 0o644)
        txt = (d / "EVENT_SPEC.yaml").read_text().replace('development_end: "2020-01-01"', 'development_end: "2019-01-01"')
        (d / "EVENT_SPEC.yaml").write_text(txt.replace('selection_holdout_end: "2021-01-01"', 'selection_holdout_end: "2020-01-01"').replace('lockbox_start: "2021-01-01"', 'lockbox_start: "2020-01-01"'))
        with pytest.raises(ApprovalError, match="partitions changed after freeze"):
            validate_approval(ws, exp)
        ws, d = fresh("frozen")
        real = lc.sha256_file
        from pathlib import Path
        mp = pytest.MonkeyPatch()
        mp.setattr(lc, "sha256_file", lambda p: "0" * 64 if Path(p).name == "SELECTION_PROCESS.yaml" else real(p))      # the NEW frozen spec is hashed too
        try:
            with pytest.raises(ApprovalError, match="frozen specification changed after freeze"):
                validate_approval(ws, exp)
        finally:
            mp.undo()
        ws, d = fresh("results")
        (d / "results" / "results.json").write_text((d / "results" / "results.json").read_text().replace('"experiment_id"', '"experiment_id" ', 1))
        with pytest.raises(ApprovalError, match="IS results.json changed"):
            validate_approval(ws, exp)
        ws, d = fresh("report_md")
        (d / "results" / "IS_REPORT.md").write_text((d / "results" / "IS_REPORT.md").read_text() + "\nI looked at the holdout.\n")
        with pytest.raises(ApprovalError, match="IS_REPORT.md was edited"):
            validate_approval(ws, exp)
        ws, d = fresh("new_report")
        reg.set_verification(ws, exp, {"DIR_RETURN_15|XGB": {"label": "FAILED", "mode": "strong"}}, "FAILED", F)
        write_is_report(ws, exp)
        with pytest.raises(ApprovalError):
            validate_approval(ws, exp)                                                                        # a regenerated report has a different hash

    def test_unverified_model_path_blocks_the_unlock(self, near_life, tmp_path):
        ws = clone(near_life[0], tmp_path)
        exp = near_life[1]
        ver = json.loads(reg.experiment_row(ws, exp)["verification_json"])
        ver["DIR_RETURN_15|XGB"] = {"label": "RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE", "mode": "fast"}      # not strong -> not final
        reg.update_experiment(ws, exp, verification_json=json.dumps(ver))
        write_is_report(ws, exp)
        human_approval(ws, exp, proposable(ws, exp, 0))
        with pytest.raises(ApprovalError, match="not externally verified"):
            validate_approval(ws, exp)

    # 10. both configs are frozen before any holdout data is read
    def test_both_configs_are_frozen_together_before_any_holdout_byte_is_read(self, near_life, tmp_path):
        ws = clone(near_life[0], tmp_path)
        exp = near_life[1]
        cfgs = proposable(ws, exp, 0)
        human_approval(ws, exp, cfgs)
        fz = freeze_campaign_selection_holdout(ws, "C001")                                                    # no table / bar is passed to the freeze at all
        assert fz["approved_config_ids"] == cfgs and fz["n_approved_configs"] == 2 and fz["n_holdout_evaluations"] == 6
        assert fz["selection_holdout_years"] == 1 and fz["partitions"] == LIFE_PARTS and len(fz["partitions_hash"]) == 64
        e0 = fz["experiments"][0]
        assert e0["near_tie_cluster_id"] == "NEAR_TIE_CLUSTER_01" and len(e0["manifest_sha256"]) == 64 and len(e0["approval_file_sha256"]) == 64
        assert reg.experiment_row(ws, exp)["status"] == "SELECTION_HOLDOUT_FROZEN" and reg.campaign_row(ws, "C001")["status"] == "SELECTION_HOLDOUT_FROZEN"
        assert reg.read_selection_holdout_access(ws).empty and not reg.selection_holdout_spent(ws, exp)       # nothing has been opened yet
        assert not (experiment_dir(ws, exp) / "results" / "SELECTION_HOLDOUT_REPORT.json").exists()
        with pytest.raises(EngineError):
            reg.register_experiment(ws, "C001")                                                               # the frozen campaign is closed

    # 12. the ledger row is written BEFORE any holdout data is analysed; no sequential look-then-decide
    def test_the_holdout_is_spent_before_data_is_analysed_so_nothing_can_be_retried(self, near_life, tmp_path):
        ws = clone(near_life[0], tmp_path)
        exp = near_life[1]
        human_approval(ws, exp, proposable(ws, exp, 0))
        freeze_campaign_selection_holdout(ws, "C001")
        campaign_open_approval(ws, "C001")
        from engine.selection_holdout_stage import execute_campaign_selection_holdout
        doc, cap, aps = validate_campaign_open(ws, "C001")

        def boom():
            raise RuntimeError("holdout data was touched")
        with pytest.raises(RuntimeError, match="touched"):
            execute_campaign_selection_holdout(ws, "C001", cap, [(exp, aps[exp], boom, pd.DatetimeIndex([]), None)], "fp", verbose=False)
        led = reg.read_selection_holdout_access(ws)
        assert len(led) == 1 and reg.campaign_row(ws, "C001")["status"] == "SELECTION_HOLDOUT_SPENT"            # spent although the evaluation died: no do-over
        assert reg.read_selection_holdout_trials(ws).empty
        with pytest.raises(SelectionHoldoutContaminated, match="CAMPAIGN SELECTION HOLDOUT HAS BEEN SPENT"):
            validate_campaign_open(ws, "C001")

    def test_nothing_opens_without_the_human_campaign_open_approval(self, near_life, tmp_path):
        ws = clone(near_life[0], tmp_path)
        exp = near_life[1]
        human_approval(ws, exp, proposable(ws, exp, 0))
        fz = freeze_campaign_selection_holdout(ws, "C001")
        with pytest.raises(ApprovalError, match="no human campaign-open approval file"):
            validate_campaign_open(ws, "C001")
        campaign_open_approval(ws, "C001", selection_holdout_freeze_sha256="0" * 64)
        with pytest.raises(ApprovalError, match="does not match the exact campaign freeze"):
            validate_campaign_open(ws, "C001")
        campaign_open_approval(ws, "C001", approved_by="CLAUDE")
        with pytest.raises(ApprovalError, match="HUMAN_USER"):
            validate_campaign_open(ws, "C001")
        campaign_open_approval(ws, "C001")
        assert validate_campaign_open(ws, "C001")[1]["_file_sha256"] and fz["freeze_sha256"] == reg.campaign_row(ws, "C001")["selection_holdout_freeze_hash"]

    def test_adding_or_swapping_a_config_after_the_freeze_is_refused(self, near_life, tmp_path):
        ws = clone(near_life[0], tmp_path)
        exp = near_life[1]
        cfgs = proposable(ws, exp, 0)
        human_approval(ws, exp, cfgs)
        freeze_campaign_selection_holdout(ws, "C001")
        campaign_open_approval(ws, "C001")
        human_approval(ws, exp, cfgs[:1])                                                                     # a later edit of the human file cannot change the frozen set
        with pytest.raises(ApprovalError, match="changed since the campaign freeze|approved_configs must be exactly"):
            validate_campaign_open(ws, "C001")

    def test_the_freeze_document_cannot_be_edited_after_the_freeze(self, near_life, tmp_path):
        ws = clone(near_life[0], tmp_path)
        exp = near_life[1]
        human_approval(ws, exp, proposable(ws, exp, 0))
        freeze_campaign_selection_holdout(ws, "C001")
        campaign_open_approval(ws, "C001")
        p = freeze_path(ws, "C001")
        doc = json.loads(p.read_text())
        doc["approved_config_ids"].append("EXP_0001|DIR_RETURN_180|UPPER_HALF")
        p.write_text(json.dumps(doc, indent=2, sort_keys=True))
        with pytest.raises(ApprovalError, match="missing or was edited"):
            validate_campaign_open(ws, "C001")


# ============================================================ the one-shot campaign selection holdout (near-tie pair, 6 evaluations)
class TestSelectionHoldoutOpening:
    def test_the_ledger_records_the_one_opening_with_every_frozen_config(self, spent_b):
        ws, exp, tables, cfgs, rep = spent_b
        led = reg.read_selection_holdout_access(ws)
        assert len(led) == 1 and reg.verify_selection_holdout_ledger(ws) == 1
        row = led.iloc[0]
        assert row["campaign_id"] == "C001" and row["experiments"] == exp and row["approved_experiment_groups"] == ";".join(cfgs) and row["n_holdout_evaluations"] == "6"
        assert row["selection_holdout_start"] == "2020-01-01" and row["selection_holdout_end"] == "2021-01-01"
        assert row["freeze_hash"] == reg.campaign_row(ws, "C001")["selection_holdout_freeze_hash"] and len(row["code_hash"]) == 64 and row["unlock_timestamp"]
        assert reg.campaign_row(ws, "C001")["status"] == "SELECTION_HOLDOUT_SPENT" and reg.experiment_row(ws, exp)["status"] == "SELECTION_HOLDOUT_SPENT"
        assert not any(w in " ".join(history(ws, exp)) for w in ("OOS", "CONFIRMED"))                         # no misleading status was ever displayed

    # 11. both configs use exactly the same holdout interval
    def test_both_configs_are_evaluated_on_exactly_the_same_holdout_interval(self, spent_b):
        ws, exp, tables, cfgs, rep = spent_b
        assert rep["selection_holdout_period"] == ["2020-01-01", "2021-01-01"] and rep["selection_holdout_years"] == 1
        ev = rep["evaluations"]
        assert {e["group_id"] for e in ev} == {c.split("|", 1)[1] for c in cfgs} and len({e["selection_holdout_weeks"] for e in ev}) == 1
        assert all(e["model"] in ("RIDGE", "SPLINE", "XGB") for e in ev) and len(ev) == 6
        assert rep["holdout_model_evaluations"] == 6 and rep["campaign_experiments_in_family"] == [exp]

    # 12. no sequential A-then-B: one opening, one family
    def test_there_is_no_sequential_a_then_b_opening(self, spent_b):
        ws, exp, tables, cfgs, rep = spent_b
        with pytest.raises(SelectionHoldoutContaminated, match="CAMPAIGN SELECTION HOLDOUT HAS BEEN SPENT"):
            validate_campaign_open(ws, "C001")
        with pytest.raises(SelectionHoldoutContaminated, match="CAMPAIGN SELECTION HOLDOUT HAS BEEN SPENT"):
            validate_approval(ws, exp)
        with pytest.raises(EngineError, match="CAMPAIGN SELECTION HOLDOUT HAS BEEN SPENT"):
            reg.append_selection_holdout_access(ws, campaign_id="C001")
        assert len(reg.read_selection_holdout_access(ws)) == 1
        rows = reg.read_selection_holdout_trials(ws)
        assert len(set(rows["revealed_at"])) == 1                                                            # all six evaluations revealed in the same opening

    # 14. multiplicity includes every model of every config, losers included
    def test_selection_holdout_multiplicity_covers_every_config_and_model(self, spent_b):
        ws, exp, tables, cfgs, rep = spent_b
        rows = reg.read_selection_holdout_trials(ws)
        assert len(rows) == 6 == rep["family_size_for_multiple_testing"] and (rows["selection_holdout_trials_in_family"].astype(int) == 6).all()
        p = rows["raw_p"].astype(float).to_numpy()
        assert np.allclose(rows["selection_holdout_bonferroni_p"].astype(float), np.minimum(p * 6, 1.0))
        assert np.allclose(rows["selection_holdout_q"].astype(float), benjamini_hochberg(p))
        assert (rows.groupby("group_id").size() == 3).all() and set(rows["model"]) == {"RIDGE", "SPLINE", "XGB"}
        assert "ENTIRE CAMPAIGN" in rep["scope_of_multiplicity"] and "min(raw_p * 6, 1)" in rep["formulas"]["selection_holdout_bonferroni_p"]
        up = {c: np.median([r["standardized_uplift"] for r in rep["evaluations"] if r["group_id"] == c.split("|", 1)[1]]) for c in cfgs}
        assert up[cfgs[0]] < up[cfgs[1]]                                                                     # the weakened (losing) config's evaluations are in the family too, not only the winner's

    def test_the_holdout_report_has_year_and_month_breakdowns_for_every_config_and_model(self, spent_b):
        ws, exp, tables, cfgs, rep = spent_b
        assert len(rep["by_year"]) == len(rep["by_month"]) == 6                                              # 2 configs x 3 models
        for k, rows in rep["by_year"].items():
            assert rows and all(r["year"] == "2020" for r in rows) and all("mean_directional_effect" in r for r in rows)
        assert all(r["month"].startswith("2020-") for rows in rep["by_month"].values() for r in rows)
        assert "by year" in (experiment_dir(ws, exp) / "results" / "SELECTION_HOLDOUT_REPORT.md").read_text()

    # 15. the report is labelled selection data, never confirmation
    def test_the_holdout_report_is_labelled_selection_data_not_confirmation(self, spent_b):
        ws, exp, tables, cfgs, rep = spent_b
        banner = "SELECTION DATA — USED TO CHOOSE FINAL CONFIGURATION / NOT FINAL CONFIRMATION"
        md = (experiment_dir(ws, exp) / "results" / "SELECTION_HOLDOUT_REPORT.md").read_text()
        assert rep["label"] == banner and md.count(banner) >= 2 and md.startswith("# SELECTION HOLDOUT REPORT")
        assert rep["is_independent_confirmation"] is False and "NOT confirmation p-values" in md and "selection-holdout evidence" in md
        assert "HOLDOUT_PREFERRED_CONFIG" in md and "ADVISORY" in md and "Only the untouched final lockbox may be called confirmation" in md
        for col in ("selection_holdout_q", "selection_holdout_bonferroni_p", "raw_p"):
            assert col in rep["evaluations"][0]
        assert not re.search(r"\bOOS\b|OOS_CONFIRMED|CONFIRMED", md)

    def test_is_report_is_sealed_after_the_holdout(self, spent_b):
        ws, exp, *_ = spent_b
        assert "SPENT" in selection_holdout_status_label(ws, exp) and selection_holdout_status_label(ws, exp) != NOT_ACCESSED
        with pytest.raises(ReportSealedError):
            write_is_report(ws, exp)

    def test_changing_the_experiment_after_the_holdout_marks_it_contaminated(self, spent_b, tmp_path):
        ws = clone(spent_b[0], tmp_path)
        exp = spent_b[1]
        assert mark_contamination_if_mutated(ws, exp) is False
        d = experiment_dir(ws, exp)
        os.chmod(d / "event.py", 0o644)
        (d / "event.py").write_text((d / "event.py").read_text() + "\n# after seeing the holdout\n")
        assert mark_contamination_if_mutated(ws, exp) is True and reg.experiment_row(ws, exp)["status"] == "SELECTION_HOLDOUT_CONTAMINATED"
        with pytest.raises(EngineError, match="SELECTION_HOLDOUT_CONTAMINATED"):
            C.precheck_cpcv(ws, exp)

    def test_lineage_child_cannot_claim_the_spent_holdout_untouched(self, spent_b):
        ws, exp, *_ = spent_b
        with pytest.raises(SelectionHoldoutContaminated, match="CAMPAIGN SELECTION HOLDOUT HAS BEEN SPENT"):
            reg.register_experiment(ws, "C001", lineage_parent=exp)

    # 30. holdout evidence cannot create a new config
    def test_the_holdout_only_evaluates_configs_frozen_before_it_opened(self, spent_b):
        ws, exp, tables, cfgs, rep = spent_b
        assert rep["approved_configs"] == cfgs
        assert {f"{exp}|{e['group_id']}" for e in rep["evaluations"]} == set(cfgs)
        assert set(rep["preference"]["ranking"]) <= set(cfgs) and set(c["config_id"] for c in rep["preference"]["cards"]) == set(cfgs)
        assert rep["path_diagnostics"]["status"] == "NOT_COMPUTED_NO_BARS"                                    # table-level run: bars are exercised in test_end_to_end_bars

    def test_the_holdout_phase_never_touches_the_final_lockbox(self):
        import inspect

        from engine import cpcv as cpcv_mod
        from engine import selection_holdout_stage
        from engine.partitions import parse_partitions, selection_holdout_view
        parts = parse_partitions(LIFE_PARTS)
        idx = pd.date_range("2019-06-01", "2021-03-01", freq="1D", tz="UTC")
        bars = pd.DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0}, index=idx)
        poisoned = bars.copy()
        poisoned.loc[poisoned.index >= parts.lockbox_start, ["open", "high", "low", "close"]] = 9e9
        a, b = selection_holdout_view(bars, parts), selection_holdout_view(poisoned, parts)
        assert a.equals(b) and a.index.max() < parts.selection_holdout_end                                       # lockbox poison is invisible
        for fn, later in ((selection_holdout_stage.run_campaign_selection_holdout, ("build_event_tables(", "execute_campaign_selection_holdout(")),
                          (cpcv_mod.run_cpcv, ("build_event_tables(", "execute_cpcv("))):
            src = inspect.getsource(fn)
            cut = src.index("_view(bars")
            assert all(src.index(tok) > cut for tok in later if tok in src), fn.__name__
            assert "del bars" in src[cut:], fn.__name__                                                          # the uncut frame is dropped immediately


# ============================================================ preference: advisory, deterministic, never fabricated
class TestHoldoutPreference:
    def test_one_config_clearly_preferred_when_the_holdout_separates_them(self, spent_b):
        ws, exp, tables, cfgs, rep = spent_b
        p = rep["preference"]
        assert p["status"] == "HOLDOUT_PREFERRED_CONFIG" and p["holdout_preferred_config"] == cfgs[1]
        assert p["ranking"][0] == p["holdout_preferred_config"] and all(c["qualifies"] for c in p["cards"])
        assert p["pair_test"]["abs_diff"] > 0.03 and "ADVISORY" in p["note"]
        assert {c["config_id"] for c in p["cards"]} == set(cfgs)                                                # the 15 config (60 lost half its effect) is the preferred one

    def test_close_configs_remain_unresolved_and_no_winner_is_fabricated(self, near_life, tmp_path):
        ws = clone(near_life[0], tmp_path)
        exp = near_life[1]
        cfgs = proposable(ws, exp, 0)
        human_approval(ws, exp, cfgs)
        rep = spend_selection_holdout(ws, exp, near_life[2])
        p = rep["preference"]
        assert p["status"] == "HOLDOUT_UNRESOLVED" and p["holdout_preferred_config"] is None and p["pair_test"]["ci_contains_zero"] and p["pair_test"]["abs_diff"] <= 0.03
        assert "no winner is fabricated" in p["note"] and p["ranking_leader_advisory"] in cfgs
        md = (experiment_dir(ws, exp) / "results" / "SELECTION_HOLDOUT_REPORT.md").read_text()
        assert "HOLDOUT_UNRESOLVED" in md
        # the human may still choose one of the frozen configs (or decline): the engine accepts either, neither is made for them
        human_final_selection(ws, exp, cfgs[0])
        info = freeze_final_config(ws, exp)
        assert info["selected_config_id"] == cfgs[0] and reg.experiment_row(ws, exp)["status"] == "FINAL_CONFIG_FROZEN"
        ws2 = clone(near_life[0], tmp_path, "decl")
        human_approval(ws2, exp, cfgs)
        spend_selection_holdout(ws2, exp, near_life[2])
        human_final_selection(ws2, exp, "DECLINE")
        assert freeze_final_config(ws2, exp)["decline"] and reg.experiment_row(ws2, exp)["status"] == "HUMAN_DECLINED"

    def test_the_preference_rule_is_the_frozen_order(self):
        from engine.holdout_preference import holdout_preference

        def cfg(cid, rank, up, eff, freq, pos=3):
            rows = [{"model": m, "standardized_uplift": up, "selected_effect": eff, "selected_frequency": freq, "uplift": 0.1 if i < pos else -0.1}
                    for i, m in enumerate(("RIDGE", "SPLINE", "XGB"))]
            return {"config_id": cid, "is_rank": rank, "model_rows": rows}
        out = holdout_preference([cfg("B", 2, 0.30, 0.2, 2.0), cfg("A", 1, 0.20, 0.5, 5.0)], F)                  # no series: pairwise test skipped -> pure ranking
        assert out["ranking"] == ["B", "A"] and out["holdout_preferred_config"] == "B"                           # 1. median std uplift DESC dominates
        out = holdout_preference([cfg("B", 2, 0.30, 0.2, 2.0), cfg("A", 1, 0.30, 0.5, 1.0)], F)
        assert out["ranking"] == ["A", "B"]                                                                    # 2. then selected effect DESC
        out = holdout_preference([cfg("B", 2, 0.30, 0.5, 2.0), cfg("A", 1, 0.30, 0.5, 1.5)], F)
        assert out["ranking"] == ["B", "A"]                                                                    # 3. then frequency DESC
        out = holdout_preference([cfg("B", 2, 0.30, 0.5, 2.0), cfg("A", 1, 0.30, 0.5, 2.0)], F)
        assert out["ranking"] == ["A", "B"]                                                                    # 4. then frozen IS rank ASC
        out = holdout_preference([cfg("Z", 1, 0.30, 0.5, 2.0), cfg("A", 1, 0.30, 0.5, 2.0)], F)
        assert out["ranking"] == ["A", "Z"]                                                                    # 5. then config id ASC
        out = holdout_preference([cfg("A", 1, 0.9, 0.9, 9.0, pos=1), cfg("B", 2, 0.1, 0.1, 1.0)], F)           # requirement: >= 2 of 3 models with positive uplift
        assert out["ranking"] == ["B"] and out["cards"][0]["qualifies"] is False
        out = holdout_preference([cfg("A", 1, 0.9, 0.9, 0.5)], F)                                              # requirement: frequency >= 1/week
        assert out["status"] == "NO_QUALIFYING_CONFIG" and out["holdout_preferred_config"] is None
        out = holdout_preference([cfg("A", 1, 0.9, -0.1, 3.0)], F)                                             # requirement: selected effect > 0
        assert out["status"] == "NO_QUALIFYING_CONFIG"


# ============================================================ the human's final configuration choice
class TestFinalConfigSelection:
    # 16. the human final-selection file is required after the holdout
    def test_a_final_config_selection_file_is_required_after_the_holdout(self, spent_b, tmp_path):
        ws = clone(spent_b[0], tmp_path)
        exp = spent_b[1]
        assert not final_selection_path(ws, exp).exists()
        with pytest.raises(ApprovalError, match="no human final-configuration selection file"):
            freeze_final_config(ws, exp)
        with pytest.raises(EngineError, match="CPCV runs only for FINAL_CONFIG_FROZEN"):
            C.precheck_cpcv(ws, exp)                                                                           # and without it CPCV cannot start
        assert reg.read_final_configs(ws).empty
        p = subprocess.run([sys.executable, str(CODE_ROOT / "scripts/finalize_final_config.py"), "--experiment", exp, "--data", "/nonexistent.parquet",
                            "--workspace", str(ws.root)], capture_output=True, text=True)
        assert p.returncode != 0 and "no human final-configuration selection file" in (p.stderr + p.stdout)

    # 17. exactly one final config
    @pytest.mark.parametrize("bad", ["list", "two_in_string", "empty", "no_pipe", "none"])
    def test_exactly_one_config_can_be_selected(self, spent_b, tmp_path, bad):
        ws = clone(spent_b[0], tmp_path)
        exp, cfgs = spent_b[1], spent_b[3]
        value = {"list": list(cfgs), "two_in_string": f"{cfgs[0]},{cfgs[1]}", "empty": "", "no_pipe": "DIR_RETURN_15", "none": None}[bad]
        human_final_selection(ws, exp, value)
        with pytest.raises(ApprovalError):
            validate_final_selection(ws, exp)
        assert reg.read_final_configs(ws).empty and reg.experiment_row(ws, exp)["status"] == "SELECTION_HOLDOUT_SPENT"

    # 18. must have been evaluated in the holdout (and frozen before it)
    def test_the_final_config_must_have_been_frozen_and_evaluated_in_the_holdout(self, spent_b, tmp_path):
        ws = clone(spent_b[0], tmp_path)
        exp, cfgs = spent_b[1], spent_b[3]
        side = cfgs[0].rsplit("|", 1)[1]
        opposite = "LOWER_HALF" if side == "UPPER_HALF" else "UPPER_HALF"
        for other in (f"{exp}|DIR_RETURN_15|{opposite}", f"{exp}|DIR_RETURN_60|{opposite}", f"{exp}|DIR_RETURN_180|{side}"):          # IS-eligible or not: never evaluated
            human_final_selection(ws, exp, other)
            with pytest.raises(ApprovalError, match="was not evaluated in the selection holdout"):
                validate_final_selection(ws, exp)
        assert reg.read_final_configs(ws).empty

    @pytest.mark.parametrize("name,override,needle", [
        ("wrong_is_hash", {"is_report_sha256": "0" * 64}, "is_report_sha256 does not match"),
        ("wrong_manifest", {"manifest_sha256": "f" * 64}, "manifest_sha256 does not match"),
        ("wrong_holdout_hash", {"selection_holdout_report_sha256": "a" * 64}, "selection_holdout_report_sha256 does not match"),
        ("skipped_marker_but_spent", {"selection_holdout_report_sha256": None}, "selection_holdout_report_sha256 does not match"),
        ("not_human", {"selected_by": "CLAUDE"}, "selected_by must be exactly HUMAN_USER"),
        ("empty_note", {"selection_note": " "}, "selection_note must be non-empty"),
        ("wrong_campaign", {"campaign_id": "C999"}, "campaign_id mismatch"),
        ("wrong_experiment", {"experiment_id": "EXP_9999"}, "experiment_id mismatch"),
    ])
    def test_invalid_final_selection_files_are_refused(self, spent_b, tmp_path, name, override, needle):
        ws = clone(spent_b[0], tmp_path, name)
        exp, cfgs = spent_b[1], spent_b[3]
        human_final_selection(ws, exp, cfgs[1], **override)
        with pytest.raises(ApprovalError, match=needle):
            validate_final_selection(ws, exp)
        assert reg.read_final_configs(ws).empty

    def test_a_valid_final_selection_freezes_exactly_one_config_and_writes_the_ledger(self, spent_b, tmp_path):
        ws = clone(spent_b[0], tmp_path)
        exp, cfgs = spent_b[1], spent_b[3]
        p = human_final_selection(ws, exp, cfgs[1])
        info = freeze_final_config(ws, exp)
        assert info["selected_config_id"] == cfgs[1] and info["holdout_used"] and info["holdout_rank"] == "1"
        assert reg.experiment_row(ws, exp)["status"] == "FINAL_CONFIG_FROZEN"
        led = reg.read_final_configs(ws)
        assert len(led) == 1 and reg.verify_final_config_ledger(ws) == 1
        row = led.iloc[0]
        assert row["event"] == "FINAL_CONFIG_FROZEN" and row["selected_config_id"] == cfgs[1] and row["selection_holdout_used"] == "yes" and row["cpcv_status"] == "PENDING"
        assert row["is_rank"] == str(next(c["is_rank"] for c in spent_b[4]["preference"]["cards"] if c["config_id"] == cfgs[1])) and row["near_tie_cluster"] == "NEAR_TIE_CLUSTER_01" and row["selection_holdout_rank"] == "1"
        assert row["human_selection_file_hash"] == hashlib.sha256(p.read_bytes()).hexdigest() and len(row["manifest_hash"]) == 64 and row["frozen_at"]
        # there can only ever be ONE final config: a second selection (the runner-up, or the same one again) is refused
        human_final_selection(ws, exp, cfgs[0])
        with pytest.raises(ApprovalError, match="already froze its final configuration"):
            freeze_final_config(ws, exp)
        assert len(reg.read_final_configs(ws)) == 1 and reg.experiment_row(ws, exp)["status"] == "FINAL_CONFIG_FROZEN"

    def test_the_final_config_ledger_is_append_only_and_integrity_checked(self, spent_b, tmp_path):
        ws = clone(spent_b[0], tmp_path)
        exp, cfgs = spent_b[1], spent_b[3]
        human_final_selection(ws, exp, cfgs[1])
        freeze_final_config(ws, exp)
        path = ws.path("final_configs.csv")
        good = path.read_text()
        path.write_text(good.replace(cfgs[1], cfgs[0], 1))                                                    # swap the final config in the ledger
        with pytest.raises(reg.RegistryIntegrityError, match="final_configs.csv was edited"):
            reg.verify_final_config_ledger(ws)
        with pytest.raises(reg.RegistryIntegrityError):
            reg.integrity_check(ws)
        path.write_text(good)
        assert reg.verify_final_config_ledger(ws) == 1
        with pytest.raises(EngineError, match="CPCV_RESULT needs exactly one prior FINAL_CONFIG_FROZEN"):
            reg.append_final_config(ws, campaign_id="C001", experiment_id="EXP_9999", event="CPCV_RESULT")

    def test_declining_to_choose_ends_the_experiment_with_no_cpcv(self, spent_b, tmp_path):
        ws = clone(spent_b[0], tmp_path)
        exp = spent_b[1]
        human_final_selection(ws, exp, "DECLINE")
        assert freeze_final_config(ws, exp)["decline"] and reg.experiment_row(ws, exp)["status"] == "HUMAN_DECLINED"
        assert reg.read_final_configs(ws).empty and reg.read_cpcv(ws).empty
        with pytest.raises(EngineError, match="CPCV runs only for FINAL_CONFIG_FROZEN"):
            C.precheck_cpcv(ws, exp)


# ============================================================ scenarios A–E (end to end, real CPCV)
@pytest.fixture(scope="module")
def scen_a(clear_life, tmp_path_factory):
    """A — one clearly superior IS config; the human selects it directly; the holdout is skipped; CPCV runs automatically and passes."""
    ws = clone(clear_life[0], tmp_path_factory.mktemp("scen_a"), "ws")
    exp, tables = clear_life[1], clear_life[2]
    cfg = f"{exp}|{top_group_ids(ws, exp)[0]}"
    seen, spy = with_spy()
    mp = pytest.MonkeyPatch()
    mp.setattr(C, "run_cpcv_tables", spy)
    try:
        approvals_before = sorted(p.name for p in ws.approvals.glob("*"))
        human_final_selection(ws, exp, cfg, selection_holdout_report_sha256=None)
        approvals_with_selection = sorted(p.name for p in ws.approvals.glob("*"))
        info = freeze_final_config(ws, exp)
        rep = run_cpcv_stage(ws, exp, tables)                                            # no approval file other than the final selection exists
    finally:
        mp.undo()
    return dict(ws=ws, exp=exp, cfg=cfg, info=info, rep=rep, seen=seen, tables=tables, approvals=(approvals_before, approvals_with_selection))


class TestScenarioA_ClearIsWinnerDirectSelection:
    def test_no_near_tie_and_a_single_clear_config_per_side(self, clear_life):
        ws, exp, _ = clear_life
        rec = json.loads((experiment_dir(ws, exp) / "results" / "IS_REPORT.json").read_text())["Y_selection_holdout_recommendation"]
        assert rec["available"] is False and rec["recommended"] is False and "no near-tie cluster" in rec["reason"]
        assert reg.experiment_row(ws, exp)["status"] == "AWAITING_HUMAN_FINAL_CONFIG_SELECTION"
        assert {g.split("|")[0] for g in top_group_ids(ws, exp)} == {"DIR_RETURN_180"}

    # 19. direct final selection from IS works when the holdout is skipped
    def test_direct_selection_freezes_the_final_config_and_marks_the_holdout_skipped(self, scen_a):
        ws, exp, cfg, info = scen_a["ws"], scen_a["exp"], scen_a["cfg"], scen_a["info"]
        assert info["holdout_used"] is False and info["selected_config_id"] == cfg
        h = history(ws, exp)
        assert h.index("SELECTION_HOLDOUT_SKIPPED") < h.index("FINAL_CONFIG_FROZEN") < h.index("CPCV_CONFIRMED") and h[-1] == "AWAITING_FINAL_LOCKBOX_APPROVAL"
        led = reg.read_final_configs(ws)
        assert list(led["event"]) == ["FINAL_CONFIG_FROZEN", "CPCV_RESULT"] and set(led["selection_holdout_used"]) == {"no"} and led.iloc[0]["selection_holdout_rank"] == ""
        assert led.iloc[1]["cpcv_status"] == "CPCV_CONFIRMED" and reg.verify_final_config_ledger(ws) == 2

    # 20. the unused holdout stays unread
    def test_the_unused_holdout_remains_unread(self, scen_a):
        ws, exp = scen_a["ws"], scen_a["exp"]
        assert reg.read_selection_holdout_access(ws).empty and not reg.selection_holdout_spent(ws, exp)
        assert reg.campaign_row(ws, "C001")["status"] == "OPEN"
        assert not (experiment_dir(ws, exp) / "results" / "SELECTION_HOLDOUT_REPORT.json").exists() and reg.read_selection_holdout_trials(ws).empty

    # 23. CPCV uses development ONLY when the holdout was skipped
    def test_cpcv_uses_development_only_when_the_holdout_was_skipped(self, scen_a):
        seen, ws, exp = scen_a["seen"], scen_a["ws"], scen_a["exp"]
        cutoff, label = C.cpcv_cutoff(ws, exp)
        assert cutoff == pd.Timestamp("2020-01-01", tz="UTC") and "DEVELOPMENT only" in label
        assert seen["max"] < pd.Timestamp("2020-01-01", tz="UTC") and seen["min"] >= pd.Timestamp("2015-01-01", tz="UTC")
        assert scen_a["rep"]["data_used"].startswith("DEVELOPMENT only") and scen_a["rep"]["selection_holdout_used"] is False

    def test_cpcv_script_loads_only_development_rows_when_the_holdout_was_skipped(self, scen_a, monkeypatch, tmp_path):
        import runpy

        import engine.partitions as P
        asked = {}

        def fake_loader(path, cutoff, ts):
            asked["cutoff"] = cutoff
            raise RuntimeError("stop: loader inspected")
        monkeypatch.setattr(P, "load_bars_before", fake_loader)
        ws, exp = clone(scen_a["ws"], tmp_path), scen_a["exp"]
        monkeypatch.setattr(sys, "argv", ["run_cpcv.py", "--experiment", exp, "--data", "unused", "--workspace", str(ws.root)])
        monkeypatch.syspath_prepend(str(CODE_ROOT / "scripts"))
        with pytest.raises(RuntimeError, match="loader inspected"):
            runpy.run_path(str(CODE_ROOT / "scripts/run_cpcv.py"), run_name="__main__")
        assert asked["cutoff"] == pd.Timestamp("2020-01-01", tz="UTC")                                 # the holdout and lockbox rows are never even loaded

    # 21. CPCV starts without a separate human approval
    def test_cpcv_ran_with_no_approval_other_than_the_final_config_selection(self, scen_a):
        before, with_sel = scen_a["approvals"]
        assert before == [] and with_sel == [f"{scen_a['exp']}_FINAL_CONFIG_SELECTION.yaml"]
        assert not any("CPCV" in p.name for p in scen_a["ws"].approvals.glob("*"))
        assert scen_a["rep"]["n_splits"] == 15

    # 24. CPCV cannot change the final config
    def test_cpcv_evaluates_only_the_frozen_config_and_changes_nothing_about_it(self, scen_a):
        rep, cfg, ws, exp = scen_a["rep"], scen_a["cfg"], scen_a["ws"], scen_a["exp"]
        group = cfg.split("|", 1)[1]
        assert rep["final_config_id"] == cfg and list(rep["group_verdicts"]) == [group] and scen_a["seen"]["groups"] == [group]
        assert {k.rsplit("|", 1)[0] for k in rep["summary"]} == {group} and {k.rsplit("|", 1)[1] for k in rep["summary"]} == {"RIDGE", "SPLINE", "XGB"}
        led = reg.read_final_configs(ws)
        assert set(led["selected_config_id"]) == {cfg}
        assert set(reg.read_cpcv(ws)["group_id"]) == {group}

    # 27. a pass reaches AWAITING_FINAL_LOCKBOX_APPROVAL; labelled as post-selection robustness
    def test_cpcv_pass_reaches_awaiting_final_lockbox_approval_with_the_right_label(self, scen_a):
        ws, exp, rep = scen_a["ws"], scen_a["exp"], scen_a["rep"]
        assert rep["cpcv_passed"] and reg.experiment_row(ws, exp)["status"] == "AWAITING_FINAL_LOCKBOX_APPROVAL"
        assert rep["label"] == "POST-SELECTION ROBUSTNESS — NOT INDEPENDENT CONFIRMATION" and rep["final_lockbox_accessed"] is False
        md = (experiment_dir(ws, exp) / "results" / "CPCV_REPORT.md").read_text()
        assert "POST-SELECTION ROBUSTNESS — NOT INDEPENDENT CONFIRMATION" in md and "Final lockbox accessed: NO" in md and "CPCV_CONFIRMED" in md
        for m in ("RIDGE", "SPLINE", "XGB"):
            s = rep["summary"][f"{scen_a['cfg'].split('|', 1)[1]}|{m}"]
            assert s["n_valid_splits"] == 15 and s["cpcv_pass"] and s["n_effect_positive"] >= 12 and s["n_uplift_positive"] >= 12

    def test_lineage_of_a_frozen_final_config_stops(self, scen_a):
        with pytest.raises(EngineError, match="this lineage STOPS"):
            reg.register_experiment(scen_a["ws"], "C001", lineage_parent=scen_a["exp"])


@pytest.fixture(scope="module")
def scen_b(spent_b, tmp_path_factory):
    """B — a genuine near tie; the human approved both; the same holdout evaluates both; one is HOLDOUT_PREFERRED; the human selects it; CPCV passes."""
    ws = clone(spent_b[0], tmp_path_factory.mktemp("scen_b"), "ws")
    exp, tables, cfgs, rep = spent_b[1], spent_b[2], spent_b[3], spent_b[4]
    pick = rep["preference"]["holdout_preferred_config"]
    seen, spy = with_spy()
    mp = pytest.MonkeyPatch()
    mp.setattr(C, "run_cpcv_tables", spy)
    try:
        info, cp = finalize_config(ws, exp, tables, pick)
    finally:
        mp.undo()
    return dict(ws=ws, exp=exp, pick=pick, cfgs=cfgs, info=info, rep=cp, seen=seen)


class TestScenarioB_GenuineNearTieThroughTheHoldout:
    def test_the_preferred_config_was_chosen_by_the_human_and_cpcv_passed(self, scen_b):
        ws, exp = scen_b["ws"], scen_b["exp"]
        assert scen_b["pick"] in scen_b["cfgs"] and len(scen_b["cfgs"]) == 2 and scen_b["info"]["holdout_used"] is True
        assert scen_b["rep"]["cpcv_passed"] and reg.experiment_row(ws, exp)["status"] == "AWAITING_FINAL_LOCKBOX_APPROVAL"
        h = history(ws, exp)
        for a, b in zip(["NEAR_TIE_REVIEW_REQUIRED", "SELECTION_HOLDOUT_FROZEN", "SELECTION_HOLDOUT_SPENT", "FINAL_CONFIG_FROZEN", "CPCV_CONFIRMED", "AWAITING_FINAL_LOCKBOX_APPROVAL"],
                        ["SELECTION_HOLDOUT_FROZEN", "SELECTION_HOLDOUT_SPENT", "FINAL_CONFIG_FROZEN", "CPCV_CONFIRMED", "AWAITING_FINAL_LOCKBOX_APPROVAL", None]):
            assert a in h and (b is None or h.index(a) < h.index(b))
        assert "SELECTION_HOLDOUT_SKIPPED" not in h

    # 22. CPCV uses development + holdout if the holdout was used
    def test_cpcv_uses_development_plus_selection_holdout_when_it_was_used(self, scen_b):
        ws, exp, seen = scen_b["ws"], scen_b["exp"], scen_b["seen"]
        cutoff, label = C.cpcv_cutoff(ws, exp)
        assert cutoff == pd.Timestamp("2021-01-01", tz="UTC") and label == "DEVELOPMENT + SELECTION_HOLDOUT"
        assert seen["min"] < pd.Timestamp("2020-01-01", tz="UTC") and pd.Timestamp("2020-01-01", tz="UTC") <= seen["max"] < pd.Timestamp("2021-01-01", tz="UTC")
        assert scen_b["rep"]["data_used"] == "DEVELOPMENT + SELECTION_HOLDOUT" and scen_b["rep"]["selection_holdout_used"] is True
        assert scen_b["rep"]["label"].startswith("POST-SELECTION ROBUSTNESS")

    def test_the_final_config_is_exactly_the_humans_choice(self, scen_b):
        led = reg.read_final_configs(scen_b["ws"])
        assert list(led["event"]) == ["FINAL_CONFIG_FROZEN", "CPCV_RESULT"] and set(led["selected_config_id"]) == {scen_b["pick"]}
        assert led.iloc[1]["cpcv_status"] == "CPCV_CONFIRMED" and led.iloc[0]["selection_holdout_rank"] == "1"

    def test_the_whole_lifecycle_never_adds_a_selection_trial(self, scen_b):
        ws = scen_b["ws"]
        assert len(reg.read_trials(ws)) == 24 and reg.integrity_check(ws)["selection_trials"] == 24 and len(reg.read_selection_holdout_trials(ws)) == 6


@pytest.fixture(scope="module")
def scen_d(tmp_path_factory):
    """D — A and B both enter the holdout; the human selects A; A fails CPCV; the engine must NOT switch to B."""
    ws, exp, tables = lifecycle_workspace(tmp_path_factory.mktemp("scen_d"), **UNSTABLE)
    cfgs = proposable(ws, exp, 0)
    human_approval(ws, exp, cfgs)
    holdout = spend_selection_holdout(ws, exp, tables)
    info, rep = finalize_config(ws, exp, tables, cfgs[0])
    return dict(ws=ws, exp=exp, tables=tables, cfgs=cfgs, holdout=holdout, info=info, rep=rep)


class TestScenarioD_CpcvFailureHasNoFallback:
    def test_a_fails_cpcv_and_the_experiment_is_rejected(self, scen_d):
        ws, exp, rep = scen_d["ws"], scen_d["exp"], scen_d["rep"]
        assert len(scen_d["cfgs"]) == 2 and all(v["evidence_gates_met"] for v in scen_d["holdout"]["evidence_gate_verdicts"].values())   # both looked fine in the holdout
        assert rep["cpcv_passed"] is False and reg.experiment_row(ws, exp)["status"] == "CPCV_REJECTED"
        assert not any(v["cpcv_pass"] for v in rep["summary"].values())
        assert "AWAITING_FINAL_LOCKBOX_APPROVAL" not in history(ws, exp) and "CPCV_CONFIRMED" not in history(ws, exp)
        led = reg.read_final_configs(ws)
        assert led.iloc[1]["cpcv_status"] == "CPCV_REJECTED" and (reg.read_cpcv(ws)["group_cpcv_pass"] == "False").all()

    # 25. CPCV failure cannot fall back to the runner-up
    def test_the_engine_does_not_fall_back_to_the_runner_up(self, scen_d, tmp_path):
        ws = clone(scen_d["ws"], tmp_path)
        exp, a, b = scen_d["exp"], scen_d["cfgs"][0], scen_d["cfgs"][1]
        human_final_selection(ws, exp, b)                                                                    # even a human file naming B is refused
        with pytest.raises(ApprovalError, match="already froze its final configuration|no fallback"):
            freeze_final_config(ws, exp)
        with pytest.raises(EngineError):
            validate_final_selection(ws, exp)
        led = reg.read_final_configs(ws)
        assert set(led["selected_config_id"]) == {a} and b not in set(led["selected_config_id"])
        assert reg.experiment_row(ws, exp)["status"] == "CPCV_REJECTED"
        with pytest.raises(EngineError, match="CPCV runs only for FINAL_CONFIG_FROZEN"):
            run_cpcv_stage(ws, exp, scen_d["tables"])                                                       # nothing can run CPCV for B either

    # 26. CPCV failure ends the lineage
    def test_cpcv_failure_ends_the_lineage(self, scen_d):
        ws, exp = scen_d["ws"], scen_d["exp"]
        with pytest.raises(EngineError):
            reg.register_experiment(ws, "C001", lineage_parent=exp)                                         # a child lineage in this campaign is refused
        with pytest.raises(EngineError, match="CPCV runs only for FINAL_CONFIG_FROZEN"):
            C.precheck_cpcv(ws, exp)
        assert reg.experiment_row(ws, exp)["status"] == "CPCV_REJECTED"
        assert not any(h.startswith("LOCKBOX") for h in history(ws, exp))


@pytest.fixture(scope="module")
def scen_e(tmp_path_factory):
    """E — a strong IS config: the holdout collapses; the human declines; no CPCV; no lockbox."""
    ws, exp, tables = lifecycle_workspace(tmp_path_factory.mktemp("scen_e"), **CURVEFIT)
    cfgs = proposable(ws, exp, 0)
    human_approval(ws, exp, cfgs)
    holdout = spend_selection_holdout(ws, exp, tables)
    return dict(ws=ws, exp=exp, tables=tables, cfgs=cfgs, holdout=holdout)


class TestScenarioE_CurveFitCollapsesInTheHoldout:
    def test_is_looks_excellent_but_the_holdout_collapses_and_no_winner_is_fabricated(self, scen_e):
        ws, exp, h = scen_e["ws"], scen_e["exp"], scen_e["holdout"]
        t = reg.experiment_trials(ws, exp)
        assert (t["decision"] == "IS_SHORTLIST_ELIGIBLE").sum() >= 6 and t["standardized_uplift"].max() > 0.3
        conf = pd.DataFrame(h["evaluations"])
        assert (conf["selected_effect"] < 0).all() and not conf["gates_pass"].any()
        assert h["preference"]["status"] == "NO_QUALIFYING_CONFIG" and h["preference"]["holdout_preferred_config"] is None
        assert not any(v["evidence_gates_met"] for v in h["evidence_gate_verdicts"].values())

    def test_nothing_is_viable_so_the_experiment_stops_with_no_final_config_and_no_cpcv(self, scen_e, tmp_path):
        ws = clone(scen_e["ws"], tmp_path)
        exp = scen_e["exp"]
        assert scen_e["holdout"]["no_final_config"] is True and scen_e["holdout"]["viable_configs"] == [] and reg.experiment_row(ws, exp)["status"] == "NO_FINAL_CONFIG"
        for choice in (scen_e["cfgs"][0], "DECLINE"):
            human_final_selection(ws, exp, choice)
            with pytest.raises(ApprovalError, match="NO_FINAL_CONFIG"):
                freeze_final_config(ws, exp)
        assert reg.read_cpcv(ws).empty and reg.read_final_configs(ws).empty
        with pytest.raises(EngineError, match="no FINAL_CONFIG_FROZEN ledger row"):
            run_cpcv_stage(ws, exp, scen_e["tables"])
        assert not any(h.startswith(("CPCV", "AWAITING_FINAL_LOCKBOX", "LOCKBOX", "FINAL_CONFIG")) for h in history(ws, exp))

    def test_the_engine_does_not_pick_even_a_collapsed_config_for_the_human(self, scen_e, tmp_path):
        ws = clone(scen_e["ws"], tmp_path)
        exp = scen_e["exp"]
        with pytest.raises(ApprovalError, match="NO_FINAL_CONFIG|no human final-configuration selection file"):
            freeze_final_config(ws, exp)
        assert reg.read_final_configs(ws).empty


# ============================================================ final lockbox + wording guards
class TestFinalLockboxAndWording:
    # 28. the lockbox is inaccessible without the human
    def test_the_final_lockbox_is_never_opened_by_any_code_path(self, scen_a):
        p = subprocess.run([sys.executable, str(CODE_ROOT / "scripts/confirm_lockbox.py")], capture_output=True, text=True)
        assert p.returncode != 0 and "not implemented" in (p.stderr + p.stdout)
        ws, exp = scen_a["ws"], scen_a["exp"]
        assert reg.experiment_row(ws, exp)["status"] == "AWAITING_FINAL_LOCKBOX_APPROVAL"                  # it only WAITS for a human; nothing opens it
        from engine import partitions
        assert "lockbox_view" not in dir(partitions) and not [n for n in dir(partitions) if "lockbox" in n.lower() and callable(getattr(partitions, n))]
        for st in ("LOCKBOX_REJECTED", "LOCKBOX_CONFIRMED"):
            assert st in reg.LIFECYCLE and st not in " ".join(history(ws, exp))                              # defined, never entered by the engine
        src = "".join(open(CODE_ROOT / f).read() for f in ("engine/cpcv.py", "engine/selection_holdout_stage.py", "engine/experiment_runner.py"))
        assert "LOCKBOX_CONFIRMED" not in src and "LOCKBOX_REJECTED" not in src

    # 33. nothing calls the selection holdout "final confirmation" / OOS
    def test_no_code_path_calls_the_selection_holdout_final_confirmation(self):
        files = sorted((CODE_ROOT / "engine").glob("*.py")) + sorted((CODE_ROOT / "scripts").glob("*.py")) + [CODE_ROOT / n for n in ("README.md", "AGENTS.md", "RESEARCH_RULES.md")] \
            + sorted((CODE_ROOT / "docs").glob("*.md")) + sorted((CODE_ROOT / "templates").rglob("*")) + sorted((CODE_ROOT / "frozen").rglob("*.yaml"))
        neg = re.compile(r"\b(not|NOT|never|no|cannot|isn't|without|nor|only the untouched|only the final)\b|NOT FINAL|not independent|never confirm", re.I)
        bad = []
        for f in files:
            if not f.is_file():
                continue
            if f.name == "V1_2_LIFECYCLE.md":                                                                # the one document that maps the OLD names to the new ones
                continue
            for n, line in enumerate(f.read_text(errors="ignore").splitlines(), 1):
                if re.search(r"\bOOS\b|OOS_CONFIRMED|OOS_SPENT|oos_", line) and "renamed" not in line.lower() and "formerly" not in line.lower():
                    bad.append((f.name, n, "OOS token", line.strip()[:100]))
                stripped = re.sub(r"(CPCV|LOCKBOX)_CONFIRMED|confirm_lockbox", "", line)                       # legitimate status / script names
                if re.search(r"selection[ _-]?holdout", stripped, re.I) and re.search(r"confirm(ed|ation|s)\b", stripped, re.I) and not neg.search(stripped):
                    bad.append((f.name, n, "confirm wording", line.strip()[:100]))
        assert not bad, bad[:10]

    # 34. no code path asks for a human approval to run the fixed CPCV
    def test_no_code_path_asks_for_a_human_approval_to_run_the_fixed_cpcv(self):
        cp = (CODE_ROOT / "engine/cpcv.py").read_text()
        for tok in ("approval_path", "campaign_approval_path", "final_selection_path", "input(", "yaml.safe_load", ".approvals"):
            assert tok not in cp.replace("freeze_final_config", ""), tok
        assert 'exp["status"] != "FINAL_CONFIG_FROZEN"' in cp                                                   # the ONLY gate is a valid frozen final config
        for s in ("scripts/run_cpcv.py", "scripts/finalize_final_config.py"):
            txt = (CODE_ROOT / s).read_text()
            assert "input(" not in txt and "approve" not in txt.lower().replace("no approval", "").replace("without approval", "").replace("without any approval", "")
        import yaml
        sp = yaml.safe_load((CODE_ROOT / "frozen/v1/SELECTION_PROCESS.yaml").read_text())
        assert sp["cpcv"]["human_approval_required"] is False and sp["cpcv"]["automatic_after_final_config_frozen"] is True
        assert sp["human_approval_table"] == {"define_confirm_event_premise": True, "run_development_is": "explicit run", "open_selection_holdout": True,
                                              "choose_final_config": True, "run_fixed_cpcv": False, "open_final_lockbox": True}

    def test_the_documented_lifecycle_statuses_exist(self):
        want = ["DRAFT", "FROZEN", "IS_REJECTED", "IS_SHORTLIST_ELIGIBLE", "NEAR_TIE_REVIEW_REQUIRED", "AWAITING_HUMAN_SELECTION_HOLDOUT_APPROVAL",
                "SELECTION_HOLDOUT_FROZEN", "SELECTION_HOLDOUT_SPENT", "AWAITING_HUMAN_FINAL_CONFIG_SELECTION", "SELECTION_HOLDOUT_SKIPPED", "FINAL_CONFIG_FROZEN",
                "CPCV_REJECTED", "CPCV_CONFIRMED", "AWAITING_FINAL_LOCKBOX_APPROVAL", "LOCKBOX_REJECTED", "LOCKBOX_CONFIRMED", "NO_FINAL_CONFIG"]
        assert set(want) <= set(reg.LIFECYCLE) and not [s for s in reg.LIFECYCLE if "OOS" in s]
        assert reg.STATUS_ALIASES["AWAITING_HUMAN_SELECTION_HOLDOUT_APPROVAL"] == "NEAR_TIE_REVIEW_REQUIRED"
