"""Hard data-partition guard: DEVELOPMENT rows only reach research code; poisoned OOS / lockbox prices change nothing."""
import hashlib
import json
import textwrap
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import engine.experiment_runner as runner
from engine import trial_registry as reg
from engine.common import EngineError, load_frozen
from engine.experiment_lifecycle import create_experiment, experiment_dir, freeze
from engine.partitions import (PartitionError, Partitions, development_view, load_bars_before, oos_view, parse_partitions)
from engine.synthetic import make_bars

F = load_frozen()
P = {"development_end": "2018-01-01", "oos_end": "2018-07-01", "lockbox_start": "2018-10-01"}


def test_partition_parsing_validates_chronology_and_hashes():
    p = parse_partitions(P)
    assert p.development_end < p.oos_end < p.lockbox_start and len(p.hash()) == 64
    assert parse_partitions(dict(P)).hash() == p.hash() != parse_partitions({**P, "oos_end": "2018-08-01"}).hash()
    for bad in ({**P, "oos_end": "2017-06-01"}, {**P, "lockbox_start": "2018-03-01"}, {**P, "development_end": "2018-07-01"},
                {"development_end": "2018-01-01"}, {**P, "extra": "2019-01-01"}, {**P, "oos_end": "not-a-date"}):
        with pytest.raises(PartitionError):
            parse_partitions(bad)
    assert parse_partitions({**P, "oos_end": "2018-10-01"}).oos_end == parse_partitions(P).lockbox_start      # oos_end == lockbox_start allowed


def three_stage_bars():
    return make_bars(n_days=820, seed=3)                                  # 2016-01-04 .. ~2019-02


def test_development_view_physically_removes_oos_and_lockbox_rows():
    bars = three_stage_bars()
    p = parse_partitions(P)
    dev = development_view(bars, p)
    assert dev.index.max() < p.development_end and len(dev) < len(bars)
    assert len(dev) == int((bars.index < p.development_end).sum())
    ov = oos_view(bars, p)
    assert ov.index.max() < pd.Timestamp("2018-07-01", tz="UTC") and len(ov) > len(dev)
    assert not (ov.index >= p.oos_end).any() and not (ov.index >= p.lockbox_start).any()          # lockbox never in any view


def test_file_loader_never_materialises_rows_after_the_cutoff(tmp_path):
    bars = three_stage_bars()
    path = tmp_path / "bars.parquet"
    bars.reset_index().rename(columns={"index": "timestamp"}).to_parquet(path)
    cutoff = pd.Timestamp("2018-01-01", tz="UTC")
    got = load_bars_before(path, cutoff)
    assert got.index.max() < cutoff and len(got) == int((bars.index < cutoff).sum())
    csv = tmp_path / "bars.csv"
    bars.reset_index().rename(columns={"index": "timestamp"}).to_csv(csv, index=False)
    assert len(load_bars_before(csv, cutoff)) == len(got)


EVENT_SRC = """
import numpy as np
import pandas as pd


def detect_events(bars, params):
    step = int(params["every_n_bars"])
    interval = pd.Timedelta(bars.attrs["bar_interval"])
    keep = np.arange(len(bars)) % step == 0
    return pd.DataFrame({"event_time": bars.index[keep] + interval, "direction": np.ones(int(keep.sum()), dtype=int)})
"""


def make_experiment(ws, parts=P):
    exp = create_experiment(ws, new_campaign="C001", partitions=parts)
    d = experiment_dir(ws, exp)
    (d / "event.py").write_text(EVENT_SRC)
    (d / "EVENT_SPEC.yaml").write_text(textwrap.dedent(f"""
        experiment_id: {exp}
        campaign_id: C001
        hypothesis: "Every 90th bar is an event; a guard test for the partition boundary."
        partitions: {{development_end: "{parts['development_end']}", oos_end: "{parts['oos_end']}", lockbox_start: "{parts['lockbox_start']}"}}
        instrument: NQ_1m
        data_interval: 1min
        eligible_session: {{start: "09:31", end: "15:00"}}
        direction_definition: {{rule: "always long", values: [1]}}
        event_condition: {{description: "every n-th bar", parameters_used: [every_n_bars]}}
        deduplication_rule: keep_first_per_event_time
        cooldown: {{bars: 0}}
        base_parameters: {{every_n_bars: 90}}
        sensitivity_parameters: []
        expected_information_time: {{rule: "completion time of the n-th bar", confirmation_delay_bars: 0}}
    """))
    freeze(ws, exp)
    return exp


def poison(bars, p):
    """Wreck OOS and lockbox prices, add NaN, absurd volumes and an extra post-lockbox tail."""
    b = bars.copy()
    late = b.index.tz_convert("UTC") >= p.development_end
    rng = np.random.default_rng(1)
    b.loc[late, ["open", "high", "low", "close"]] = rng.uniform(1, 1e6, size=(int(late.sum()), 4))
    b.loc[late, "volume"] = -5.0
    b.iloc[-50:, b.columns.get_loc("close")] = np.nan
    return b


