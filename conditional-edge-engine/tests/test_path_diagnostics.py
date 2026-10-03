"""Forward-path / monetisation diagnostics (frozen/v1/PATH_DIAGNOSTICS.yaml): DIAGNOSTIC ONLY, never selection.

Pure-array tests use hand-computed examples and a brute-force reference; the class at the bottom runs the real IS pipeline on
bars (clean / SELECTION HOLDOUT-poisoned / lockbox-poisoned / path-stage-disabled) to prove the lifecycle wall and non-interference."""
import ast
import copy
import json
import tracemalloc
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import engine.experiment_runner as runner
from engine import path_diagnostics as pdx
from engine import trial_registry as reg
from engine.common import CODE_ROOT, EngineError, load_frozen
from engine.experiment_lifecycle import experiment_dir
from engine.partitions import parse_partitions
from engine.path_engine import (AMBIG, EXPIRED, STOP, TARGET, barrier_outcome, bracket_distances, bracket_pnl, compute_paths,
                                mfe_mae_log, path_eligibility, rv_ref, sigma_ref)
from engine.synthetic import make_bars
from tests.test_event_contract import LADDER_EVENT, module_from
from tests.test_ladder import ladder_spec
from tests.test_partition_guard import P, make_experiment, three_stage_bars

F = load_frozen()
SPEC = F.path_diagnostics
H = [5, 15, 30, 60, 120]
LV = [0.5, 1.0, 1.5, 2.0]
IV = 60_000_000_000


def arr(rows):
    a = np.array(rows, dtype="float64")
    return a[:, 0], a[:, 1], a[:, 2], a[:, 3]


def one_event(rows, d, sigma=0.02, horizons=(5,), first=0):
    o, h, l, c = arr(rows)
    ts = np.arange(len(o), dtype=np.int64) * IV
    return compute_paths(o, h, l, c, ts, np.array([first]), np.array([d]), np.array([sigma]), np.array([ts[-1] + 10 * IV]), IV, list(horizons), LV)


HAND = [(100, 102, 99, 101), (101, 105, 100, 104), (104, 104, 97, 98), (98, 99, 96, 97), (97, 103, 97, 102)]     # P0 = 100


def test_frozen_path_constants_are_pinned_and_the_discovery_space_is_unchanged():
    assert SPEC["horizons_bars"] == [5, 15, 30, 60, 120] and SPEC["sigma_ref"]["feature"] == "RV_60" and SPEC["sigma_ref"]["alternative_normalisers"] == "none"
    assert SPEC["sigma_ref"]["formula"] == "sigma_ref = RV_60 / sqrt(60)" and SPEC["sigma_ref"]["fallback_to_raw_RV_60"] == "none"
    assert set(SPEC["sigma_ref"]["used_for"]) == {"MFE_sigma", "MAE_sigma", "first_passage_barriers", "fixed_bracket_cells_64"}
    b = SPEC["bracket_surface"]
    assert (b["stops_sigma"], b["targets_sigma"], b["expiries_bars"], b["n_cells"]) == (LV, LV, [15, 30, 60, 120], 64)
    assert SPEC["stability"]["min_events_for_eligible_year"] == 20 and SPEC["percentiles"]["excursion_summary"] == ["mean", "median", "p75", "p95"]
    p = F.trial_policy                                                                          # the discovery policy is untouched by this layer
    assert p["expected_trials_per_experiment"] == 24 and p["max_experiments_per_campaign"] == 20 and p["selection_holdout"]["max_groups_per_campaign"] == 6
    assert (SPEC["promotion_eligible"], SPEC["selection_trials_affected"]) == (False, 0)
    assert len(reg.trial_specs(F)) == 24


# =================================================== sigma_ref = RV_60 / sqrt(60)
RV60 = 0.0774596669                                                                           # = 0.01 * sqrt(60)


def test_sigma_ref_is_rv60_over_sqrt_60():
    assert sigma_ref(np.array([RV60]))[0] == pytest.approx(RV60 / np.sqrt(60), rel=1e-15)
    assert sigma_ref(np.array([RV60]))[0] == pytest.approx(0.01, rel=1e-9)                     # sqrt(60) = 7.745966692
    assert np.allclose(sigma_ref(np.array([0.0, 0.05, 0.2])), np.array([0.0, 0.05, 0.2]) / np.sqrt(60), rtol=1e-15)
    assert "RV_60 / sqrt(60)" in SPEC["sigma_ref"]["definition"] and SPEC["sigma_ref"]["units"] == "one_bar_log_return"
    for name in ("path_diagnostics", "path_engine"):                                          # single definition, no alternative normaliser / fallback
        src = (CODE_ROOT / "engine" / f"{name}.py").read_text()
        assert src.count("RV_60") <= 6 and "raw RV" not in src.lower()
    src = (CODE_ROOT / "engine" / "path_diagnostics.py").read_text()
    assert 'sigma_ref(features["RV_60"]' in src and "sigma_ref(rv_ref(" in src                  # both call sites convert; neither passes RV_60 raw


SIG = float(sigma_ref(np.array([RV60]))[0])                                                   # 0.01
UP, DN = 100 * np.exp(SIG), 100 * np.exp(-SIG)                                                 # 101.00502..., 99.00498...


def _bars(*hl):
    return [(100, h, l, 100) for h, l in hl] + [(100, 100.2, 99.8, 100)] * 4


def test_barrier_conversion_long_plus_and_minus_one_sigma():
    tgt = one_event(_bars((101.01, 99.5)), +1, sigma=SIG)                                      # high above 100*exp(+sigma), low above the stop level
    code, cons, raw, sd = bracket_pnl(tgt, 1.0, 1.0, 5)
    assert code[0] == TARGET and raw[0] == pytest.approx(100 * (np.exp(SIG) - 1))              # +1.005017 points
    stp = one_event(_bars((100.5, 98.9)), +1, sigma=SIG)
    code, cons, raw, sd = bracket_pnl(stp, 1.0, 1.0, 5)
    assert code[0] == STOP and raw[0] == pytest.approx(-100 * (1 - np.exp(-SIG)))              # -0.995017 points
    assert one_event(_bars((101.00, 99.01)), +1, sigma=SIG).t_fav[1.0][0] == 2**30            # 101.00 < 101.005 and 99.01 > 99.005: neither level touched
    assert one_event(_bars((101.00, 99.01)), +1, sigma=SIG).t_adv[1.0][0] == 2**30


