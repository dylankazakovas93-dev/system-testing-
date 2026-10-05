"""Near-tie / configuration-uncertainty detection (frozen/v1/SELECTION_PROCESS.yaml) on real table-level IS runs and on crafted series.

Near-tie checks are DIAGNOSTICS: they never create a selection trial, never promote a rejected configuration and never choose for the human."""
import json

import numpy as np
import pytest

from engine import near_tie as nt
from engine import trial_registry as reg
from engine.common import load_frozen
from engine.experiment_lifecycle import experiment_dir
from engine.selection_holdout_stage import ApprovalError, validate_approval
from tests.scenario_helpers import CLEAR_WINNER, NEAR_TIE_PAIR, human_approval, lifecycle_workspace, proposable

F = load_frozen()
NT = F.selection_process["near_tie"]
DEFAULT_LINEAR = dict(signal="linear", slope=0.35, target_scale={"DIR_PATH_SKEW_60": 0.0},                      # 15, 60 and 180 carry the same relation AND noise -> a 3-member cluster per side
                      tie={"DIR_RETURN_60": "DIR_RETURN_15", "DIR_RETURN_180": "DIR_RETURN_15"})
FAR = dict(signal="linear", slope=0.35, target_scale={"DIR_RETURN_180": 0.5, "DIR_PATH_SKEW_60": 0.0}, tie={"DIR_RETURN_60": "DIR_RETURN_15"})   # 180 carries half the effect: clearly separated


@pytest.fixture(scope="module")
def near(tmp_path_factory):
    return lifecycle_workspace(tmp_path_factory.mktemp("near"), **NEAR_TIE_PAIR)


@pytest.fixture(scope="module")
def default3(tmp_path_factory):
    return lifecycle_workspace(tmp_path_factory.mktemp("default3"), **DEFAULT_LINEAR)


@pytest.fixture(scope="module")
def far(tmp_path_factory):
    return lifecycle_workspace(tmp_path_factory.mktemp("far"), **FAR)


@pytest.fixture(scope="module")
def clear(tmp_path_factory):
    return lifecycle_workspace(tmp_path_factory.mktemp("clear"), **CLEAR_WINNER)


def report(ws, exp):
    return json.loads((experiment_dir(ws, exp) / "results" / "IS_REPORT.json").read_text())


# ---------------------------------------------------------------- frozen rule
def test_the_near_tie_rule_is_frozen_exactly_as_specified():
    assert NT["max_abs_diff_median_standardized_uplift"] == 0.03 and NT["both_is_shortlist_eligible"] and NT["same_side"] and NT["same_experiment"]
    pb = NT["paired_bootstrap"]
    assert (pb["repetitions"], pb["seed"], pb["ci_level"], pb["block"]) == (2000, 1729, 0.95, "trading_week")
    assert NT["clustering"] == "connected_components" and NT["max_configs_proposed_per_cluster"] == 2
    assert NT["creates_selection_trials"] is False and NT["can_promote_a_rejected_config"] is False


# 1. near tie detected when uplift difference <= 0.03 and the paired CI includes 0
def test_near_tie_detected_when_difference_small_and_paired_ci_contains_zero(near):
    ws, exp, _ = near
    det = nt.detect(ws, exp)
    assert det["available"] and det["clusters"]
    tied = [p for p in det["pairs"] if p["near_tie"]]
    assert tied and all(p["abs_diff"] <= 0.03 and p["ci_low"] <= 0.0 <= p["ci_high"] for p in tied)
    assert all("contains 0" in p["reason"] for p in tied)
    cl = det["clusters"][0]
    assert {m.split("|", 1)[1].split("|")[0] for m in cl["members"]} == {"DIR_RETURN_15", "DIR_RETURN_60"}


# 2. no near tie if the difference is larger than 0.03 (no bootstrap is even needed)
def test_no_near_tie_if_the_difference_exceeds_0_03(far):
    ws, exp, _ = far
    det = nt.detect(ws, exp)
    far = [p for p in det["pairs"] if p["abs_diff"] > 0.03]
    assert far and not any(p["near_tie"] for p in far)
    assert all("not a near tie" in p["reason"] and "ci_low" not in p for p in far)       # decided by the difference alone


# 3. no near tie if the paired CI excludes zero (crafted so that |difference| <= 0.03 yet the paired difference is systematic)
def _crafted(shift):
    rng = np.random.default_rng(5)
    n, weeks = 6000, 120
    wk = np.array([f"W{i % weeks:03d}" for i in range(n)])
    x = rng.normal(size=n)
    y = 0.2 * x + rng.normal(size=n)
    sel = x > 0
    sd = float(y.std())
    a = (wk, y, sel, 1.0, sd)
    b = (wk, y + shift * sel, sel, 1.0, sd)                  # B = A plus a tiny, perfectly systematic selected-event shift
    return a, b


