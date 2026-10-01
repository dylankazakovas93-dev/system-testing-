import json
import numpy as np
import os
import shutil
from pathlib import Path

import pandas as pd
import pytest

from engine import trial_registry as reg
from engine.common import CODE_ROOT, EngineError, load_frozen
from tests.scenario_helpers import PARTS, fake_results, new_frozen_experiment
from engine.experiment_lifecycle import (MANIFEST, MutationDetected, create_experiment, experiment_dir, freeze,
                                         validate_experiment, verify_manifest)
from engine.event_contract import EventSpecError

F = load_frozen()


@pytest.fixture()
def ws(tmp_path):
    return reg.Workspace(tmp_path / "ws").init()


def make_valid(ws, exp_id):
    """Edit the template into a valid spec (what the event-writing user would do)."""
    d = experiment_dir(ws, exp_id)
    p = d / "EVENT_SPEC.yaml"
    p.write_text(p.read_text().replace("TODO: one or two sentences.", "A confirmed pivot is followed by a path."))
    return d


def test_exactly_24_trials_product_and_ids():
    specs = reg.trial_specs(F)
    assert len(specs) == 24
    assert len({(s["target"], s["model"], s["state"]) for s in specs}) == 24
    assert {s["target"] for s in specs} == {"DIR_RETURN_15", "DIR_RETURN_30", "DIR_RETURN_60", "DIR_PATH_SKEW_60"}
    assert {s["model"] for s in specs} == {"RIDGE", "SPLINE", "XGB"}
    assert {s["state"] for s in specs} == {"UPPER_HALF", "LOWER_HALF"}
    assert reg.trial_id("EXP_0001", 0) == "EXP_0001_T01" and reg.trial_id("EXP_0001", 23) == "EXP_0001_T24"
    assert F.trial_policy["expected_trials_per_experiment"] == 24
    assert "max_trials" not in {k.lower() for k in F.trial_policy}        # no generic MAX_TRIALS


def test_freeze_preregisters_24_trials_before_results_and_locks(ws):
    exp = create_experiment(ws, new_campaign="C001", partitions=PARTS)
    assert exp == "EXP_0001"
    assert reg.read_trials(ws).empty                                     # nothing registered before freeze
    d = make_valid(ws, exp)
    man = freeze(ws, exp)
    t = reg.experiment_trials(ws, exp)
    assert len(t) == 24 and (t["status"] == "PREREGISTERED").all() and (t["decision"] == "PENDING").all()
    assert t["raw_p"].isna().all()                                       # no result exists at registration
    assert set(t["event_hash"]) == {man["event_hash"]} and t["feature_bank_hash"].nunique() == 1
    assert t["trial_policy_hash"].iloc[0] == F.hashes()["trial_policy_hash"]
    assert (d / MANIFEST).exists()
    assert not os.access(d / "event.py", os.W_OK) or os.geteuid() == 0   # read-only (root ignores mode)
    assert reg.experiment_row(ws, exp)["status"] == "FROZEN"
    assert reg.integrity_check(ws)["selection_trials"] == 24


def test_no_api_path_to_trial_25(ws):
    exp = create_experiment(ws, new_campaign="C001", partitions=PARTS)
    make_valid(ws, exp)
    freeze(ws, exp)
    with pytest.raises(EngineError):                                     # cannot preregister twice
        reg.preregister_trials(ws, exp, event_hash="x", manifest_hash="y", hashes=F.hashes(), frozen=F)
    with pytest.raises(EngineError):                                     # cannot freeze twice
        freeze(ws, exp)
    public = [n for n in dir(reg) if not n.startswith("_") and callable(getattr(reg, n))]
    creators = [n for n in public if "trial" in n and n.startswith(("add_", "create_", "new_", "append_"))]
    assert creators == []                                                # no add_trial / create_trial API
    # hand-edited CSV with a 25th row is DETECTED
    df = reg.read_trials(ws)
    extra = df.iloc[[0]].copy()
    extra["trial_id"] = "EXP_0001_T25"
    reg._write(ws.path("selection_trials.csv"), pd.concat([df, extra], ignore_index=True), reg.TRIAL_COLS)
    with pytest.raises(reg.RegistryIntegrityError):
        reg.integrity_check(ws)