def test_barrier_conversion_short_plus_and_minus_one_sigma():
    tgt = one_event(_bars((100.5, 98.9)), -1, sigma=SIG)                                       # price FALLS through 100*exp(-sigma) -> favourable for a short
    code, cons, raw, sd = bracket_pnl(tgt, 1.0, 1.0, 5)
    assert code[0] == TARGET and raw[0] == pytest.approx(100 * (1 - np.exp(-SIG)))             # +0.995017 points
    stp = one_event(_bars((101.01, 99.5)), -1, sigma=SIG)                                      # price RISES through 100*exp(+sigma) -> adverse
    code, cons, raw, sd = bracket_pnl(stp, 1.0, 1.0, 5)
    assert code[0] == STOP and raw[0] == pytest.approx(-100 * (np.exp(SIG) - 1))               # -1.005017 points
    tdist, sdist = bracket_distances(np.array([100.0]), np.array([-1.0]), np.array([SIG]), 1.0, 1.0)
    assert tdist[0] == pytest.approx(100 * (1 - np.exp(-SIG))) and sdist[0] == pytest.approx(100 * (np.exp(SIG) - 1))


def test_one_bar_sigma_and_raw_rv60_give_different_barrier_outcomes_on_the_same_path():
    rows = [(100, 100.4, 99.9, 100.3), (100.3, 102, 100.2, 101.5), (101.5, 105, 101, 104.5), (104.5, 105, 103, 104), (104, 104.5, 103.5, 104)]
    one_bar = one_event(rows, +1, sigma=float(sigma_ref(np.array([RV60]))[0]))                 # 1 sigma = 1%: touched by the +5% path
    raw_scale = one_event(rows, +1, sigma=RV60)                                                # what v1.1.0 used: 1 sigma = 7.7%: not touched
    assert barrier_outcome(one_bar.t_fav[1.0], one_bar.t_adv[1.0], 5)[0] == TARGET
    assert barrier_outcome(raw_scale.t_fav[1.0], raw_scale.t_adv[1.0], 5)[0] == EXPIRED
    assert one_bar.t_fav[1.0][0] == 2 and raw_scale.t_fav[1.0][0] == 2**30


# =================================================== exact session-boundary arithmetic (RTH 09:30-16:00 America/New_York, frozen)
NY = "America/New_York"
LATEST = {5: "15:55", 15: "15:45", 30: "15:30", 60: "15:00", 120: "14:00"}                      # close 16:00 - h bars: last bar opens 15:59


def _day(day):
    idx = pd.date_range(f"{day} 09:30", f"{day} 17:59", freq="1min", tz=NY).tz_convert("UTC")    # continuous through the close: only the SESSION rule can bind
    px = 100 + np.arange(len(idx)) * 0.01
    return pd.DataFrame({"open": px, "high": px + 0.05, "low": px - 0.05, "close": px + 0.01, "volume": 1.0}, index=idx)


def _elig(bars, day, hhmmss, h):
    t = pd.Timestamp(f"{day} {hhmmss}", tz=NY).tz_convert("UTC")
    ev = pd.DataFrame({"event_time": [t], "direction": [1]})
    return bool(pdx.make_paths(bars, ev, np.array([0.01]), F).elig[h][0])


def test_rth_close_is_frozen_as_1600_new_york():
    assert F.instrument["rth"] == {"open": "09:30", "close": "16:00", "minutes": 390} and F.tz == NY and F.interval == pd.Timedelta("1min")


@pytest.mark.parametrize("day", ["2024-01-08", "2024-07-08", "2024-03-11", "2024-11-04"])      # EST, EDT, day after spring-forward, day after fall-back
@pytest.mark.parametrize("h", [5, 15, 30, 60, 120])
def test_latest_eligible_event_for_every_horizon_is_exact_to_the_bar(day, h):
    bars = _day(day)
    latest = pd.Timestamp(f"{day} {LATEST[h]}", tz=NY)
    # forward bars open latest .. latest+h-1 minutes; the last one opens 15:59 and completes exactly at the 16:00 close
    assert latest + pd.Timedelta(minutes=h) == pd.Timestamp(f"{day} 16:00", tz=NY)
    earlier, later = (latest - pd.Timedelta(minutes=1)).strftime("%H:%M"), (latest + pd.Timedelta(minutes=1)).strftime("%H:%M")
    assert _elig(bars, day, earlier, h)                                                        # one bar earlier: eligible
    assert _elig(bars, day, LATEST[h], h)                                                      # boundary minus h bars: eligible (window ends AT the close)
    assert not _elig(bars, day, later, h)                                                      # one bar later: its last bar would complete at 16:01


def test_event_time_between_bars_uses_the_first_bar_that_opens_at_or_after_it():
    bars = _day("2024-01-08")
    assert _elig(bars, "2024-01-08", "13:59:30", 120)                                          # first forward bar opens 14:00 -> window 14:00..15:59
    assert not _elig(bars, "2024-01-08", "14:00:30", 120)                                      # first forward bar opens 14:01 -> would end 16:01
    assert _elig(bars, "2024-01-08", "14:00:00", 120) and not _elig(bars, "2024-01-08", "14:00:01", 120)


def test_path_rule_equals_the_primary_target_rule_at_60_bars_for_every_minute_of_the_day():
    from engine.target_engine import target_timestamp_ineligible
    day = "2024-07-08"
    bars = _day(day)
    minutes = pd.date_range(f"{day} 09:31", f"{day} 15:59", freq="1min", tz=NY).tz_convert("UTC")
    ev = pd.DataFrame({"event_time": minutes, "direction": 1})
    T = pdx.make_paths(bars, ev, np.full(len(ev), 0.01), F)
    assert (T.elig[60] == ~target_timestamp_ineligible(minutes, F)).all()                      # same arithmetic as the frozen primary-target rule
    local = minutes.tz_convert(NY)
    for h, last in LATEST.items():
        expected = np.array([t.strftime("%H:%M") <= last for t in local])
        assert (T.elig[h] == expected).all(), h                                                # eligibility == (event_time <= 16:00 - h minutes), nothing else
    assert T.elig[120].sum() == len([t for t in local if t.strftime("%H:%M") <= "14:00"])
    assert not (T.elig[120] & ~T.elig[60]).any() and not (T.elig[60] & ~T.elig[30]).any()      # nested: a longer window is never more eligible


def test_template_session_end_1500_makes_120_bar_windows_unavailable_after_1400_only():
    from engine.event_contract import load_spec
    spec = load_spec(CODE_ROOT / "templates/experiment/EVENT_SPEC.yaml")
    assert spec["eligible_session"] == {"start": "09:31", "end": "15:00"}                      # events are < 15:00: all 60-bar eligible (latest 15:00)
    assert LATEST[60] == "15:00" and LATEST[120] == "14:00"                                    # but events in (14:00, 15:00) are PATH_TIMESTAMP_INELIGIBLE at 120 bars