def test_paired_ci_excluding_zero_is_not_a_near_tie_even_when_the_difference_is_tiny():
    a, b = _crafted(0.0)
    same = nt.paired_difference([a], [b], reps=2000, seed=1729, ci_level=0.95)
    assert same["difference"] == 0.0 and same["ci_contains_zero"] is True
    a, b = _crafted(0.03)
    r = nt.paired_difference([b], [a], reps=2000, seed=1729, ci_level=0.95)
    assert 0.0 < abs(r["difference"]) <= 0.03 and r["ci_contains_zero"] is False and (r["ci_low"] > 0 or r["ci_high"] < 0)


def test_detect_rejects_a_pair_whose_ci_excludes_zero(near, monkeypatch):
    ws, exp, _ = near
    real = nt.paired_difference

    def excl(*a, **k):
        out = real(*a, **k)
        return {**out, "ci_low": 0.01, "ci_high": 0.02, "ci_contains_zero": False}
    monkeypatch.setattr(nt, "paired_difference", excl)
    det = nt.detect(ws, exp)
    close = [p for p in det["pairs"] if p["abs_diff"] <= 0.03]
    assert close and not any(p["near_tie"] for p in close) and det["clusters"] == []
    assert all("excludes 0: not a near tie" in p["reason"] for p in close)


# 4. a rejected IS config can never enter a cluster
def test_rejected_is_configs_never_enter_a_near_tie_cluster(near):
    ws, exp, _ = near
    det = nt.detect(ws, exp)
    eligible = {g["config_id"] for g in det["eligible_groups"]}
    members = {m for c in det["clusters"] for m in c["members"]}
    assert members <= eligible and not any("DIR_RETURN_180" in m or "DIR_PATH_SKEW_60" in m for m in members)     # those targets carry no effect


def test_losing_eligibility_removes_a_config_from_its_cluster(near, tmp_path):
    import shutil
    ws0, exp, _ = near
    dst = tmp_path / "w"
    shutil.copytree(ws0.root, dst)
    ws = reg.Workspace(dst)
    ver = json.loads(reg.experiment_row(ws, exp)["verification_json"])
    for m in ("RIDGE", "SPLINE"):
        ver[f"DIR_RETURN_60|{m}"] = {"label": "FAILED", "mode": "strong"}                       # 60 loses its 2-of-3 model agreement
    reg.set_verification(ws, exp, ver, "FAILED", F)
    det = nt.detect(ws, exp)
    assert not any("DIR_RETURN_60" in g["config_id"] for g in det["eligible_groups"])
    assert det["clusters"] == [] and all("DIR_RETURN_60" not in p["a"] + p["b"] for p in det["pairs"])


# 5. opposite sides never form a cluster
def test_opposite_sides_do_not_form_the_same_near_tie_cluster(default3):
    ws, exp, _ = default3
    det = nt.detect(ws, exp)
    assert det["clusters"] and all(len({m.rsplit("|", 1)[1] for m in c["members"]}) == 1 for c in det["clusters"])
    assert all(p["a"].rsplit("|", 1)[1] == p["b"].rsplit("|", 1)[1] for p in det["pairs"])                      # opposite sides are never even compared
    by = {g["config_id"]: g["median_standardized_uplift"] for g in det["eligible_groups"]}
    a, b = f"{exp}|DIR_RETURN_15|LOWER_HALF", f"{exp}|DIR_RETURN_60|UPPER_HALF"
    assert abs(by[a] - by[b]) <= 0.03                                                                    # ~identical uplift on opposite sides...
    assert not any({p["a"], p["b"]} == {a, b} for p in det["pairs"])                                     # ...yet never paired nor clustered


# 6. deterministic clusters; connected components; ranked by the existing frozen IS group ranking
def test_cluster_construction_is_deterministic_and_ranked_by_the_frozen_is_ranking(default3):
    ws, exp, _ = default3
    a, b = nt.detect(ws, exp), nt.detect(ws, exp)
    assert json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str)
    for c in a["clusters"]:
        ranks = [c["is_ranks"][m] for m in c["members"]]
        assert ranks == sorted(ranks)                                                                    # members listed in the existing frozen IS rank order
    firsts = [min(c["is_ranks"].values()) for c in a["clusters"]]
    assert firsts == sorted(firsts) and [c["cluster_id"] for c in a["clusters"]] == [f"NEAR_TIE_CLUSTER_{k:02d}" for k in range(1, len(a["clusters"]) + 1)]
    # the cluster is a CONNECTED COMPONENT (here the three identical-label configs are joined by >= 2 near-tie edges)
    edges = {(p["a"], p["b"]) for p in a["pairs"] if p["near_tie"]}
    big = max(a["clusters"], key=lambda c: len(c["members"]))
    assert len(big["members"]) == 3 and len(edges) >= 2