def test_reveal_requires_exactly_the_24_preregistered_trials(ws):
    exp = create_experiment(ws, new_campaign="C001", partitions=PARTS)
    make_valid(ws, exp); freeze(ws, exp)
    ok = fake_results(ws, exp)
    ids = list(ok)
    with pytest.raises(reg.RegistryIntegrityError):                      # 25 results, one unregistered
        reg.reveal_experiment(ws, exp, {**ok, "EXP_0001_T25": dict(ok[ids[0]])}, train_period="a", validation_period="b", frozen=F)
    with pytest.raises(reg.RegistryIntegrityError):                      # only 23
        reg.reveal_experiment(ws, exp, {i: ok[i] for i in ids[:23]}, train_period="a", validation_period="b", frozen=F)
    reg.reveal_experiment(ws, exp, ok, train_period="a", validation_period="b", frozen=F)
    with pytest.raises(EngineError, match="already revealed"):           # one reveal only
        reg.reveal_experiment(ws, exp, ok, train_period="a", validation_period="b", frozen=F)


def test_campaign_rejects_experiment_21(ws):
    reg.create_campaign(ws, "C001", PARTS, F)
    for i in range(20):
        assert reg.register_experiment(ws, "C001", frozen=F) == f"EXP_{i + 1:04d}"
    with pytest.raises(reg.CampaignLimitExceeded):
        reg.register_experiment(ws, "C001", frozen=F)
    with pytest.raises(reg.CampaignLimitExceeded):
        create_experiment(ws, campaign_id="C001")
    # an explicit new campaign is the only way forward; numbering continues globally
    assert create_experiment(ws, new_campaign="C002", partitions={"development_end": "2025-01-01", "oos_end": "2026-01-01", "lockbox_start": "2026-01-01"}) == "EXP_0021"
    s = reg.campaign_summary(ws, "C001", F)
    assert s["experiments_used"] == 20 and s["selection_trials_max"] == 480 == 20 * 24


def test_lineage_consumes_a_new_slot_and_never_overwrites(ws):
    e1 = create_experiment(ws, new_campaign="C001", partitions=PARTS)
    make_valid(ws, e1); freeze(ws, e1)
    e2 = create_experiment(ws, campaign_id="C001", lineage_parent=e1)
    assert e2 != e1 and (experiment_dir(ws, e2) / "LINEAGE.md").exists()
    assert reg.campaign_summary(ws, "C001", F)["experiments_used"] == 2
    assert verify_manifest(ws, e1)["errors"] == []                       # parent untouched


def test_mutation_after_freeze_is_detected(ws):
    exp = create_experiment(ws, new_campaign="C001", partitions=PARTS)
    d = make_valid(ws, exp); freeze(ws, exp)
    assert verify_manifest(ws, exp)["errors"] == []
    ev = d / "event.py"
    os.chmod(ev, 0o644)
    ev.write_text(ev.read_text() + "\n# tweak\n")
    with pytest.raises(MutationDetected, match="event.py changed"):
        verify_manifest(ws, exp)
    shutil.copy(CODE_ROOT / "templates/experiment/event.py", ev)


def test_spec_frozen_file_and_manifest_tampering_detected(ws, monkeypatch):
    exp = create_experiment(ws, new_campaign="C001", partitions=PARTS)
    d = make_valid(ws, exp); freeze(ws, exp)
    spec = d / "EVENT_SPEC.yaml"; os.chmod(spec, 0o644)
    original = spec.read_text()
    mutated = original.replace("pivot_left: 30", "pivot_left: 31", 1)
    assert mutated != original                                           # the mutation must really change the file
    spec.write_text(mutated)
    assert any("EVENT_SPEC.yaml changed" in e for e in verify_manifest(ws, exp, raise_on_error=False)["errors"])
    # manifest edited
    man = d / MANIFEST; os.chmod(man, 0o644)
    m = json.loads(man.read_text()); m["hashes"]["event_py"] = "0" * 64
    man.write_text(json.dumps(m))
    errs = verify_manifest(ws, exp, raise_on_error=False)["errors"]
    assert any("manifest was edited" in e.lower() or "FROZEN_MANIFEST.json was edited" in e for e in errs)