# =================================================== sigma_ref actually flows through the pipeline
# =================================================== 1-2. MFE / MAE hand examples
def test_long_mfe_mae_hand_example():
    pa = one_event(HAND, +1)
    assert pa.p0[0] == 100 and pa.mfe_pts[5][0] == 5 and pa.mae_pts[5][0] == -4          # max(high-100) = 105-100 ; min(low-100) = 96-100
    assert (pa.t_mfe[5][0], pa.t_mae[5][0]) == (2, 4)                                     # first occurrence, 1-based
    assert pa.mfe_pts[5][0] + pa.mae_pts[5][0] == 1                                       # path dominance > 0: favourable dominated
    assert pa.close_h[5][0] == 102 and pa.mfe_pts[5][0] >= 0 >= pa.mae_pts[5][0]
    ml, al = mfe_mae_log(pa.p0, pa.d, pa.mfe_pts[5], pa.mae_pts[5])
    assert ml[0] == pytest.approx(np.log(1.05)) and al[0] == pytest.approx(np.log(0.96))


def test_short_mfe_mae_hand_example():
    pa = one_event(HAND, -1)
    assert pa.mfe_pts[5][0] == 4 and pa.mae_pts[5][0] == -5                               # max(100-low) = 4 ; min(100-high) = -5
    assert (pa.t_mfe[5][0], pa.t_mae[5][0]) == (4, 2)
    assert pa.mfe_pts[5][0] + pa.mae_pts[5][0] == -1                                      # adverse dominated
    ml, al = mfe_mae_log(pa.p0, pa.d, pa.mfe_pts[5], pa.mae_pts[5])
    assert ml[0] == pytest.approx(-np.log(0.96)) and al[0] == pytest.approx(-np.log(1.05))
    assert ml[0] >= 0 >= al[0]


# =================================================== 3. percentile convention
def test_percentile_convention_is_linear_interpolation_with_only_declared_percentiles():
    s = pdx.summ_exc(np.array([0, 10, 20, 30, 40.0]))
    assert (s["median"], s["p75"], s["p95"], s["mean"]) == (20.0, 30.0, 38.0, 20.0)        # 0.95 * 4 = 3.8 -> 30 + 0.8 * 10
    e = pdx.summ_endpoint(np.array([1, 2, 3, 4.0]))
    assert e["p25"] == pytest.approx(1.75) and e["p75"] == pytest.approx(3.25) and e["p5"] == pytest.approx(1.15) and e["p95"] == pytest.approx(3.85)
    assert e["std"] == pytest.approx(np.sqrt(5 / 3))                                       # ddof = 1
    assert set(e) == {"n", "mean", "median", "p25", "p75", "p5", "p95", "std"} and set(s) == {"n", "mean", "median", "p75", "p95"}
    assert SPEC["percentiles"]["method"] == "linear_interpolation" and SPEC["percentiles"]["no_other_percentiles"] is True


# =================================================== 4 + 27. continuation / reversal / flat, ties
def _blocks(closes, d=+1):
    rows, first = [], []
    for k, last in enumerate(closes):
        first.append(len(rows))
        rows += [(100, 100.5, 99.5, 100)] * 4 + [(100, max(100, last) + 0.5, min(100, last) - 0.5, last)]
    o, h, l, c = arr(rows)
    ts = np.arange(len(o), dtype=np.int64) * IV
    E = len(first)
    return compute_paths(o, h, l, c, ts, np.array(first), np.full(E, d), np.full(E, 0.02), np.full(E, ts[-1] + 10 * IV), IV, [5], LV)


def test_continuation_reversal_flat_counts_and_flat_ties():
    closes = [101, 99, 100, 102, 98]                                                        # one exact tie: endpoint == P0
    for d, cont in ((+1, 2), (-1, 2)):
        pa = _blocks(closes, d)
        c = pdx.core_sections(pa, np.ones(5, dtype=bool), 0.25)["continuation"][5]
        assert (c["continuation"]["n"], c["reversal"]["n"], c["flat"]["n"]) == (cont, 2, 1)
        assert c["continuation"]["denominator"] == 5 and c["flat"]["rate"] == pytest.approx(0.2)    # numerators AND denominators, not just percentages
        assert c["continuation"]["n"] + c["reversal"]["n"] + c["flat"]["n"] == 5                   # flat is neither continuation nor reversal


def test_equal_extrema_use_the_first_occurrence():
    rows = [(100, 103, 98, 100), (100, 103, 98, 100), (100, 102, 99, 100), (100, 103, 98, 100), (100, 101, 99, 100)]
    pa = one_event(rows, +1)
    assert (pa.mfe_pts[5][0], pa.t_mfe[5][0], pa.mae_pts[5][0], pa.t_mae[5][0]) == (3, 1, -2, 1)       # tie -> bar 1
    t = pdx.core_sections(pa, np.ones(1, dtype=bool), 0.25)["time_to_extrema"][5]
    assert t["p_same_bar"]["n"] == 1 and t["p_mfe_before_mae"]["n"] == 0 and t["p_mae_before_mfe"]["n"] == 0
    zero = one_event([(100, 100, 100, 100)] * 5, +1)                                          # zero excursions from the start
    assert zero.mfe_pts[5][0] == 0 and zero.mae_pts[5][0] == 0 and zero.t_mfe[5][0] == 1 and zero.t_mae[5][0] == 1


# =================================================== 5-6. same-bar ambiguity, conservative convention
def test_same_bar_touch_is_ambiguous_and_conservative_result_counts_it_as_a_stop():
    pa = one_event(HAND, +1)                                                                  # bar 1 high 102 (+0.5 sigma) and low 99 (-0.5 sigma)
    assert pa.t_fav[0.5][0] == 1 and pa.t_adv[0.5][0] == 1
    code, cons, raw, sd = bracket_pnl(pa, 0.5, 0.5, 5)
    assert code[0] == AMBIG
    assert cons[0] == pytest.approx(-sd[0]) and sd[0] == pytest.approx(100 * (1 - np.exp(-0.01)))      # AMBIGUOUS -> STOP
    assert np.isnan(raw[0])                                                                   # raw path result assumes no winner
    fp = pdx.first_passage_sections(pa, np.ones(1, dtype=bool), {"first_passage": {**SPEC["first_passage"], "horizons_bars": [5]}})
    r = fp["symmetric"]["+0.5sigma_before_-0.5sigma"][5]
    assert r["ambiguous_same_bar"]["n"] == 1 and r["confirmed_target_first"]["n"] == 0 and r["confirmed_stop_first"]["n"] == 0
    code1, cons1, raw1, sd1 = bracket_pnl(pa, 1.0, 1.0, 5)                                    # target (bar 2) strictly before stop (bar 3)
    assert code1[0] == TARGET and cons1[0] == raw1[0] == pytest.approx(100 * (np.exp(0.02) - 1))


