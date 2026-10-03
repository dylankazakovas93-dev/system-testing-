"""Campaign-level SELECTION HOLDOUT (selection data, not confirmation): freeze all approved configs together, open once, correct multiplicity across the WHOLE campaign, spend the partition once.

Cheap registry-level tests first; the class at the bottom runs a real three-experiment campaign (table-level synthetic data,
real DEVELOPMENT_CV / SELECTION HOLDOUT code; near-tied 15|60 configs). Human approvals are written by TEST CODE PLAYING THE HUMAN (AGENTS.md rule 1)."""
import json
import os
import shutil

import numpy as np
import pandas as pd
import pytest
import yaml

from engine import trial_registry as reg
from engine.common import EngineError, load_frozen
from engine.experiment_lifecycle import experiment_dir
from engine.is_report import ReportSealedError, write_is_report
from engine.multiplicity import benjamini_hochberg
from engine.selection_holdout_stage import (ApprovalError, SelectionHoldoutContaminated, approval_path, campaign_approval_path, freeze_campaign_selection_holdout, freeze_path,
                              group_verdicts, mark_contamination_if_mutated, selection_holdout_evaluations, validate_approval, validate_campaign_open)
from tests.scenario_helpers import (LIFE_PARTS, campaign_open_approval, fake_results, human_approval, make_tie_tables, new_frozen_experiment,
                                    open_campaign_selection_holdout, prepare_for_approval, proposable, run_is_tables, top_group_ids)

F = load_frozen()
RULE = F.acceptance["selection_holdout_evidence"]


def clone(ws, tmp_path, name="copy"):
    dst = tmp_path / name
    shutil.copytree(ws.root, dst)
    return reg.Workspace(dst)


def spent_ledger_campaign(ws, cid):
    """Mark a campaign spent exactly as the engine does (ledger row + status), without running any data."""
    reg.append_selection_holdout_access(ws, campaign_id=cid, freeze_hash="f", open_approval_file_hash="o", experiments="E", approved_experiment_groups="E:G",
                          n_holdout_evaluations=3, selection_holdout_start="x", selection_holdout_end="y", unlock_timestamp="t", code_hash="h")
    reg.update_campaign(ws, cid, status="SELECTION_HOLDOUT_SPENT")


# ================================================== global SELECTION HOLDOUT Bonferroni / BH (pure functions) ==============================
def _row(exp, group, model, p, **kw):
    r = dict(experiment_id=exp, group_id=group, model=model, n_selected=300, selected_frequency=2.0, standardized_uplift=0.2,
             selected_effect=0.1, bootstrap_ci_low=0.01, raw_p=p)
    r.update(kw)
    return r


def test_bonferroni_is_over_every_confirmation_of_the_campaign_not_per_experiment():
    a = [_row("EXP_0001", "G1|U", m, 0.012) for m in ("RIDGE", "SPLINE", "XGB")]
    b = [_row("EXP_0002", "G1|U", m, 0.012) for m in ("RIDGE", "SPLINE", "XGB")]
    alone = selection_holdout_evaluations(a, RULE)
    assert all(r["selection_holdout_trials_in_family"] == 3 and r["gates_pass"] for r in alone)          # per-experiment: 0.012 * 3 = 0.036 <= 0.05
    both = selection_holdout_evaluations(a + b, RULE)
    assert all(r["selection_holdout_trials_in_family"] == 6 for r in both)
    assert all(r["selection_holdout_bonferroni_p"] == pytest.approx(0.072) for r in both)                  # campaign-wide: 0.012 * 6 > 0.05
    assert not any(r["gates_pass"] for r in both) and all("Bonferroni" in r["rejection_reason"] for r in both)
    assert group_verdicts([r for r in both if r["experiment_id"] == "EXP_0001"], RULE)["G1|U"]["evidence_gates_met"] is False


def test_bh_is_over_every_confirmation_of_the_campaign_not_per_experiment():
    a = [_row("EXP_0001", "G1|U", m, p) for m, p in zip(("RIDGE", "SPLINE", "XGB"), (0.001, 0.04, 0.04))]
    b = [_row("EXP_0002", "G9|U", m, 0.5) for m in ("RIDGE", "SPLINE", "XGB")]
    qa = [r["selection_holdout_q"] for r in selection_holdout_evaluations(a, RULE)]
    assert np.allclose(qa, benjamini_hochberg(np.array([0.001, 0.04, 0.04]))) and max(qa) <= 0.05          # alone: all within BH 0.05
    both = selection_holdout_evaluations(a + b, RULE)
    glob = benjamini_hochberg(np.array([r["raw_p"] for r in a + b]))
    assert np.allclose([r["selection_holdout_q"] for r in both], glob)                                                   # exactly the BH over all six
    assert both[1]["selection_holdout_q"] == pytest.approx(0.08) and both[2]["selection_holdout_q"] == pytest.approx(0.08)             # 0.04 * 6 / 3
    assert [r["gates_pass"] for r in both[:3]] == [True, False, False]                                       # the rest of the campaign makes it stricter
    assert group_verdicts(both[:3], RULE)["G1|U"]["evidence_gates_met"] is False                                      # 1 of 3 models: no confirmation