def test_frozen_yaml_change_detected(ws, monkeypatch):
    """Simulate an edit of a frozen spec WITHOUT touching the real file (other tests hash it concurrently)."""
    import engine.experiment_lifecycle as lc
    exp = create_experiment(ws, new_campaign="C001", partitions=PARTS)
    make_valid(ws, exp); freeze(ws, exp)
    real = lc.sha256_file
    monkeypatch.setattr(lc, "sha256_file", lambda p: "0" * 64 if Path(p).name == "ACCEPTANCE_RULES.yaml" else real(p))
    errs = verify_manifest(ws, exp, raise_on_error=False)["errors"]
    assert any("frozen specification changed after freeze" in e and "ACCEPTANCE_RULES.yaml" in e for e in errs)
    monkeypatch.setattr(lc, "sha256_file", real)
    assert verify_manifest(ws, exp)["errors"] == []


def test_freeze_rejects_invalid_specs(ws):
    exp = create_experiment(ws, new_campaign="C001", partitions=PARTS)
    d = experiment_dir(ws, exp)
    with pytest.raises(EventSpecError, match="hypothesis"):              # template still has TODO
        freeze(ws, exp)
    assert reg.experiment_row(ws, exp)["status"] == "DRAFT" and reg.read_trials(ws).empty


def test_spec_validation_rules(ws):
    import yaml
    from engine.event_contract import validate_spec
    base = yaml.safe_load((CODE_ROOT / "templates/experiment/EVENT_SPEC.yaml").read_text())
    base["experiment_id"], base["campaign_id"] = "EXP_0001", "C001"
    base["partitions"] = dict(PARTS)
    base["hypothesis"] = "A sufficiently long and real hypothesis sentence."
    assert validate_spec(base, F) == []
    def bad(mut, needle):
        s = json.loads(json.dumps(base)); mut(s)
        errs = validate_spec(s, F)
        assert any(needle in e for e in errs), (needle, errs)
    bad(lambda s: s.pop("cooldown"), "missing required keys")
    bad(lambda s: s.pop("partitions"), "missing required keys")
    bad(lambda s: s["partitions"].update(oos_end="2022-06-01"), "development_end < oos_end <= lockbox_start")
    bad(lambda s: s["partitions"].update(development_end="2024-06-01"), "development_end < oos_end <= lockbox_start")
    bad(lambda s: s["partitions"].update(lockbox_start="2023-06-01"), "development_end < oos_end <= lockbox_start")
    bad(lambda s: s["direction_definition"].update(values=[1, -1]), "ONE direction per experiment")
    bad(lambda s: s.update(filter_ladder=["CONDITION_1", "FINAL_EVENT"]), "filter_ladder")
    bad(lambda s: s.update(filter_ladder=["BASE_TRIGGER", "FINAL_EVENT", "BASE_TRIGGER"]), "filter_ladder")
    bad(lambda s: s.update(sensitivity_parameters=["pivot_left", "pivot_right", "x"]), "at most")
    bad(lambda s: s.update(sensitivity_parameters=["nope"]), "not in base_parameters")
    bad(lambda s: s["base_parameters"].update(pivot_left=2), "must be >= 3")
    bad(lambda s: s["eligible_session"].update(start="09:30"), "eligible_session must satisfy")
    bad(lambda s: s["eligible_session"].update(end="16:30"), "eligible_session must satisfy")
    bad(lambda s: s["indicator"]["inputs"].update(pivot_left=7), "not registered")
    bad(lambda s: s.update(deduplication_rule="whatever"), "deduplication_rule")
    bad(lambda s: s["base_parameters"].update(pivot_left="five"), "base_parameters")
    bad(lambda s: s["direction_definition"].update(values=[0, 2]), "direction_definition")
    bad(lambda s: s.pop("indicator"), "indicator block")
    bad(lambda s: s["expected_information_time"].update(confirmation_delay_bars="ghost"), "confirmation_delay_bars")