def test_expiry_marks_to_market_at_the_expiry_close_in_the_event_direction():
    pa = one_event(HAND, +1, sigma=0.06)
    code, cons, raw, sd = bracket_pnl(pa, 2.0, 2.0, 5)                                        # 2 sigma = 12% is never touched inside 5 bars
    assert code[0] == EXPIRED and cons[0] == raw[0] == pytest.approx(2.0)                      # close 102 - P0
    pas = one_event(HAND, -1, sigma=0.06)
    code, cons, raw, _ = bracket_pnl(pas, 2.0, 2.0, 5)
    assert code[0] == EXPIRED and cons[0] == pytest.approx(-2.0)


# =================================================== 7-9, 12. frozen banks and canonical order
def test_first_passage_bank_contains_exactly_the_declared_cases():
    fp = SPEC["first_passage"]
    assert fp["horizons_bars"] == [15, 30, 60, 120] and fp["levels_sigma"] == [0.5, 1.0, 1.5, 2.0]
    assert fp["asymmetric_target_stop_sigma"] == [[1.0, 0.5], [2.0, 1.0], [0.5, 1.0], [1.0, 2.0]]
    pa = one_event(HAND, +1, horizons=(5,))
    out = pdx.first_passage_sections(pa, np.ones(1, dtype=bool), {"first_passage": {**fp, "horizons_bars": [5]}})
    assert list(out["symmetric"]) == [f"+{k}sigma_before_-{k}sigma" for k in LV]
    assert list(out["asymmetric"]) == ["+1.0sigma_target/-0.5sigma_stop", "+2.0sigma_target/-1.0sigma_stop", "+0.5sigma_target/-1.0sigma_stop", "+1.0sigma_target/-2.0sigma_stop"]
    assert fp["outcomes"] == ["TARGET_FIRST", "STOP_FIRST", "AMBIGUOUS_SAME_BAR", "NEITHER"]


def test_bracket_surface_is_exactly_64_cells_in_canonical_order_and_no_65th():
    cells = pdx.bracket_cell_defs(SPEC)
    keys = [(c["expiry_bars"], c["stop_sigma"], c["target_sigma"]) for c in cells]
    assert len(cells) == 64 == SPEC["bracket_surface"]["n_cells"] and len(set(keys)) == 64
    assert keys == list(product([15, 30, 60, 120], LV, LV)) and SPEC["bracket_surface"]["canonical_order"] == ["expiry", "stop", "target"]
    bigger = copy.deepcopy(SPEC)
    bigger["bracket_surface"]["stops_sigma"] = LV + [2.5]                                      # a 65th+ cell is impossible without editing the frozen spec
    with pytest.raises(AssertionError):
        pdx.bracket_cell_defs(bigger)
    assert SPEC["bracket_surface"]["costs_applied"] is False and SPEC["bracket_surface"]["cost_banner"] == "GROSS — COSTS NOT APPLIED"


def test_the_frozen_yaml_is_hashed_and_forbids_winner_language():
    from engine.common import frozen_files
    assert "frozen/v1/PATH_DIAGNOSTICS.yaml" in {str(p.relative_to(CODE_ROOT)) for p in frozen_files()}
    assert set(SPEC["bracket_surface"]["forbidden_output_phrases"]) == set(pdx.FORBIDDEN_PHRASES)
    assert SPEC["promotion_eligible"] is False and SPEC["selection_trials_affected"] == 0
    with pytest.raises(AssertionError):
        pdx.assert_no_forbidden_phrases({"x": "the Best Bracket is 1 sigma"})


# =================================================== 16, 26, 25. timestamps, gaps, volume, NaN
def test_session_end_horizon_ineligibility_is_timestamp_only_and_never_wraps():
    ts = np.arange(200, dtype=np.int64) * IV
    close = np.full(1, ts[120] + IV)                                                           # last bar completing by the close = index 120
    el = lambda first, h: bool(path_eligibility(ts, np.array([first]), close, IV, h)[0])      # noqa: E731
    assert el(100, 15) and el(106, 15) and not el(107, 15)                                     # ts[120] + iv == close is still inside; one bar later is not
    assert el(100, 5) and not el(100, 30) and not el(100, 120)
    assert not el(190, 15)                                                                     # data ends first
    rng = np.random.default_rng(0)
    o = np.full(200, 100.0)
    for tweak in (1.0, 1e6):                                                                   # wildly different prices: eligibility cannot change
        p = o * tweak
        pa = compute_paths(p, p, p, p, ts, np.array([100, 107]), np.array([1, 1]), np.array([0.01, 0.01]), np.full(2, close[0]), IV, [15], LV)
        assert pa.elig[15].tolist() == [True, False]


def test_timestamp_gaps_make_windows_ineligible_not_silently_shorter():
    ts = np.arange(100, dtype=np.int64) * IV
    ts[50:] += 7 * IV                                                                          # a 7-minute hole between bar 49 and 50
    close = np.full(2, ts[-1] + IV)
    el = path_eligibility(ts, np.array([40, 60]), close, IV, 15)
    assert el.tolist() == [False, True]                                                        # window 40..54 spans the hole; 60..74 does not
    assert path_eligibility(ts, np.array([40]), close[:1], IV, 5)[0]                           # a shorter horizon before the hole is fine


def test_non_finite_prices_inside_a_window_make_the_event_ineligible_and_volume_is_irrelevant():
    rows = [list(r) for r in HAND]
    rows[2][1] = np.nan
    pa = one_event(rows, +1)
    assert not pa.elig[5][0]
    bars = make_bars(3, seed=1)
    ev = pd.DataFrame({"event_time": [bars.index[100] + pd.Timedelta("1min")], "direction": [1]})
    a = pdx.make_paths(bars, ev, np.array([0.01]), F)
    b = pdx.make_paths(bars.assign(volume=0.0), ev, np.array([0.01]), F)                       # zero volume everywhere
    for h in H:
        assert np.array_equal(a.mfe_pts[h], b.mfe_pts[h]) and np.array_equal(a.close_h[h], b.close_h[h]) and (a.elig[h] == b.elig[h]).all()