def test_losing_experiments_evaluations_count_in_the_family_too():
    win = [_row("EXP_0001", "G1|U", m, 0.0005) for m in ("RIDGE", "SPLINE", "XGB")]
    lose = [_row("EXP_0002", "G2|U", m, 0.9, selected_effect=-0.1) for m in ("RIDGE", "SPLINE", "XGB")]
    rows = selection_holdout_evaluations(win + lose, RULE)
    assert {r["selection_holdout_trials_in_family"] for r in rows} == {6}                                                  # never only winners
    assert rows[0]["selection_holdout_bonferroni_p"] == pytest.approx(0.003)


# ================================================== sequential reuse rejection (registry level) ==============================
def test_sequential_reuse_of_a_spent_selection_holdout_partition_is_rejected(tmp_path):
    ws = reg.Workspace(tmp_path / "ws").init()
    e1 = new_frozen_experiment(ws, "C001", LIFE_PARTS)
    spent_ledger_campaign(ws, "C001")
    # (a) no further experiment of the spent campaign (so no experiment can claim its SELECTION HOLDOUT as untouched)
    with pytest.raises(SelectionHoldoutContaminated, match="CAMPAIGN SELECTION HOLDOUT HAS BEEN SPENT"):
        reg.register_experiment(ws, "C001")
    # (b) a lineage child cannot either
    with pytest.raises(SelectionHoldoutContaminated, match="CAMPAIGN SELECTION HOLDOUT HAS BEEN SPENT"):
        reg.register_experiment(ws, "C001", lineage_parent=e1)
    # (c) a new campaign with the identical SELECTION HOLDOUT partition
    with pytest.raises(SelectionHoldoutContaminated, match="SELECTION HOLDOUT CONTAMINATED"):
        reg.create_campaign(ws, "C002", dict(LIFE_PARTS))
    # (d) a new campaign whose SELECTION HOLDOUT interval merely overlaps
    for dev_end, selection_holdout_end in (("2020-07-01", "2021-07-01"), ("2019-07-01", "2020-07-01"), ("2019-06-01", "2021-06-01")):
        with pytest.raises(SelectionHoldoutContaminated, match="overlaps the SELECTION HOLDOUT partition"):
            reg.create_campaign(ws, "C002", {"development_end": dev_end, "selection_holdout_end": selection_holdout_end, "lockbox_start": selection_holdout_end})
    assert set(reg.read_campaigns(ws)["campaign_id"]) == {"C001"}
    # (e) a genuinely later, disjoint SELECTION HOLDOUT partition is fine (the spent data may serve as development data there)
    reg.create_campaign(ws, "C002", {"development_end": "2021-01-01", "selection_holdout_end": "2022-01-01", "lockbox_start": "2022-01-01"})
    assert reg.register_experiment(ws, "C002") == "EXP_0002"
    # a campaign ending exactly where the spent SELECTION HOLDOUT starts does not overlap either (half-open intervals)
    reg.create_campaign(ws, "C003", {"development_end": "2019-01-01", "selection_holdout_end": "2020-01-01", "lockbox_start": "2020-01-01"})


def test_an_overlapping_campaign_created_earlier_cannot_freeze_or_open_after_the_other_spends(tmp_path):
    ws = reg.Workspace(tmp_path / "ws").init()
    reg.create_campaign(ws, "C001", dict(LIFE_PARTS))
    reg.create_campaign(ws, "C002", {"development_end": "2020-06-01", "selection_holdout_end": "2021-06-01", "lockbox_start": "2021-06-01"})   # overlaps, still unspent
    spent_ledger_campaign(ws, "C001")
    with pytest.raises(SelectionHoldoutContaminated, match="SELECTION HOLDOUT CONTAMINATED"):
        freeze_campaign_selection_holdout(ws, "C002")
    with pytest.raises(SelectionHoldoutContaminated, match="SELECTION HOLDOUT CONTAMINATED"):                              # defence in depth at the open step
        reg.update_campaign(ws, "C002", status="SELECTION_HOLDOUT_FROZEN")
        validate_campaign_open(ws, "C002")


def test_a_spent_campaign_can_never_be_opened_again(tmp_path):
    ws = reg.Workspace(tmp_path / "ws").init()
    new_frozen_experiment(ws, "C001", LIFE_PARTS)
    spent_ledger_campaign(ws, "C001")
    with pytest.raises(SelectionHoldoutContaminated, match="CAMPAIGN SELECTION HOLDOUT HAS BEEN SPENT"):
        reg.append_selection_holdout_access(ws, campaign_id="C001")
    with pytest.raises(SelectionHoldoutContaminated, match="CAMPAIGN SELECTION HOLDOUT HAS BEEN SPENT"):
        validate_campaign_open(ws, "C001")
    with pytest.raises(SelectionHoldoutContaminated, match="CAMPAIGN SELECTION HOLDOUT HAS BEEN SPENT"):
        freeze_campaign_selection_holdout(ws, "C001")
    with pytest.raises(SelectionHoldoutContaminated):                                                         # every experiment of the campaign, approved or not
        validate_approval(ws, "EXP_0001")
    assert reg.integrity_check(ws)["selection_holdout_unlocks"] == 1