def test_observations_reference_experiment_and_cannot_promote(ws):
    exp = create_experiment(ws, new_campaign="C001", partitions=PARTS)
    oid = reg.add_observation(ws, exp, "top_decile", "top decile unusually strong", "decile10_mean", 0.05)
    o = reg.read_observations(ws)
    assert o.iloc[0]["experiment_id"] == exp and o.iloc[0]["eligible_for_promotion"] == "False"
    assert "CANNOT INFLUENCE PROMOTION" in o.iloc[0]["note"]
    with pytest.raises(EngineError):
        reg.add_observation(ws, "EXP_9999", "x", "y")
    assert reg.integrity_check(ws)["observations"] == 1


# ============================ partitions, opportunity numbers, multiplicity, ledgers ================================
def test_partitions_are_frozen_in_the_manifest_and_hashed(ws):
    exp = create_experiment(ws, new_campaign="C001", partitions=PARTS)
    d = make_valid(ws, exp)
    man = freeze(ws, exp)
    assert man["partitions"] == PARTS and len(man["partitions_hash"]) == 64
    import yaml
    from engine.partitions import parse_partitions
    assert parse_partitions(yaml.safe_load((d / "EVENT_SPEC.yaml").read_text())["partitions"]).hash() == man["partitions_hash"]
    # moving a boundary after freeze is detected (spec hash AND partitions hash)
    spec = d / "EVENT_SPEC.yaml"; os.chmod(spec, 0o644)
    spec.write_text(spec.read_text().replace('development_end: "2023-01-01"', 'development_end: "2022-06-01"'))
    errs = verify_manifest(ws, exp, raise_on_error=False)["errors"]
    assert any("partitions changed after freeze" in e for e in errs) and any("EVENT_SPEC.yaml changed" in e for e in errs)


def test_experiment_partitions_must_equal_the_campaign_partitions(ws):
    exp = create_experiment(ws, new_campaign="C001", partitions=PARTS)
    d = make_valid(ws, exp)
    spec = d / "EVENT_SPEC.yaml"
    spec.write_text(spec.read_text().replace('oos_end: "2024-01-01"', 'oos_end: "2023-09-01"'))
    with pytest.raises(EventSpecError, match="differ from the campaign"):
        freeze(ws, exp)


def test_new_campaign_requires_explicit_partitions_and_never_infers_them(ws):
    with pytest.raises(EngineError, match="explicit partitions"):
        create_experiment(ws, new_campaign="C001")
    from engine.partitions import PartitionError
    with pytest.raises(PartitionError):
        reg.create_campaign(ws, "C009", {"development_end": "2023-01-01", "oos_end": "2022-01-01", "lockbox_start": "2024-01-01"}, F)
    with pytest.raises(PartitionError):
        reg.create_campaign(ws, "C009", {"development_end": "2023-01-01", "oos_end": "2024-01-01"}, F)
    assert reg.read_campaigns(ws).empty


def test_selection_opportunity_numbers_are_preregistered_and_unique_per_campaign(ws):
    e1 = new_frozen_experiment(ws)
    e2 = new_frozen_experiment(ws)
    t1, t2 = reg.experiment_trials(ws, e1), reg.experiment_trials(ws, e2)
    assert t1["selection_opportunity_number"].tolist() == list(range(1, 25))
    assert t2["selection_opportunity_number"].tolist() == list(range(25, 49))
    assert (t1["status"] == "PREREGISTERED").all() and t1["raw_p"].isna().all()           # numbers exist before any result
    assert t1["manifest_hash"].nunique() == 1 and t1["manifest_hash"].iloc[0] != t2["manifest_hash"].iloc[0]