# 7. at most the top two of a cluster are proposable; a third is refused
def test_only_the_top_two_of_a_cluster_may_enter_the_selection_holdout(default3):
    ws, exp, _ = default3
    det = nt.detect(ws, exp)
    big = max(det["clusters"], key=lambda c: len(c["members"]))
    assert len(big["members"]) == 3 and big["proposable_for_holdout"] == big["members"][:2]
    ws.approvals.mkdir(parents=True, exist_ok=True)
    human_approval(ws, exp, big["members"])                                                              # all three: refused
    with pytest.raises(ApprovalError, match="MAX_SELECTION_HOLDOUT_CONFIGS_PER_EXPERIMENT = 2"):
        validate_approval(ws, exp)
    human_approval(ws, exp, [big["members"][0], big["members"][2]], near_tie_cluster_id=big["cluster_id"])  # rank 1 + rank 3 of the cluster: refused (not top two)
    with pytest.raises(ApprovalError, match="not one of the top-2"):
        validate_approval(ws, exp)
    human_approval(ws, exp, big["proposable_for_holdout"], near_tie_cluster_id=big["cluster_id"])
    assert validate_approval(ws, exp)["approved_configs"] == big["proposable_for_holdout"]
    ws.approvals.joinpath(f"{exp}_SELECTION_HOLDOUT_APPROVAL.yaml").unlink()


# ---------------------------------------------------------------- report + status + no new trials
def test_the_is_report_surfaces_configuration_uncertainty_and_never_chooses(near):
    ws, exp, _ = near
    md = (experiment_dir(ws, exp) / "results" / "IS_REPORT.md").read_text()
    assert "## NT. CONFIGURATION UNCERTAINTY / NEAR-TIES" in md and "NEAR-TIE CLUSTER 01" in md
    for needle in ("config ID", "median std uplift", "campaign BH q", "campaign Bonf p", "positive years", "positive folds", "paired weekly-block CI",
                   "reason classified as near-tie", "median selected-effect difference", "IS evidence does not clearly distinguish",
                   "The engine does not choose one automatically", "(A) choose one configuration directly", "(B) approve at most the top 2", "(C) decline"):
        assert needle in md, needle
    assert "SELECTION HOLDOUT status = NOT ACCESSED" in md
    j = report(ws, exp)["NT_configuration_uncertainty"]
    assert j["label"] == "CONFIGURATION UNCERTAINTY / NEAR-TIES" and j["clusters"] and "creates no selection trial" in j["note"]
    assert reg.experiment_row(ws, exp)["status"] == "NEAR_TIE_REVIEW_REQUIRED"


def test_no_near_tie_means_a_direct_human_choice_status(clear):
    ws, exp, _ = clear
    assert report(ws, exp)["NT_configuration_uncertainty"]["clusters"] == []
    assert reg.experiment_row(ws, exp)["status"] == "AWAITING_HUMAN_FINAL_CONFIG_SELECTION"
    assert "No near-tie among" in (experiment_dir(ws, exp) / "results" / "IS_REPORT.md").read_text()


# 31 (25 in the spec). near-tie bootstrap comparisons create no selection trial; the DEVELOPMENT count stays exactly 24
def test_near_tie_diagnostics_create_no_selection_trials_and_cannot_promote(near):
    ws, exp, _ = near
    before = reg.read_trials(ws).copy()
    nt.detect(ws, exp)
    after = reg.read_trials(ws)
    assert len(before) == len(after) == 24 and before.equals(after)
    assert reg.integrity_check(ws)["selection_trials"] == 24
    t = reg.experiment_trials(ws, exp)
    rej = t[t["target"].isin(["DIR_RETURN_180", "DIR_PATH_SKEW_60"])]
    assert len(rej) == 12 and not rej["decision"].eq("IS_SHORTLIST_ELIGIBLE").any()                 # never promoted by being "close" to an eligible config
    assert proposable(ws, exp, 0) and len(proposable(ws, exp, 0)) == 2