# ================================================== freeze needs every IS experiment complete ================================
def test_freeze_refuses_while_any_experiment_has_not_completed_its_is_stage(tmp_path):
    ws = reg.Workspace(tmp_path / "ws").init()
    done = new_frozen_experiment(ws, "C001", LIFE_PARTS)
    reg.reveal_experiment(ws, done, fake_results(ws, done, {}, default_p=0.5, good=False), train_period="a", validation_period="b", frozen=F)
    pending = new_frozen_experiment(ws, "C001")                                                  # frozen but its IS run never happened
    draft = reg.register_experiment(ws, "C001")                                                  # still a DRAFT
    with pytest.raises(EngineError, match="IS stage is incomplete") as e:
        freeze_campaign_selection_holdout(ws, "C001")
    assert pending in str(e.value) and draft in str(e.value) and done not in str(e.value)
    assert reg.campaign_row(ws, "C001")["status"] == "OPEN" and not freeze_path(ws, "C001").exists()


# ================================================== a real three-experiment campaign =========================================
def approve_pair(ws, exp):
    """The human approves exactly the proposable (top-2) near-tied pair of the experiment's first cluster."""
    cfgs = proposable(ws, exp, 0)
    human_approval(ws, exp, cfgs)
    return cfgs


class TestCampaignFreezeAndSingleOpening:
    @pytest.fixture(scope="class")
    def built(self, tmp_path_factory):
        """A: near-tied pair (seed 11) - B: near-tied pair (seed 12) - N: no signal (IS_REJECTED, not included)."""
        ws = reg.Workspace(tmp_path_factory.mktemp("campaign")).init()
        tabs = {}
        for key, kw in (("A", dict(seed=11, signal="linear", slope=0.35)), ("B", dict(seed=12, signal="linear", slope=0.35)), ("N", dict(seed=13, signal="none"))):
            t = make_tie_tables(**kw)
            exp, _, _ = run_is_tables(ws, t, campaign="C001", partitions=LIFE_PARTS)
            tabs[key] = (exp, t)
        for key in ("A", "B"):
            prepare_for_approval(ws, tabs[key][0])
        return ws, {k: v[0] for k, v in tabs.items()}, {v[0]: v[1] for v in tabs.values()}

    @pytest.fixture(scope="class")
    def frozen_ws(self, built, tmp_path_factory):
        ws0, ids, _ = built
        ws = clone(ws0, tmp_path_factory.mktemp("frz"), "ws")
        a, b = ids["A"], ids["B"]
        ca, cb = approve_pair(ws, a), approve_pair(ws, b)
        doc = freeze_campaign_selection_holdout(ws, "C001")
        return ws, ids, doc, ca, cb

    def test_n_is_rejected_experiment_completes_is_but_is_not_eligible(self, built):
        ws, ids, _ = built
        assert reg.experiment_row(ws, ids["N"])["status"] == "IS_REJECTED"
        assert {reg.experiment_row(ws, ids[k])["status"] for k in "AB"} == {"NEAR_TIE_REVIEW_REQUIRED"}

    def test_freeze_collects_all_approved_configs_from_all_experiments_together(self, frozen_ws):
        ws, ids, doc, ca, cb = frozen_ws
        assert [e["experiment_id"] for e in doc["experiments"]] == [ids["A"], ids["B"]]
        assert doc["n_approved_configs"] == 4 and doc["n_holdout_evaluations"] == 12                    # 3 x (2 + 2)
        assert doc["approved_config_ids"] == ca + cb and doc["experiments_not_included"] == {ids["N"]: "IS_REJECTED"}
        c = reg.campaign_row(ws, "C001")
        assert c["status"] == "SELECTION_HOLDOUT_FROZEN" and c["selection_holdout_freeze_hash"] == doc["freeze_sha256"] and not reg.campaign_selection_holdout_spent(ws, "C001")
        saved = json.loads(freeze_path(ws, "C001").read_text())
        assert saved["experiments"][0]["approved_configs"] == ca and saved["partitions"] == LIFE_PARTS and len(saved["partitions_hash"]) == 64
        assert {reg.experiment_row(ws, ids[k])["status"] for k in "AB"} == {"SELECTION_HOLDOUT_FROZEN"}      # all frozen before any holdout byte is read
        assert reg.read_selection_holdout_access(ws).empty

    def test_a_frozen_campaign_is_closed(self, frozen_ws):
        ws, ids, doc, *_ = frozen_ws
        with pytest.raises(reg.CampaignClosed, match="register a new experiment"):
            reg.register_experiment(ws, "C001")
        with pytest.raises(reg.CampaignClosed, match="verification"):
            reg.set_verification(ws, ids["A"], {})
        with pytest.raises(ReportSealedError, match="SELECTION_HOLDOUT_FROZEN"):
            write_is_report(ws, ids["A"])
        with pytest.raises(reg.CampaignClosed):
            freeze_campaign_selection_holdout(ws, "C001")                                                          # no second freeze

    def test_each_experiment_approval_must_still_match_after_the_freeze(self, frozen_ws, tmp_path):
        ws0, ids, doc, ca, cb = frozen_ws
        for name, mutate, needle in (
                ("configs_changed", lambda w: human_approval(w, ids["A"], ca[:1]), "changed since the campaign freeze|approved_configs must be exactly"),
                ("approval_note_edited", lambda w: human_approval(w, ids["B"], cb, approval_note="a different human note"), "approval_file_sha256 changed")):
            ws = clone(ws0, tmp_path, name)
            campaign_open_approval(ws, "C001")
            mutate(ws)
            with pytest.raises(ApprovalError, match=needle):
                validate_campaign_open(ws, "C001")

    @pytest.mark.parametrize("name,override,needle", [
        ("wrong_freeze_hash", {"selection_holdout_freeze_sha256": "0" * 64}, "selection_holdout_freeze_sha256 does not match"),
        ("not_human", {"approved_by": "CLAUDE"}, "approved_by must be exactly HUMAN_USER"),
        ("not_bool", {"approved": "yes"}, "approved must be the boolean true"),
        ("wrong_campaign", {"campaign_id": "C999"}, "campaign_id mismatch"),
        ("empty_note", {"approval_note": " "}, "approval_note must be non-empty")])
    def test_the_human_campaign_open_approval_is_validated(self, frozen_ws, tmp_path, name, override, needle):
        ws = clone(frozen_ws[0], tmp_path, name)
        campaign_open_approval(ws, "C001", **override)
        with pytest.raises(ApprovalError, match=needle):
            validate_campaign_open(ws, "C001")
        assert reg.read_selection_holdout_access(ws).empty

    def test_nothing_opens_without_the_human_campaign_approval(self, frozen_ws, tmp_path):
        ws = clone(frozen_ws[0], tmp_path)
        assert not campaign_approval_path(ws, "C001").exists()
        with pytest.raises(ApprovalError, match="no human campaign-open approval file"):
            validate_campaign_open(ws, "C001")
        assert reg.read_selection_holdout_access(ws).empty and reg.campaign_row(ws, "C001")["status"] == "SELECTION_HOLDOUT_FROZEN"

    # ---- one opening for the whole campaign
    @pytest.fixture(scope="class")
    def opened(self, frozen_ws, built, tmp_path_factory):
        ws = clone(frozen_ws[0], tmp_path_factory.mktemp("opn"), "ws")
        res = open_campaign_selection_holdout(ws, "C001", built[2])
        return ws, frozen_ws[1], frozen_ws[3], frozen_ws[4], res

    def test_the_shared_partition_is_opened_exactly_once_with_one_ledger_row(self, opened):
        ws, ids, ca, cb, res = opened
        led = reg.read_selection_holdout_access(ws)
        assert len(led) == 1 and led.iloc[0]["campaign_id"] == "C001" and reg.verify_selection_holdout_ledger(ws) == 1
        assert led.iloc[0]["experiments"] == f"{ids['A']};{ids['B']}" and led.iloc[0]["n_holdout_evaluations"] == "12"
        assert led.iloc[0]["approved_experiment_groups"].split(";") == ca + cb
        assert reg.campaign_row(ws, "C001")["status"] == "SELECTION_HOLDOUT_SPENT" and reg.campaign_row(ws, "C001")["selection_holdout_spent_at"]
        assert reg.integrity_check(ws)["selection_holdout_unlocks"] == 1

    def test_bonferroni_and_bh_run_across_all_twelve_campaign_evaluations(self, opened):
        ws, ids, ca, cb, res = opened
        rows = reg.read_selection_holdout_trials(ws)
        assert len(rows) == 12 and set(rows["experiment_id"]) == {ids["A"], ids["B"]}
        assert (rows["selection_holdout_trials_in_family"].astype(int) == 12).all()                                    # NOT 6 per experiment
        p = rows["raw_p"].astype(float).to_numpy()
        assert np.allclose(rows["selection_holdout_bonferroni_p"].astype(float), np.minimum(p * 12, 1.0))
        assert np.allclose(rows["selection_holdout_q"].astype(float), benjamini_hochberg(p))                           # one BH over the pooled p-values
        assert (rows["selection_holdout_bonferroni_p"].astype(float) > np.minimum(p * 6, 1.0)).any()                   # strictly stricter than a per-experiment family

    def test_per_experiment_reports_and_statuses_are_preserved(self, opened):
        ws, ids, ca, cb, res = opened
        for key, cfgs in (("A", ca), ("B", cb)):
            e = ids[key]
            rep = json.loads((experiment_dir(ws, e) / "results" / "SELECTION_HOLDOUT_REPORT.json").read_text())
            assert rep["experiment_id"] == e and rep["approved_configs"] == cfgs and rep["holdout_model_evaluations"] == 6
            assert rep["family_size_for_multiple_testing"] == 12 and rep["scope_of_multiplicity"] == "ENTIRE CAMPAIGN"
            assert rep["campaign_experiments_in_family"] == [ids["A"], ids["B"]] and len(rep["evaluations"]) == 6
            assert rep["status"] == reg.experiment_row(ws, e)["status"] == "SELECTION_HOLDOUT_SPENT" and rep["label"].startswith("SELECTION DATA")
            md = (experiment_dir(ws, e) / "results" / "SELECTION_HOLDOUT_REPORT.md").read_text()
            assert "ENTIRE CAMPAIGN" in md and "NOT FINAL CONFIRMATION" in md
        assert reg.experiment_row(ws, ids["N"])["status"] == "IS_REJECTED"                              # not part of the SELECTION HOLDOUT, untouched
        assert not (experiment_dir(ws, ids["N"]) / "results" / "SELECTION_HOLDOUT_REPORT.json").exists()
        camp = json.loads((ws.root / "registry" / "selection_holdout_campaign_report_C001.json").read_text())
        assert camp["family_size"] == 12 and len(camp["evaluations"]) == 12

    # ---- campaign-SELECTION HOLDOUT-spent enforcement
    def test_after_opening_nothing_can_reopen_or_extend_the_campaign(self, opened):
        ws, ids, ca, cb, res = opened
        with pytest.raises(SelectionHoldoutContaminated, match="CAMPAIGN SELECTION HOLDOUT HAS BEEN SPENT"):
            validate_campaign_open(ws, "C001")
        with pytest.raises(SelectionHoldoutContaminated, match="CAMPAIGN SELECTION HOLDOUT HAS BEEN SPENT"):
            reg.register_experiment(ws, "C001")
        with pytest.raises(SelectionHoldoutContaminated, match="CAMPAIGN SELECTION HOLDOUT HAS BEEN SPENT"):
            reg.append_selection_holdout_access(ws, campaign_id="C001")
        human_approval(ws, ids["A"], ca)                                                                  # a fresh human approval changes nothing
        with pytest.raises(SelectionHoldoutContaminated, match="CAMPAIGN SELECTION HOLDOUT HAS BEEN SPENT"):
            validate_approval(ws, ids["A"])
        assert len(reg.read_selection_holdout_access(ws)) == 1 and len(reg.read_selection_holdout_trials(ws)) == 12

    def test_every_experiment_of_the_spent_campaign_is_sealed_even_non_participants(self, opened):
        ws, ids, *_ = opened
        for e in ids.values():
            with pytest.raises(ReportSealedError):
                write_is_report(ws, e)
        with pytest.raises(SelectionHoldoutContaminated, match="CAMPAIGN SELECTION HOLDOUT HAS BEEN SPENT"):
            validate_approval(ws, ids["N"])

    def test_changing_any_experiment_after_the_campaign_opened_marks_it_contaminated(self, opened, tmp_path):
        ws = clone(opened[0], tmp_path)
        ids = opened[1]
        d = experiment_dir(ws, ids["N"])                                                                  # even the non-participating experiment
        os.chmod(d / "event.py", 0o644)
        (d / "event.py").write_text((d / "event.py").read_text() + "\n# edited after the campaign SELECTION HOLDOUT was spent\n")
        assert mark_contamination_if_mutated(ws, ids["N"]) is True
        assert reg.experiment_row(ws, ids["N"])["status"] == "SELECTION_HOLDOUT_CONTAMINATED"
        assert mark_contamination_if_mutated(ws, ids["A"]) is False

    def test_spent_selection_holdout_cannot_be_claimed_by_a_new_overlapping_campaign(self, opened):
        ws = opened[0]
        with pytest.raises(SelectionHoldoutContaminated, match="SELECTION HOLDOUT CONTAMINATED"):
            reg.create_campaign(ws, "C002", dict(LIFE_PARTS))
        reg.create_campaign(ws, "C002", {"development_end": "2021-01-01", "selection_holdout_end": "2022-01-01", "lockbox_start": "2022-01-01"})

    def test_the_whole_campaign_registry_stays_consistent(self, opened):
        ws, ids, *_ = opened
        chk = reg.integrity_check(ws)
        assert chk["experiments"] == 3 and chk["selection_trials"] == 72 and chk["revealed_trials"] == 72           # the DEVELOPMENT count stays 24 per experiment
        s = reg.campaign_summary(ws, "C001")
        assert s["campaign_status"] == "SELECTION_HOLDOUT_SPENT" and s["campaign_selection_holdout_spent"] is True and s["selection_holdout_unlocks"] == 1


