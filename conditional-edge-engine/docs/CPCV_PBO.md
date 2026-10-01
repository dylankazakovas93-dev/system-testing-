# CPCV and the PBO-style diagnostic (v1, fixed)

**CPCV** (final robustness stage; veto only): N = 6 chronological groups of ~equal model-eligible event count (boundaries snapped
to exchange-local day starts), k = 2 held out ⇒ C(6,2) = **15** splits. TEST = the 2 held-out groups; TRAIN = the other 4 minus
(a) *purge*: every training event whose label interval [event_time, effective_target_end] overlaps a held-out region, and
(b) *embargo*: every training event within the maximum primary target horizon (60 bars of information time) before the start or
after the end of each held-out region. Training-only preprocessing, nested inner-OOF calibration and score median in every split.

`CPCV_PASS` per candidate model: all 15 splits valid, median selected effect > 0, median uplift > 0, selected effect > 0 in ≥ 12/15
splits, uplift > 0 in ≥ 12/15 splits. A target/side group needs ≥ 2 of 3 models to pass (mirrors model agreement). CPCV only runs for
OOS-confirmed groups and can only veto: it never creates, rescues or re-selects anything.

**PBO-style diagnostic** (Bailey–Borwein–López de Prado–Zhu style, adapted; *not* an independent p-value; never used to rank, select or
veto). Configurations i = 1..N are the (target, side, model) configs of OOS-confirmed groups that entered CPCV; N ≥ 2 required, else
`PBO = NOT APPLICABLE`.

1. `m[i,g]` = mean, over the CPCV splits in which group g was held out, of config i's uplift (selected effect − parent effect, side-adjusted)
   measured on the events of group g only (NaN → 0).
2. For each of the 15 splits s with test groups T and training groups C = {1..6} \ T:
   `IS_i = mean_{g∈C} m[i,g]`, `OOS_i = mean_{g∈T} m[i,g]`, `n* = argmax_i IS_i`.
3. `ω_s = rank_ascending(OOS_{n*} among OOS_1..OOS_N) / (N+1)`, `λ_s = ln(ω_s / (1 − ω_s))`.
4. `PBO = (1/15) · #{ s : λ_s < 0 }` — the share of splits in which the best "in-sample" configuration lands below the median out-of-sample.

Caveats: the configs of one group share a target/side so they are highly dependent; the 15 splits share data; therefore PBO is a
descriptive indicator of rank instability, not a probability with a sampling distribution.