@pytest.fixture(scope="module")
def two_runs(tmp_path_factory):
    """The IS stage run twice in identical workspaces: on clean bars and on bars whose OOS/lockbox rows are poisoned."""
    bars = three_stage_bars()
    p = parse_partitions(P)
    seen = {}
    outs = {}
    for label, data in (("clean", bars), ("poisoned", poison(bars, p))):
        ws = reg.Workspace(tmp_path_factory.mktemp(label)).init()
        exp = make_experiment(ws)
        recorded = []
        def spy(name, fn):
            def wrapped(b, *a, **k):
                recorded.append((name, b.index.tz_convert("UTC").max(), len(b)))
                return fn(b, *a, **k)
            return wrapped
        import pytest as _pt
        mp = _pt.MonkeyPatch()
        for name in ("compute_features", "compute_primary_targets", "check_event_causality", "generate_events"):
            fn = getattr(runner, name)
            mp.setattr(runner, name, spy(name, fn) if name in ("compute_features", "compute_primary_targets") else
                       (lambda n, f: (lambda m, b, *a, **k: (recorded.append((n, b.index.tz_convert("UTC").max(), len(b))), f(m, b, *a, **k))[1]))(name, fn))
        try:
            out = runner.run_experiment(ws, exp, data, verbose=False, run_sensitivity_stage=False)
        finally:
            mp.undo()
        outs[label] = (ws, exp, out)
        seen[label] = recorded
    return outs, seen, p


def test_is_runner_hands_research_code_development_rows_only(two_runs):
    outs, seen, p = two_runs
    for label in ("clean", "poisoned"):
        assert seen[label], "spies recorded nothing"
        for name, last_ts, n in seen[label]:
            assert last_ts < p.development_end, (label, name, last_ts)               # event, feature, target code never saw OOS/lockbox
    assert {n for n, _, _ in seen["clean"]} >= {"compute_features", "compute_primary_targets", "check_event_causality", "generate_events"}
    assert outs["clean"][2]["base_event"]["rows_removed_before_research"] > 0


def test_poisoning_oos_and_lockbox_prices_cannot_alter_any_is_result_or_artifact(two_runs):
    outs, _, _ = two_runs
    (ws_a, exp_a, out_a), (ws_b, exp_b, out_b) = outs["clean"], outs["poisoned"]
    da, db = experiment_dir(ws_a, exp_a) / "results", experiment_dir(ws_b, exp_b) / "results"
    assert (da / "results.json").read_bytes() == (db / "results.json").read_bytes()                  # byte-identical IS bundle
    for f in sorted(da.glob("cv_*.csv")):
        assert f.read_bytes() == (db / f.name).read_bytes(), f.name                                  # every DEVELOPMENT_CV panel
    ta, tb = reg.experiment_trials(ws_a, exp_a), reg.experiment_trials(ws_b, exp_b)
    sealed = [c for c in reg.SEALED_TRIAL_FIELDS if c not in ("revealed_at", "manifest_hash")]
    assert ta[sealed].equals(tb[sealed])                                                              # registry result fields identical
    assert (ta["decision"] == tb["decision"]).all() and (ta["rejection_reason"] == tb["rejection_reason"]).all()
    ja, jb = json.loads((da / "IS_REPORT.json").read_text()), json.loads((db / "IS_REPORT.json").read_text())
    for k in ("E_data_period", "D_raw_event_frequency", "K_calendar_years", "L_development_cv_folds", "R_feature_diagnostics", "S_filter_ladder"):
        assert ja[k] == jb[k], k
    assert ja["X_hashes"]["is_data_fingerprint"] == jb["X_hashes"]["is_data_fingerprint"]
    def norm(md):
        return "\n".join(l for l in md.splitlines() if not l.startswith(("| manifest_sha256", "| manifest_hash", "| trial_ledger_hash")))
    assert norm((da / "IS_REPORT.md").read_text()) == norm((db / "IS_REPORT.md").read_text())        # plots/reports/diagnostics too
    oa = reg.read_observations(ws_a)[["category", "description"]]
    ob = reg.read_observations(ws_b)[["category", "description"]]
    assert oa.equals(ob)                                                                              # logged diagnostics identical


def test_changing_a_development_price_does_change_results_control(tmp_path_factory, two_runs):
    """Positive control: the comparison above has power - perturbing DEVELOPMENT rows does alter the IS fingerprint."""
    bars = three_stage_bars()
    p = parse_partitions(P)
    dev = development_view(bars, p)
    mutated = dev.copy()
    mutated.iloc[1000, mutated.columns.get_loc("close")] *= 1.01
    assert runner.bars_fingerprint(dev) != runner.bars_fingerprint(mutated)
    assert runner.bars_fingerprint(dev) == runner.bars_fingerprint(development_view(poison(bars, p), p))   # poison is invisible to IS


def test_is_runner_has_no_oos_code_path():
    import ast
    import inspect
    tree = ast.parse(inspect.getsource(runner))
    names = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Name):
            names.add(n.id)
        elif isinstance(n, ast.Attribute):
            names.add(n.attr)
        elif isinstance(n, ast.ImportFrom):
            names.add(n.module or "")
            names.update(a.name for a in n.names)
        elif isinstance(n, ast.Import):
            names.update(a.name for a in n.names)
    assert not ({"oos_view", "oos_stage", "run_campaign_oos", "execute_campaign_oos", "validate_approval", "approval_path", "cpcv", "run_cpcv"} & names)
    assert "development_view" in names
    assert "oos" not in " ".join(inspect.signature(runner.run_experiment).parameters).lower()