# =================================================== 28. tick conversion
def test_tick_size_comes_from_the_instrument_config_never_hard_coded():
    assert F.tick_size == 0.25
    pa = one_event(HAND, +1)
    m = np.ones(1, dtype=bool)
    a = pdx.core_sections(pa, m, 0.25)["excursions"][5]["MFE"]
    b = pdx.core_sections(pa, m, 0.5)["excursions"][5]["MFE"]
    assert a["points"]["median"] == 5.0 and a["ticks"]["median"] == 20.0 and b["ticks"]["median"] == 10.0
    for name in ("path_engine", "path_diagnostics", "path_report"):
        tree = ast.parse((CODE_ROOT / "engine" / f"{name}.py").read_text())
        consts = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, float)}
        assert 0.25 not in consts, name


# =================================================== 24. memory
def test_streaming_implementation_never_builds_horizon_sized_matrices():
    for name in ("path_engine", "path_diagnostics"):
        src = (CODE_ROOT / "engine" / f"{name}.py").read_text()
        assert "sliding_window_view" not in src and "stride_tricks" not in src and "gather(" not in src and "np.tile" not in src
    rng = np.random.default_rng(0)
    n, E = 300_000, 100_000
    c = 5000 * np.exp(np.cumsum(rng.normal(0, 4e-4, n)))
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) * (1 + abs(rng.normal(0, 2e-4, n)))
    l = np.minimum(o, c) * (1 - abs(rng.normal(0, 2e-4, n)))
    ts = np.arange(n, dtype=np.int64) * IV
    first = np.sort(rng.integers(0, n - 200, E))
    args = (o, h, l, c, ts, first, rng.choice([-1, 1], E), np.full(E, 0.01), np.full(E, ts[-1] + 10**15), IV, H, LV)
    tracemalloc.start()
    pa = compute_paths(*args)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert peak < 0.5 * E * max(H) * 8, peak                                                   # a single E x 120 float64 matrix alone would be 96 MB
    assert pa.mfe_pts[120].shape == (E,)


# =================================================== 23. brute-force equivalence (MFE, MAE, extrema times, barriers, brackets, same-bar)
def _ref(o, hi, lo, cl, ts, first, d, sig, close, h):
    """Straightforward per-event python loops."""
    n = len(o)
    ok = first + h - 1 < n and ts[first + h - 1] - ts[first] == (h - 1) * IV and ts[first + h - 1] + IV <= close
    if not ok:
        return None
    p0 = o[first]
    mfe, mae, tm, ta = -np.inf, np.inf, 0, 0
    for j in range(h):
        fav = (hi[first + j] - p0) if d > 0 else (p0 - lo[first + j])
        adv = (lo[first + j] - p0) if d > 0 else (p0 - hi[first + j])
        if fav > mfe:
            mfe, tm = fav, j + 1
        if adv < mae:
            mae, ta = adv, j + 1
    return mfe, mae, tm, ta, cl[first + h - 1]


def _ref_touch(o, hi, lo, first, d, sig, k, kind, upto):
    p0 = o[first]
    for j in range(min(upto, len(o) - first)):
        lh, ll = np.log(hi[first + j] / p0), np.log(lo[first + j] / p0)
        fav, adv = (lh, ll) if d > 0 else (-ll, -lh)
        if (kind == "t" and fav >= k * sig) or (kind == "s" and adv <= -k * sig):
            return j + 1
    return 10**9


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_brute_force_equivalence_on_random_paths(seed):
    rng = np.random.default_rng(seed)
    n, E = 700, 160
    c = 100 * np.exp(np.cumsum(rng.normal(0, 3e-3, n)))
    o = np.r_[c[0], c[:-1]]
    hi = np.maximum(o, c) * (1 + abs(rng.normal(0, 1.5e-3, n)))
    lo = np.minimum(o, c) * (1 - abs(rng.normal(0, 1.5e-3, n)))
    ts = np.cumsum(np.where(rng.random(n) < 0.01, rng.integers(2, 9, n), 1)).astype(np.int64) * IV         # random timestamp gaps
    first = rng.integers(0, n - 5, E)
    d = rng.choice([-1, 1], E)
    sig = rng.uniform(0.002, 0.02, E)
    close = ts[np.minimum(first, n - 1)] + rng.integers(1, 200, E) * IV                                      # random session ends
    pa = compute_paths(o, hi, lo, cl := c, ts, first, d, sig, close, IV, H, LV)
    assert sum(int(pa.elig[h].sum()) for h in H) > 100 and (pa.elig[5].sum() > pa.elig[120].sum())
    for i in range(E):
        for h in H:
            r = _ref(o, hi, lo, cl, ts, first[i], d[i], sig[i], close[i], h)
            assert bool(pa.elig[h][i]) == (r is not None), (i, h)
            if r is None:
                continue
            assert np.allclose([pa.mfe_pts[h][i], pa.mae_pts[h][i], pa.close_h[h][i]], [r[0], r[1], r[4]], rtol=0, atol=1e-12)
            assert (pa.t_mfe[h][i], pa.t_mae[h][i]) == (r[2], r[3])                                        # first-occurrence times, exactly
    for tgt, stp, ex in product(LV, LV, [15, 30, 60, 120]):                                                 # every one of the 64 bracket cells
        code, cons, raw, sd = bracket_pnl(pa, tgt, stp, ex)
        tdist, sdist = bracket_distances(pa.p0, pa.d, pa.sigma_log, tgt, stp)
        for i in np.flatnonzero(pa.elig[ex]):
            tt = _ref_touch(o, hi, lo, first[i], d[i], sig[i], tgt, "t", ex)
            ts_ = _ref_touch(o, hi, lo, first[i], d[i], sig[i], stp, "s", ex)
            exp_code = EXPIRED if tt == ts_ == 10**9 else (AMBIG if tt == ts_ else (TARGET if tt < ts_ else STOP))
            assert code[i] == exp_code, (tgt, stp, ex, i)
            exp_raw = {TARGET: tdist[i], STOP: -sdist[i], EXPIRED: d[i] * (cl[first[i] + ex - 1] - o[first[i]]), AMBIG: np.nan}[exp_code]
            assert (np.isnan(raw[i]) and exp_code == AMBIG) or raw[i] == pytest.approx(exp_raw)
            assert cons[i] == pytest.approx(-sdist[i] if exp_code == AMBIG else exp_raw)
    assert any((bracket_pnl(pa, t, s, e)[0] == AMBIG).any() for t, s, e in product(LV, LV, [15, 30, 60, 120]))   # the property test does exercise ambiguity


