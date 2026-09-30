import json
import os
import shutil
from pathlib import Path

import pandas as pd
import pytest

from engine import trial_registry as reg
from engine.common import CODE_ROOT, EngineError, load_frozen
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
    exp = create_experiment(ws, new_campaign="C001", lockbox_start="2025-01-01")
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
    exp = create_experiment(ws, new_campaign="C001", lockbox_start="2025-01-01")
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
    exp = create_experiment(ws, new_campaign="C001", lockbox_start="2025-01-01")
    make_valid(ws, exp); freeze(ws, exp)
    ids = list(reg.experiment_trials(ws, exp)["trial_id"])
    empty = {k: 0 for k in ("n_parent", "n_selected", "parent_frequency", "selected_frequency", "retention_ratio",
             "parent_effect", "selected_effect", "uplift", "standardized_uplift", "bootstrap_ci_low",
             "bootstrap_ci_high", "raw_p", "positive_years", "eligible_years", "target_sd", "n_oos_weeks")}
    with pytest.raises(reg.RegistryIntegrityError):                      # 25 results, one unregistered
        reg.reveal_experiment(ws, exp, {**{i: dict(empty) for i in ids}, "EXP_0001_T25": dict(empty)},
                              train_period="a", oos_period="b", frozen=F)
    with pytest.raises(reg.RegistryIntegrityError):                      # only 23
        reg.reveal_experiment(ws, exp, {i: dict(empty) for i in ids[:23]}, train_period="a", oos_period="b", frozen=F)


def test_campaign_rejects_experiment_21(ws):
    reg.create_campaign(ws, "C001", "2025-01-01", F)
    for i in range(20):
        assert reg.register_experiment(ws, "C001", frozen=F) == f"EXP_{i + 1:04d}"
    with pytest.raises(reg.CampaignLimitExceeded):
        reg.register_experiment(ws, "C001", frozen=F)
    with pytest.raises(reg.CampaignLimitExceeded):
        create_experiment(ws, campaign_id="C001")
    # an explicit new campaign is the only way forward; numbering continues globally
    assert create_experiment(ws, new_campaign="C002", lockbox_start="2026-01-01") == "EXP_0021"
    s = reg.campaign_summary(ws, "C001", F)
    assert s["experiments_used"] == 20 and s["selection_trials_max"] == 480 == 20 * 24


def test_lineage_consumes_a_new_slot_and_never_overwrites(ws):
    e1 = create_experiment(ws, new_campaign="C001", lockbox_start="2025-01-01")
    make_valid(ws, e1); freeze(ws, e1)
    e2 = create_experiment(ws, campaign_id="C001", lineage_parent=e1)
    assert e2 != e1 and (experiment_dir(ws, e2) / "LINEAGE.md").exists()
    assert reg.campaign_summary(ws, "C001", F)["experiments_used"] == 2
    assert verify_manifest(ws, e1)["errors"] == []                       # parent untouched


def test_mutation_after_freeze_is_detected(ws):
    exp = create_experiment(ws, new_campaign="C001", lockbox_start="2025-01-01")
    d = make_valid(ws, exp); freeze(ws, exp)
    assert verify_manifest(ws, exp)["errors"] == []
    ev = d / "event.py"
    os.chmod(ev, 0o644)
    ev.write_text(ev.read_text() + "\n# tweak\n")
    with pytest.raises(MutationDetected, match="event.py changed"):
        verify_manifest(ws, exp)
    shutil.copy(CODE_ROOT / "templates/experiment/event.py", ev)


def test_spec_frozen_file_and_manifest_tampering_detected(ws, monkeypatch):
    exp = create_experiment(ws, new_campaign="C001", lockbox_start="2025-01-01")
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
    exp = create_experiment(ws, new_campaign="C001", lockbox_start="2025-01-01")
    make_valid(ws, exp); freeze(ws, exp)
    real = lc.sha256_file
    monkeypatch.setattr(lc, "sha256_file", lambda p: "0" * 64 if Path(p).name == "ACCEPTANCE_RULES.yaml" else real(p))
    errs = verify_manifest(ws, exp, raise_on_error=False)["errors"]
    assert any("frozen specification changed after freeze" in e and "ACCEPTANCE_RULES.yaml" in e for e in errs)
    monkeypatch.setattr(lc, "sha256_file", real)
    assert verify_manifest(ws, exp)["errors"] == []


def test_freeze_rejects_invalid_specs(ws):
    exp = create_experiment(ws, new_campaign="C001", lockbox_start="2025-01-01")
    d = experiment_dir(ws, exp)
    with pytest.raises(EventSpecError, match="hypothesis"):              # template still has TODO
        freeze(ws, exp)
    assert reg.experiment_row(ws, exp)["status"] == "DRAFT" and reg.read_trials(ws).empty


def test_spec_validation_rules(ws):
    import yaml
    from engine.event_contract import validate_spec
    base = yaml.safe_load((CODE_ROOT / "templates/experiment/EVENT_SPEC.yaml").read_text())
    base["experiment_id"], base["campaign_id"] = "EXP_0001", "C001"
    base["hypothesis"] = "A sufficiently long and real hypothesis sentence."
    assert validate_spec(base, F) == []
    def bad(mut, needle):
        s = json.loads(json.dumps(base)); mut(s)
        errs = validate_spec(s, F)
        assert any(needle in e for e in errs), (needle, errs)
    bad(lambda s: s.pop("cooldown"), "missing required keys")
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
    exp = create_experiment(ws, new_campaign="C001", lockbox_start="2025-01-01")
    oid = reg.add_observation(ws, exp, "top_decile", "top decile unusually strong", "decile10_mean", 0.05)
    o = reg.read_observations(ws)
    assert o.iloc[0]["experiment_id"] == exp and o.iloc[0]["eligible_for_promotion"] == "False"
    assert "CANNOT INFLUENCE PROMOTION" in o.iloc[0]["note"]
    with pytest.raises(EngineError):
        reg.add_observation(ws, "EXP_9999", "x", "y")
    assert reg.integrity_check(ws)["observations"] == 1