def test_bonferroni_uses_all_24_and_campaign_bonferroni_uses_24E_and_is_retroactive(ws):
    from engine.multiplicity import benjamini_hochberg
    e1 = new_frozen_experiment(ws)
    r1 = fake_results(ws, e1, {("DIR_RETURN_30", "RIDGE"): 0.0005})
    reg.reveal_experiment(ws, e1, r1, train_period="a", validation_period="b", frozen=F)
    t1 = reg.experiment_trials(ws, e1)
    raw = t1["raw_p"].to_numpy()
    assert np.allclose(t1["experiment_bonferroni_p"], np.minimum(raw * 24, 1.0))              # universe = all 24, not survivors
    assert np.allclose(t1["campaign_bonferroni_p"], np.minimum(raw * 24, 1.0))                # E = 1 -> 24
    assert np.allclose(t1["experiment_q"], benjamini_hochberg(raw))
    assert (t1["cumulative_campaign_selection_trials"] == 24).all()
    e2 = new_frozen_experiment(ws)
    r2 = fake_results(ws, e2, {}, default_p=0.5)
    reg.reveal_experiment(ws, e2, r2, train_period="a", validation_period="b", frozen=F)
    t1b, t2 = reg.experiment_trials(ws, e1), reg.experiment_trials(ws, e2)
    assert np.allclose(t1b["campaign_bonferroni_p"], np.minimum(t1b["raw_p"] * 48, 1.0))      # OLD experiment updated: 24 x 2
    assert np.allclose(t2["campaign_bonferroni_p"], np.minimum(t2["raw_p"] * 48, 1.0))
    allp = np.r_[t1b["raw_p"].to_numpy(), t2["raw_p"].to_numpy()]
    assert np.allclose(np.r_[t1b["campaign_q"].to_numpy(), t2["campaign_q"].to_numpy()], benjamini_hochberg(allp))
    assert np.allclose(t1b["experiment_bonferroni_p"], t1["experiment_bonferroni_p"])           # experiment-level values never move
    assert (t1b["cumulative_campaign_selection_trials"] == 24).all() and (t2["cumulative_campaign_selection_trials"] == 48).all()
    e3 = new_frozen_experiment(ws)
    reg.reveal_experiment(ws, e3, fake_results(ws, e3, {}, default_p=0.5), train_period="a", validation_period="b", frozen=F)
    t1c = reg.experiment_trials(ws, e1)
    assert np.allclose(t1c["campaign_bonferroni_p"], np.minimum(t1c["raw_p"] * 72, 1.0))       # E = 3 -> 72, still e1's rows
    s = reg.campaign_summary(ws, "C001", F)
    assert s["selection_trials_revealed"] == s["statistical_selection_opportunities_exposed"] == 72


def test_retroactive_campaign_adjustment_can_remove_eligibility_of_an_earlier_candidate(ws):
    from engine.acceptance import PROVISIONAL, SHORTLIST
    from tests.scenario_helpers import pass_all_paths, pass_sensitivity
    e1 = new_frozen_experiment(ws)
    pairs = {("DIR_RETURN_30", m): 0.0009 for m in ("RIDGE", "SPLINE", "XGB")}
    reg.reveal_experiment(ws, e1, fake_results(ws, e1, pairs), train_period="a", validation_period="b", frozen=F)
    pass_all_paths(ws, e1); pass_sensitivity(ws, e1)
    t = reg.experiment_trials(ws, e1)
    up = t[(t["target"] == "DIR_RETURN_30") & (t["state"] == "UPPER_HALF")]
    assert (up["decision"] == SHORTLIST).all()                                    # 0.0009 * 24 = 0.0216 <= 0.05
    assert reg.experiment_row(ws, e1)["is_status"] == SHORTLIST and reg.experiment_row(ws, e1)["status"] == "AWAITING_HUMAN_OOS_APPROVAL"
    for _ in range(2):                                                            # 2 more experiments with nothing significant
        e = new_frozen_experiment(ws)
        reg.reveal_experiment(ws, e, fake_results(ws, e, {}, default_p=0.5, good=False), train_period="a", validation_period="b", frozen=F)
    t = reg.experiment_trials(ws, e1)
    up = t[(t["target"] == "DIR_RETURN_30") & (t["state"] == "UPPER_HALF")]
    assert np.allclose(up["campaign_bonferroni_p"], 0.0009 * 72)                  # 0.0648 > 0.05 -> lost eligibility
    assert (up["decision"] == PROVISIONAL).all() and "campaign-level gates" in up["rejection_reason"].iloc[0]
    assert reg.experiment_row(ws, e1)["is_status"] == PROVISIONAL
    assert reg.experiment_row(ws, e1)["status"] == "IS_PROVISIONAL_CANDIDATE"      # no longer awaiting OOS approval