def test_rv_ref_equals_the_frozen_rv_60_feature():
    from engine.feature_engine import compute_features, last_completed_position
    bars = make_bars(5, seed=2)
    ev = pd.DataFrame({"event_id": [f"E{i}" for i in range(6)], "event_time": bars.index[[700, 800, 900, 1100, 1300, 1500]] + pd.Timedelta("1min"), "direction": 1})
    feats = compute_features(bars, ev, F)
    pos = last_completed_position(bars.index, ev["event_time"], F.interval)
    assert np.allclose(rv_ref(bars["close"].to_numpy(), pos), feats["RV_60"].to_numpy(), rtol=1e-12, atol=0)


# =================================================== 13-14. year-by-year and fold diagnostics (pure)
def _synthetic_table(years, d):
    rows = [(100 + 0.1 * i, 100 + 0.1 * i + 0.3, 100 + 0.1 * i - 0.3, 100 + 0.1 * i + 0.1) for i in range(60 * len(years) + 400)]   # steady uptrend
    o, h, l, c = arr(rows)
    ts = np.arange(len(o), dtype=np.int64) * IV
    first = np.arange(len(years)) * 3 + 10
    return compute_paths(o, h, l, c, ts, first, np.asarray(d), np.full(len(years), 0.01), np.full(len(years), ts[-1] + 10**15), IV, H, LV)


def test_year_table_lists_every_eligible_year_including_negative_ones_and_flags_thin_years():
    years = np.array([2016] * 30 + [2017] * 30 + [2018] * 10)
    d = np.array([1] * 30 + [-1] * 30 + [1] * 10)                                              # 2017 trades against the uptrend: a negative year
    T = _synthetic_table(years, d)
    yt = pdx.yearly_table(T, np.ones(70, dtype=bool), years, {2016: 30.0, 2017: 15.0}, 0.25, 20)
    assert [r["year"] for r in yt["rows"]] == [2016, 2017] and yt["ineligible_years"] == [{"year": 2018, "n": 10}]
    r16, r17 = yt["rows"]
    assert r16["mean_return_60"] > 0 and r17["mean_return_60"] < 0                              # the negative year is NOT hidden
    assert r16["events_per_week"] == 1.0 and r17["events_per_week"] == 2.0
    assert set(r16) >= {"CONT_15", "CONT_30", "CONT_60", "CONT_120", "median_MFE_60", "median_absMAE_60", "P75_MFE_60", "P75_absMAE_60",
                        "mean_return_60", "median_return_60"}
    assert r16["CONT_60"]["n"] == 30 and r16["CONT_60"]["denominator"] == 30 and r17["CONT_60"]["n"] == 0


def test_fold_and_year_sections_are_produced_per_group():
    years = np.array([2016] * 30 + [2017] * 30)
    T = _synthetic_table(years, np.ones(60, dtype=int))
    folds = np.repeat([1, 2, 3, 4, 5, 0], 10)
    out = pdx._ctx_payload(T, np.ones(60, dtype=bool), years, folds, 12.0, {2016: 6.0, 2017: 6.0}, {}, F, SPEC)
    assert sorted(out["by_fold"]) == [1, 2, 3, 4, 5] and sorted(out["by_year"]) == [2016, 2017]
    assert out["by_fold"][1]["continuation"][60]["continuation"]["denominator"] == 10
    assert "bracket_surface" not in out                                                         # surfaces are attached by the orchestrator, not here


# =================================================== 15. filter-ladder path diagnostics
def test_filter_ladder_path_effects_never_remove_or_reorder_a_poor_step(tmp_path):
    from engine.event_contract import ladder_event_sets
    bars = make_bars(n_days=520, seed=4, phi=0.8)
    for label, src in (("good", LADDER_EVENT), ("bad", LADDER_EVENT.replace("up[1:] = c[1:] > c[:-1]", "up[1:] = c[1:] < c[:-1]"))):
        spec = ladder_spec()
        (tmp_path / label).mkdir()
        mod = module_from(tmp_path / label, src)
        sets = ladder_event_sets(mod, bars, spec, F)
        lad = pdx.ladder_path_diagnostics(sets, spec["filter_ladder"], bars, F)
        assert lad["order_frozen"] == ["BASE_TRIGGER", "CONDITION_1", "FINAL_EVENT"] and [s["step"] for s in lad["steps"]] == lad["order_frozen"]
        base, c1, fin = lad["steps"]
        assert base["n_events"] > c1["n_events"] == fin["n_events"] > 0 and base["delta_vs_previous_step"] is None
        for st in lad["steps"]:
            assert set(map(int, st["core"])) == set(H)
            co = st["core"][60]
            assert {"continuation", "median_MFE_points", "p75_MFE_points", "p95_MFE_points", "median_adverse_points", "p75_adverse_points", "p95_adverse_points"} <= set(co)
            assert st["by_year"] and all(y["n"] >= 20 for y in st["by_year"].values())
        d = c1["delta_vs_previous_step"]
        assert d["frequency_per_week"] < 0 and set(map(int, d["per_horizon"])) == set(H)
        assert fin["delta_vs_previous_step"]["per_horizon"][60]["continuation_rate"] == 0 and fin["delta_vs_previous_step"]["frequency_per_week"] == 0
        assert "NOT removed or altered" in lad["note"]
        if label == "good":
            good_c1 = c1["core"][60]["continuation"]["continuation"]["rate"]
        else:
            assert c1["core"][60]["continuation"]["continuation"]["rate"] < good_c1                # a bad filter is visible, kept, and in place


# =================================================== bar-level pipeline: wall, non-interference, registry
def _trial_view(ws, exp):
    t = reg.experiment_trials(ws, exp)
    drop = {"revealed_at", "registered_at", "manifest_hash"}
    return t[[c for c in reg.TRIAL_COLS if c not in drop]]