# ================================================== MAX_SELECTION_HOLDOUT_CONFIGS_PER_CAMPAIGN = 6 (=> at most 18 holdout evaluations) ========
import hashlib  # noqa: E402

CAMP_CAP = F.trial_policy["selection_holdout"]["max_groups_per_campaign"]
EXP_CAP = F.trial_policy["selection_holdout"]["max_groups_per_experiment"]


def tree_snapshot(ws):
    """Byte-level fingerprint of the whole workspace (registry, experiments, approvals, results): proves atomic refusals."""
    return {str(p.relative_to(ws.root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(ws.root.rglob("*")) if p.is_file() and "verification/stage" not in str(p)}


def test_the_caps_are_frozen_constants_in_the_v1_policy():
    assert (EXP_CAP, CAMP_CAP) == (2, 6) and F.trial_policy["selection_holdout"]["models_per_group"] == 3
    assert 3 * CAMP_CAP == 18
    from engine.selection_holdout_stage import assert_campaign_group_cap
    ent = lambda *n: [{"experiment_id": f"E{i}", "approved_configs": ["g"] * k} for i, k in enumerate(n)]   # noqa: E731
    assert assert_campaign_group_cap(ent(2, 2, 2), F) == 6 and assert_campaign_group_cap(ent(1, 1, 1, 1, 1, 1), F) == 6
    with pytest.raises(ApprovalError, match="MAX_SELECTION_HOLDOUT_CONFIGS_PER_CAMPAIGN = 6"):
        assert_campaign_group_cap(ent(2, 2, 2, 1), F)
    with pytest.raises(ApprovalError, match="MAX_SELECTION_HOLDOUT_CONFIGS_PER_EXPERIMENT = 2"):
        assert_campaign_group_cap(ent(3), F)


def test_the_full_eighteen_evaluation_family_is_corrected_jointly_including_losers():
    rows = []
    for i in range(6):                                    # 6 configs x 3 models; the last two configs are clear losers
        loser = i >= 4
        for m in ("RIDGE", "SPLINE", "XGB"):
            rows.append(_row(f"EXP_{i // 2 + 1:04d}", f"G{i}|U", m, 0.9 if loser else 0.0005 * (i + 1),
                             **({"selected_effect": -0.2} if loser else {})))
    out = selection_holdout_evaluations(rows, RULE)
    p = np.array([r["raw_p"] for r in rows])
    assert len(out) == 18 and {r["selection_holdout_trials_in_family"] for r in out} == {18}
    assert np.allclose([r["selection_holdout_bonferroni_p"] for r in out], np.minimum(p * 18, 1.0))                  # multiplier = the FULL family size
    assert np.allclose([r["selection_holdout_q"] for r in out], benjamini_hochberg(p))                                # BH over all 18 incl. losers
    assert not np.allclose(benjamini_hochberg(p[:12]), [r["selection_holdout_q"] for r in out[:12]])                  # dropping the losers WOULD change q
    assert [r["selection_holdout_bonferroni_p"] for r in out[:3]] == pytest.approx([0.009] * 3)                       # 0.0005 * 18, not * 3 or * 6


class TestCampaignConfigCap:
    @pytest.fixture(scope="class")
    def four(self, tmp_path_factory):
        """Four IS-complete, verified experiments (A..D) in one campaign; each has a near-tied pair, so approving all would be 8 configs > 6."""
        ws = reg.Workspace(tmp_path_factory.mktemp("capcamp")).init()
        ids, tabs = [], {}
        for seed in (21, 22, 23, 24):
            t = make_tie_tables(seed=seed, years=range(2015, 2021), events_per_week=9, signal="linear", slope=0.4)
            exp, _, _ = run_is_tables(ws, t, campaign="C001", partitions=LIFE_PARTS)
            prepare_for_approval(ws, exp)
            ids.append(exp)
            tabs[exp] = t
        return ws, ids, tabs

    @staticmethod
    def approve(ws, ids, which):
        return {e: approve_pair(ws, e) for e, w in zip(ids, which) if w}

    @pytest.fixture
    def forbid_selection_holdout_data(self, monkeypatch):
        import engine.selection_holdout_stage as o

        def boom(*a, **k):
            raise AssertionError("a campaign freeze must not touch SELECTION HOLDOUT data")
        monkeypatch.setattr(o, "selection_holdout_view", boom)
        monkeypatch.setattr(o, "build_event_tables", boom)

    def test_all_four_experiments_have_a_near_tie_so_the_cap_is_the_only_obstacle(self, four):
        ws, ids, _ = four
        assert {reg.experiment_row(ws, e)["status"] for e in ids} == {"NEAR_TIE_REVIEW_REQUIRED"}
        assert all(len(proposable(ws, e, 0)) == 2 for e in ids)

    def test_eight_campaign_configs_are_refused_atomically(self, four, tmp_path, forbid_selection_holdout_data):
        ws = clone(four[0], tmp_path)
        ids = four[1]
        self.approve(ws, ids, (1, 1, 1, 1))
        before = tree_snapshot(ws)
        with pytest.raises(ApprovalError, match="8 approved configs across the campaign > MAX_SELECTION_HOLDOUT_CONFIGS_PER_CAMPAIGN = 6"):
            freeze_campaign_selection_holdout(ws, "C001")
        assert tree_snapshot(ws) == before                                         # nothing at all changed: registry, statuses, files, approvals
        assert not freeze_path(ws, "C001").exists() and reg.read_selection_holdout_access(ws).empty and reg.read_selection_holdout_trials(ws).empty
        assert reg.campaign_row(ws, "C001")["status"] == "OPEN" and reg.campaign_row(ws, "C001")["selection_holdout_freeze_hash"] == ""
        assert {reg.experiment_row(ws, e)["status"] for e in ids} == {"NEAR_TIE_REVIEW_REQUIRED"}
        # the human may fix it (decline the fourth) and the very same campaign then freezes
        human_approval(ws, ids[3], proposable(ws, ids[3], 0), approved=False)
        assert freeze_campaign_selection_holdout(ws, "C001")["n_approved_configs"] == 6

    def test_exactly_six_campaign_configs_are_accepted_giving_18_evaluations(self, four, tmp_path, forbid_selection_holdout_data):
        ws = clone(four[0], tmp_path)
        ids = four[1]
        self.approve(ws, ids, (1, 1, 1, 0))
        doc = freeze_campaign_selection_holdout(ws, "C001")
        assert doc["n_approved_configs"] == 6 and doc["n_holdout_evaluations"] == 18
        assert doc["experiments_not_included"] == {ids[3]: "NO_HOLDOUT_APPROVAL"} and reg.experiment_row(ws, ids[3])["status"] == "NEAR_TIE_REVIEW_REQUIRED"   # may still be chosen directly
        assert reg.campaign_row(ws, "C001")["status"] == "SELECTION_HOLDOUT_FROZEN"

    def test_the_per_experiment_cap_of_two_still_applies(self, four, tmp_path, forbid_selection_holdout_data):
        ws = clone(four[0], tmp_path)
        ids = four[1]
        self.approve(ws, ids, (1, 0, 0, 0))
        human_approval(ws, ids[1], proposable(ws, ids[1], 0) + ["EXP_X|DIR_RETURN_30|UPPER_HALF"])      # 3 configs for one experiment, only 5 campaign-wide
        before = tree_snapshot(ws)
        with pytest.raises(ApprovalError, match="MAX_SELECTION_HOLDOUT_CONFIGS_PER_EXPERIMENT = 2"):
            freeze_campaign_selection_holdout(ws, "C001")
        assert tree_snapshot(ws) == before and reg.campaign_row(ws, "C001")["status"] == "OPEN"

    def test_zero_approved_configs_never_freeze_or_open_selection_holdout(self, four, tmp_path, forbid_selection_holdout_data):
        ws = clone(four[0], tmp_path)
        ids = four[1]
        before = tree_snapshot(ws)
        with pytest.raises(EngineError, match="nothing to freeze"):
            freeze_campaign_selection_holdout(ws, "C001")
        assert tree_snapshot(ws) == before
        for e in ids:                                                             # every approval negative
            human_approval(ws, e, proposable(ws, e, 0), approved=False)
        before = tree_snapshot(ws)
        with pytest.raises(EngineError, match="nothing to freeze"):
            freeze_campaign_selection_holdout(ws, "C001")
        assert tree_snapshot(ws) == before and reg.read_selection_holdout_access(ws).empty
        campaign_open_approval(ws, "C001", selection_holdout_freeze_sha256="0" * 64)
        with pytest.raises(ApprovalError, match="must first be frozen"):
            validate_campaign_open(ws, "C001")

    @pytest.fixture(scope="class")
    def six_frozen(self, four, tmp_path_factory):
        ws = clone(four[0], tmp_path_factory.mktemp("six"), "ws")
        self.approve(ws, four[1], (1, 1, 1, 0))
        doc = freeze_campaign_selection_holdout(ws, "C001")
        return ws, doc

    def test_an_already_frozen_campaign_cannot_bypass_the_cap(self, four, six_frozen, tmp_path):
        ws = clone(six_frozen[0], tmp_path)
        ids = four[1]
        human_approval(ws, ids[3], proposable(ws, ids[3], 0))                      # two more configs, approved after the freeze
        before = tree_snapshot(ws)
        with pytest.raises(reg.CampaignClosed):
            freeze_campaign_selection_holdout(ws, "C001")
        assert tree_snapshot(ws) == before
        campaign_open_approval(ws, "C001")
        doc, _, aps = validate_campaign_open(ws, "C001")                          # the late approval is simply not part of the frozen set
        assert doc["n_holdout_evaluations"] == 18 and set(aps) == set(ids[:3])

    def test_editing_the_freeze_json_to_add_a_seventh_config_fails_integrity(self, four, six_frozen, tmp_path):
        ids = four[1]
        from engine.common import sha256_file
        # (a) plain edit: the registry-recorded hash no longer matches
        ws = clone(six_frozen[0], tmp_path, "a")
        campaign_open_approval(ws, "C001")
        doc = json.loads(freeze_path(ws, "C001").read_text())
        doc["experiments"][0]["approved_configs"].append("EXP_X|DIR_RETURN_15|UPPER_HALF")
        doc["n_approved_configs"], doc["n_holdout_evaluations"] = 7, 21
        freeze_path(ws, "C001").write_text(json.dumps(doc, indent=2, sort_keys=True))
        with pytest.raises(ApprovalError, match="missing or was edited after the freeze"):
            validate_campaign_open(ws, "C001")
        # (b) the forger also re-hashes the file in the registry and re-writes the open approval: the cap still holds
        ws = clone(six_frozen[0], tmp_path, "b")
        doc = json.loads(freeze_path(ws, "C001").read_text())
        doc["experiments"].append({**doc["experiments"][0], "experiment_id": ids[3], "approved_configs": ["EXP_X|DIR_RETURN_15|UPPER_HALF"]})
        doc["n_approved_configs"], doc["n_holdout_evaluations"] = 7, 21
        freeze_path(ws, "C001").write_text(json.dumps(doc, indent=2, sort_keys=True))
        reg.update_campaign(ws, "C001", selection_holdout_freeze_hash=sha256_file(freeze_path(ws, "C001")))
        campaign_open_approval(ws, "C001")
        with pytest.raises(ApprovalError, match="MAX_SELECTION_HOLDOUT_CONFIGS_PER_CAMPAIGN = 6"):
            validate_campaign_open(ws, "C001")
        # (c) re-hashed edit that pushes ONE experiment over 2 configs
        ws = clone(six_frozen[0], tmp_path, "c")
        doc = json.loads(freeze_path(ws, "C001").read_text())
        doc["experiments"][0]["approved_configs"] = doc["experiments"][0]["approved_configs"] + ["x|y|z"]
        doc["experiments"][1]["approved_configs"] = doc["experiments"][1]["approved_configs"][:1]
        freeze_path(ws, "C001").write_text(json.dumps(doc, indent=2, sort_keys=True))
        reg.update_campaign(ws, "C001", selection_holdout_freeze_hash=sha256_file(freeze_path(ws, "C001")))
        campaign_open_approval(ws, "C001")
        with pytest.raises(ApprovalError, match="MAX_SELECTION_HOLDOUT_CONFIGS_PER_EXPERIMENT = 2"):
            validate_campaign_open(ws, "C001")
        # (d) re-hashed edit with inconsistent counts (cap respected) is still caught
        ws = clone(six_frozen[0], tmp_path, "d")
        doc = json.loads(freeze_path(ws, "C001").read_text())
        doc["n_holdout_evaluations"] = 12
        freeze_path(ws, "C001").write_text(json.dumps(doc, indent=2, sort_keys=True))
        reg.update_campaign(ws, "C001", selection_holdout_freeze_hash=sha256_file(freeze_path(ws, "C001")))
        campaign_open_approval(ws, "C001")
        with pytest.raises(ApprovalError, match="internally inconsistent"):
            validate_campaign_open(ws, "C001")
        assert reg.read_selection_holdout_access(ws).empty

    @pytest.fixture(scope="class")
    def opened18(self, four, six_frozen, tmp_path_factory):
        ws = clone(six_frozen[0], tmp_path_factory.mktemp("open18"), "ws")
        return ws, open_campaign_selection_holdout(ws, "C001", four[2])

    def test_the_maximum_family_is_18_and_every_evaluation_is_corrected_jointly(self, opened18):
        ws, res = opened18
        led = reg.read_selection_holdout_access(ws)
        assert len(led) == 1 and led.iloc[0]["n_holdout_evaluations"] == "18" and len(led.iloc[0]["approved_experiment_groups"].split(";")) == 6
        rows = reg.read_selection_holdout_trials(ws)
        assert len(rows) == 18 == res["family_size"] and (rows["selection_holdout_trials_in_family"].astype(int) == 18).all()
        p = rows["raw_p"].astype(float).to_numpy()
        assert np.allclose(rows["selection_holdout_bonferroni_p"].astype(float), np.minimum(p * 18, 1.0))             # full-family multiplier, never relaxed
        assert np.allclose(rows["selection_holdout_q"].astype(float), benjamini_hochberg(p))                          # BH over all 18
        assert set(rows["model"]) == {"RIDGE", "SPLINE", "XGB"} and rows["experiment_id"].nunique() == 3

    def test_a_spent_campaign_cannot_bypass_the_cap_or_reopen(self, four, opened18):
        ws, _ = opened18
        human_approval(ws, four[1][3], proposable(ws, four[1][3], 0))
        with pytest.raises(SelectionHoldoutContaminated, match="CAMPAIGN SELECTION HOLDOUT HAS BEEN SPENT"):
            freeze_campaign_selection_holdout(ws, "C001")
        with pytest.raises(SelectionHoldoutContaminated, match="CAMPAIGN SELECTION HOLDOUT HAS BEEN SPENT"):
            validate_campaign_open(ws, "C001")
        assert len(reg.read_selection_holdout_access(ws)) == 1 and len(reg.read_selection_holdout_trials(ws)) == 18

    def test_an_experiment_outside_the_holdout_can_still_choose_directly_after_the_campaign_spent_it(self, four, opened18, tmp_path):
        """D carried no holdout approval (its near-tie was not proposed). After the shared holdout is spent the human may still pick one IS-eligible
        config of D directly; the holdout is then marked SKIPPED for D and CPCV uses DEVELOPMENT only - D never reads the spent partition."""
        from engine.cpcv import cpcv_cutoff
        from engine.selection_holdout_stage import freeze_final_config
        from tests.scenario_helpers import human_final_selection
        ws, _ = opened18
        ws = clone(ws, tmp_path)
        d = four[1][3]
        assert reg.experiment_row(ws, d)["status"] == "NEAR_TIE_REVIEW_REQUIRED" and reg.campaign_row(ws, "C001")["status"] == "SELECTION_HOLDOUT_SPENT"
        cfg = f"{d}|{top_group_ids(ws, d)[0]}"
        human_final_selection(ws, d, cfg)
        info = freeze_final_config(ws, d)
        assert info["holdout_used"] is False and reg.experiment_row(ws, d)["status"] == "FINAL_CONFIG_FROZEN"
        cutoff, label = cpcv_cutoff(ws, d)
        assert str(cutoff.date()) == "2020-01-01" and "DEVELOPMENT only" in label
        assert reg.read_final_configs(ws).iloc[0]["selection_holdout_used"] == "no"