def test_ledger_detects_missing_duplicate_extra_changed_and_edited_trials(ws):
    exp = new_frozen_experiment(ws)
    reg.reveal_experiment(ws, exp, fake_results(ws, exp), train_period="a", validation_period="b", frozen=F)
    assert reg.integrity_check(ws)["revealed_trials"] == 24
    good = reg.read_trials(ws)
    path = ws.path("selection_trials.csv")

    def corrupt(mut, needle):
        df = good.copy(); mut(df)
        reg._write(path, df, reg.TRIAL_COLS)
        with pytest.raises(reg.RegistryIntegrityError):
            reg.integrity_check(ws)
        reg._write(path, good, reg.TRIAL_COLS)
        assert reg.integrity_check(ws)

    def drop(df): df.drop(index=df.index[5], inplace=True)                                 # missing trial
    corrupt(drop, "missing")
    def dup(df): df.loc[df.index[3], "trial_id"] = df.loc[df.index[2], "trial_id"]         # duplicate trial id
    corrupt(dup, "duplicate")
    def spec(df): df.loc[df.index[0], "model"] = "LASSO"                                    # changed trial spec
    corrupt(spec, "spec")
    def t25(df):
        row = df.iloc[[0]].copy(); row["trial_id"] = "EXP_0001_T25"; df.loc[len(df)] = row.iloc[0]
    corrupt(t25, "25")
    def edit(df): df.loc[df.index[7], "uplift"] = "0.123456"                                # edited historical result
    corrupt(edit, "edited")
    def edit_p(df): df.loc[df.index[7], "raw_p"] = "0.0001"
    corrupt(edit_p, "edited p")
    def edit_ok_field(df): df.loc[df.index[7], "campaign_q"] = "0.5"                        # retroactive field: legitimately recomputed
    df = good.copy(); edit_ok_field(df); reg._write(path, df, reg.TRIAL_COLS)
    assert reg.integrity_check(ws)["revealed_trials"] == 24
    reg._write(path, good, reg.TRIAL_COLS)