@pytest.fixture(scope="module")
def runs(tmp_path_factory):
    bars = three_stage_bars()
    p = parse_partitions(P)
    ts = bars.index.tz_convert("UTC")

    def corrupt(mask):
        b = bars.copy()
        rng = np.random.default_rng(3)
        b.loc[mask, ["open", "high", "low", "close"]] = rng.uniform(1, 1e6, size=(int(mask.sum()), 4))
        b.loc[mask, "volume"] = -5.0
        return b
    variants = {"clean": bars, "selection_holdout": corrupt((ts >= p.development_end) & (ts < p.selection_holdout_end)), "lockbox": corrupt(ts >= p.lockbox_start)}
    out = {}
    captured = []
    orig = pdx.make_paths

    def spy(bars_, events_, sigma_, frozen_):
        captured.append((events_.copy(), np.array(sigma_)))
        return orig(bars_, events_, sigma_, frozen_)
    mp0 = pytest.MonkeyPatch()
    mp0.setattr(pdx, "make_paths", spy)
    for label, data in variants.items():
        ws = reg.Workspace(tmp_path_factory.mktemp(label)).init()
        exp = make_experiment(ws)
        out[label] = (ws, exp, runner.run_experiment(ws, exp, data, verbose=False, run_sensitivity_stage=False))
    mp0.undo()
    out["captured"] = captured
    ws = reg.Workspace(tmp_path_factory.mktemp("nopath")).init()
    exp = make_experiment(ws)
    mp = pytest.MonkeyPatch()
    mp.setattr(runner, "_path_diagnostics_stage", lambda *a, **k: {"status": "NOT_COMPUTED_NO_BARS", "label": SPEC["label"]})
    try:
        out["nopath"] = (ws, exp, runner.run_experiment(ws, exp, bars, verbose=False, run_sensitivity_stage=False))
    finally:
        mp.undo()
    return out


def _pd(runs, label):
    ws, exp, _ = runs[label]
    return (experiment_dir(ws, exp) / "results" / "PATH_DIAGNOSTICS.json").read_bytes()