def test_oos_access_ledger_is_append_only_and_integrity_checked(ws):
    e1 = new_frozen_experiment(ws, "C001"); e2 = new_frozen_experiment(ws, "C001")
    reg.create_campaign(ws, "C002", {"development_end": "2024-01-01", "oos_end": "2025-01-01", "lockbox_start": "2025-01-01"})
    kw = dict(freeze_hash="a", open_approval_file_hash="b", experiments="E", approved_experiment_groups="E:G", n_oos_confirmations=3,
              oos_start="2023-01-01", oos_end="2024-01-01", unlock_timestamp="t", code_hash="h")
    r1 = reg.append_oos_access(ws, campaign_id="C001", **kw)
    assert r1["prev_row_hash"] == "GENESIS" and reg.oos_spent(ws, e1) and reg.oos_spent(ws, e2)    # accounting is campaign-wide
    with pytest.raises(EngineError, match="CAMPAIGN OOS HAS BEEN SPENT"):
        reg.append_oos_access(ws, campaign_id="C001", **kw)                             # ONE opening per campaign, ever
    r2 = reg.append_oos_access(ws, campaign_id="C002", **kw)
    assert r2["prev_row_hash"] == r1["row_hash"] and reg.verify_oos_ledger(ws) == 2
    reg.update_campaign(ws, "C001", status="OOS_SPENT"); reg.update_campaign(ws, "C002", status="OOS_SPENT")
    good = reg.read_oos_access(ws)
    path = ws.path("oos_access.csv")
    for mut in (lambda d: d.loc[d.index[0], "freeze_hash"].__class__ and d.__setitem__("freeze_hash", ["x", "y"]),   # edited row
                lambda d: d.drop(index=d.index[0], inplace=True),                                                            # removed row
                lambda d: d.iloc[::-1].reset_index(drop=True).pipe(lambda x: [d.__setitem__(c, x[c].to_numpy()) for c in d.columns])):  # reordered
        df = good.copy(); mut(df)
        reg._write(path, df, reg.OOS_ACCESS_COLS)
        with pytest.raises(reg.RegistryIntegrityError):
            reg.integrity_check(ws)
        reg._write(path, good, reg.OOS_ACCESS_COLS)
    assert reg.integrity_check(ws)["oos_unlocks"] == 2


def test_exploratory_analysis_must_be_diagnostic_only_and_cannot_alter_status(ws):
    exp = new_frozen_experiment(ws)
    reg.reveal_experiment(ws, exp, fake_results(ws, exp, {}, default_p=0.5, good=False), train_period="a", validation_period="b", frozen=F)
    before_trials = reg.read_trials(ws).to_csv()
    before = reg.experiment_row(ws, exp)
    with pytest.raises(EngineError, match="SELECTION OPPORTUNITY"):
        reg.log_exploratory_observation(ws, exp, "what if ER_120 > 0.7", diagnostic_only=False)
    with pytest.raises(EngineError):
        reg.log_exploratory_observation(ws, exp, "what if ER_120 > 0.7", diagnostic_only="yes")
    oid = reg.log_exploratory_observation(ws, exp, "ER_120 appears unusually important", diagnostic_only=True)
    o = reg.read_observations(ws).iloc[-1]
    assert o["observation_id"] == oid and o["diagnostic_label"] == "DIAGNOSTIC ONLY — NOT A SELECTION TRIAL" and o["eligible_for_promotion"] == "False"
    assert reg.read_trials(ws).to_csv() == before_trials                                   # no trial row touched
    after = reg.experiment_row(ws, exp)
    assert (after["status"], after["is_status"], after["trial_ledger_hash"]) == (before["status"], before["is_status"], before["trial_ledger_hash"])
    assert reg.integrity_check(ws)["observations"] == 1


def test_lifecycle_status_history_is_append_only_and_validated(ws):
    exp = new_frozen_experiment(ws)
    reg.reveal_experiment(ws, exp, fake_results(ws, exp, {}, default_p=0.5, good=False), train_period="a", validation_period="b", frozen=F)
    row = reg.experiment_row(ws, exp)
    assert row["status"] == "IS_REJECTED" and row["is_status"] == "IS_NO_CANDIDATE"
    hist = json.loads(row["status_history"])
    assert [h[0] for h in hist] == ["DRAFT", "FROZEN", "IS_REJECTED"]
    with pytest.raises(EngineError):
        reg.set_status(ws, exp, "TOTALLY_CONFIRMED")
    assert set(reg.LIFECYCLE) >= {"IS_REJECTED", "IS_PROVISIONAL_CANDIDATE", "AWAITING_HUMAN_OOS_APPROVAL", "OOS_NOT_APPROVED", "OOS_REJECTED",
                                  "OOS_CONFIRMED", "CPCV_REJECTED", "CPCV_CONFIRMED", "AWAITING_FINAL_LOCKBOX"}