class TestPipeline:
    def test_selection_holdout_poisoning_leaves_every_is_path_diagnostic_byte_identical(self, runs):
        assert _pd(runs, "selection_holdout") == _pd(runs, "clean")
        a = json.loads((experiment_dir(runs["clean"][0], runs["clean"][1]) / "results/IS_REPORT.json").read_text())
        b = json.loads((experiment_dir(runs["selection_holdout"][0], runs["selection_holdout"][1]) / "results/IS_REPORT.json").read_text())
        assert a["Z_forward_path_diagnostics"] == b["Z_forward_path_diagnostics"] and a["X_hashes"]["path_diagnostics_sha256"] == b["X_hashes"]["path_diagnostics_sha256"]

    def test_lockbox_poisoning_leaves_every_is_path_diagnostic_byte_identical(self, runs):
        assert _pd(runs, "lockbox") == _pd(runs, "clean")

    def test_the_is_report_has_no_selection_holdout_path_numbers_and_says_not_accessed(self, runs):
        ws, exp, _ = runs["clean"]
        md = (experiment_dir(ws, exp) / "results/IS_REPORT.md").read_text()
        assert "SELECTION HOLDOUT status = NOT ACCESSED" in md and "No SELECTION HOLDOUT or lockbox row entered any number below" in md
        for bad in ("SELECTION HOLDOUT MFE", "SELECTION HOLDOUT MAE", "SELECTION HOLDOUT bracket", "SELECTION HOLDOUT continuation"):
            assert bad not in md
        rep = json.loads(_pd(runs, "clean"))
        p = parse_partitions(P)
        assert rep["counts"]["model_eligible_events"] > 0
        assert pd.Timestamp(json.loads((experiment_dir(ws, exp) / "results/results.json").read_text())["base_event"]["last_bar"]) < p.development_end

    def test_report_section_and_machine_readable_statement(self, runs):
        ws, exp, _ = runs["clean"]
        md = (experiment_dir(ws, exp) / "results/IS_REPORT.md").read_text()
        for s in ("## Z. FORWARD PATH DIAGNOSTICS", "# NON-PROMOTABLE PATH DIAGNOSTICS", "PROMOTION EVIDENCE", "### Z.1 Endpoint returns", "### Z.2 Continuation / reversal",
                  "### Z.3 MFE / MAE", "### Z.4 Excursion percentiles", "### Z.5 Time to extrema", "### Z.6 First passage", "### Z.7 Fixed bracket surface",
                  "### Z.8 Year-by-year path stability", "### Z.9 Development-fold path stability", "### Z.10 Filter-ladder path effects", "### Z.11 Diagnostic observations",
                  "GROSS — COSTS NOT APPLIED", "DIAGNOSTIC ONLY — NO BRACKET WAS SELECTED"):
            assert s in md, s
        stmt = " ".join(SPEC["diagnostic_statement"].split())
        assert stmt in md
        j = json.loads((experiment_dir(ws, exp) / "results/IS_REPORT.json").read_text())["Z_forward_path_diagnostics"]
        assert j["diagnostic_statement"] == stmt and j["promotion_eligible"] is False and j["selection_trials_affected"] == 0 and j["n_bracket_cells"] == 64
        full = json.loads(_pd(runs, "clean"))
        assert full["diagnostic_statement"] == stmt and full["promotion_eligible"] is False
        for phrase in pdx.FORBIDDEN_PHRASES:
            assert phrase not in md.upper() and phrase not in _pd(runs, "clean").decode().upper()
        assert md.count("| 15 | 0.5 | 0.5 |") >= 1                                              # surface rows exist

    def test_raw_and_selected_state_diagnostics_exist_and_identical_sets_are_grouped(self, runs):
        full = json.loads(_pd(runs, "clean"))
        ctx = full["contexts"]
        assert "ALL" in ctx and full["n_contexts"] == 25                                         # raw base event + 12 UPPER + 12 LOWER (target x model)
        names = [k for k in ctx if k != "ALL"]
        assert len(names) == 24 and all(k.endswith(("UPPER_HALF", "LOWER_HALF")) for k in names)
        for k in names:
            c = ctx[k]
            while "same_events_as" in c:
                c = ctx[c["same_events_as"]]
            assert 0 < c["n_events"] < ctx["ALL"]["n_events"] and len(c["bracket_surface"]) == 64
        assert len(ctx["ALL"]["bracket_surface"]) == 64

    def test_surface_is_in_canonical_order_not_performance_order(self, runs):
        cells = json.loads(_pd(runs, "clean"))["contexts"]["ALL"]["bracket_surface"]
        keys = [(c["expiry_bars"], c["stop_sigma"], c["target_sigma"]) for c in cells]
        assert keys == list(product([15, 30, 60, 120], LV, LV))
        perf = [c["mean_gross_points"] for c in cells]
        assert perf != sorted(perf) and perf != sorted(perf, reverse=True)                        # not sorted by performance
        assert all(c["variant_primary"].startswith("CONSERVATIVE_RESULT") for c in cells) and all("raw_path_result" in c for c in cells)

    def test_ambiguity_is_reported_separately_never_hidden(self, runs):
        c = json.loads(_pd(runs, "clean"))["contexts"]["ALL"]["bracket_surface"][0]
        assert {"same_bar_ambiguous_rate", "confirmed_stop_first_rate", "stop_hit_rate_conservative", "target_hit_rate", "expiry_rate"} <= set(c)
        assert c["stop_hit_rate_conservative"]["n"] == c["confirmed_stop_first_rate"]["n"] + c["same_bar_ambiguous_rate"]["n"]

    def test_diagnostics_cannot_change_candidates_ranking_or_status(self, runs):
        a, b = runs["clean"], runs["nopath"]
        pd.testing.assert_frame_equal(_trial_view(a[0], a[1]), _trial_view(b[0], b[1]))          # every trial number, decision and reason identical
        ra, rb = reg.experiment_row(a[0], a[1]), reg.experiment_row(b[0], b[1])
        assert (ra["status"], ra["is_status"]) == (rb["status"], rb["is_status"])
        ja = json.loads((experiment_dir(a[0], a[1]) / "results/IS_REPORT.json").read_text())
        jb = json.loads((experiment_dir(b[0], b[1]) / "results/IS_REPORT.json").read_text())
        assert ja["I_top_configurations"] == jb["I_top_configurations"] and ja["J_model_agreement"] == jb["J_model_agreement"]

    def test_diagnostics_are_absent_from_the_selection_trial_registry_and_multiplicity(self, runs):
        ws, exp, _ = runs["clean"]
        t = reg.experiment_trials(ws, exp)
        assert len(t) == 24 and list(reg.read_trials(ws).columns) == reg.TRIAL_COLS
        assert not any("bracket" in str(c).lower() or "mfe" in str(c).lower() or "path" in str(c).lower() for c in reg.TRIAL_COLS)
        raw = t["raw_p"].astype(float).to_numpy()
        assert np.allclose(t["experiment_bonferroni_p"].astype(float), np.minimum(raw * 24, 1.0))     # universe = 24 trials, nothing added
        assert np.allclose(t["campaign_bonferroni_p"].astype(float), np.minimum(raw * 24, 1.0))
        from engine.multiplicity import benjamini_hochberg
        assert np.allclose(t["experiment_q"].astype(float), benjamini_hochberg(raw))
        assert reg.campaign_summary(ws, "C001")["selection_trials_revealed"] == 24
        assert reg.integrity_check(ws)["selection_trials"] == 24

    def test_selection_code_never_imports_the_path_layer(self):
        for name in ("acceptance", "trial_registry", "multiplicity", "statistics", "walkforward", "score_calibration", "model_engine", "selection_holdout_stage", "cpcv", "near_tie", "holdout_preference"):
            tree = ast.parse((CODE_ROOT / "engine" / f"{name}.py").read_text())
            mods = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
            assert not any(str(m).startswith(("engine.path", "engine import path")) for m in mods), name
            assert not any(isinstance(n, ast.ImportFrom) and n.module == "engine" and any(a.name.startswith("path_") for a in n.names) for n in ast.walk(tree)), name

    def test_observations_from_diagnostics_are_diagnostic_only(self, runs):
        ws, exp, _ = runs["clean"]
        obs = reg.read_observations(ws)
        mine = obs[obs["category"].isin(["path_continuation", "path_dominance", "bracket_surface_description"])]
        assert len(mine) == 3 and (mine["eligible_for_promotion"] == "False").all() and (mine["diagnostic_label"] == reg.DIAG_LABEL).all()
        assert any("NO BRACKET WAS SELECTED" in d and "COSTS NOT APPLIED" in d for d in mine["description"])
        before = _trial_view(ws, exp).to_csv()
        status = reg.experiment_row(ws, exp)["status"]
        reg.log_exploratory_observation(ws, exp, "1 sigma / 2 sigma bracket looks interesting; P95 MFE unusually large", diagnostic_only=True)
        with pytest.raises(EngineError, match="diagnostic_only=True"):
            reg.log_exploratory_observation(ws, exp, "use the 1.5 sigma stop", diagnostic_only=False)
        assert _trial_view(ws, exp).to_csv() == before and reg.experiment_row(ws, exp)["status"] == status
        assert reg.integrity_check(ws)["selection_trials"] == 24

    def test_path_file_is_hash_bound_to_the_report(self, runs):
        ws, exp, _ = runs["clean"]
        d = experiment_dir(ws, exp) / "results"
        res = json.loads((d / "results.json").read_text())["path_diagnostics"]
        j = json.loads((d / "IS_REPORT.json").read_text())
        import hashlib
        assert res["status"] == "COMPUTED" and hashlib.sha256((d / res["file"]).read_bytes()).hexdigest() == res["sha256"] == j["X_hashes"]["path_diagnostics_sha256"]

    def test_tampering_with_the_path_file_invalidates_a_human_approval(self, runs, tmp_path):
        import shutil

        from engine.selection_holdout_stage import ApprovalError, validate_approval
        from tests.scenario_helpers import human_approval
        ws0, exp, _ = runs["clean"]
        dst = tmp_path / "ws"
        shutil.copytree(ws0.root, dst)
        ws = reg.Workspace(dst)
        f = experiment_dir(ws, exp) / "results" / "PATH_DIAGNOSTICS.json"
        f.write_text(f.read_text().replace('"promotion_eligible":false', '"promotion_eligible":true', 1))
        human_approval(ws, exp, [f"{exp}|DIR_RETURN_30|UPPER_HALF"])
        with pytest.raises(ApprovalError, match="PATH_DIAGNOSTICS.json changed|PATH_DIAGNOSTICS.json was edited|edited"):
            validate_approval(ws, exp)

    def test_the_pipeline_passes_rv60_over_sqrt_60_to_every_barrier_and_bracket(self, runs):
        from engine.feature_engine import last_completed_position
        events, sigma = runs["captured"][0]                                                    # the clean run's make_paths call
        dev = three_stage_bars()
        dev = dev[dev.index.tz_convert("UTC") < parse_partitions(P).development_end]
        pos = last_completed_position(dev.index, events["event_time"], F.interval)
        rv = rv_ref(dev["close"].to_numpy(), pos)
        assert np.allclose(sigma, rv / np.sqrt(60), rtol=1e-12, atol=0)
        assert not np.allclose(sigma, rv, rtol=0.5)                                           # not the old raw-RV_60 scale
        assert len(runs["captured"]) >= 3 and np.array_equal(runs["captured"][1][1], sigma)      # SELECTION HOLDOUT-poisoned run: identical sigma
