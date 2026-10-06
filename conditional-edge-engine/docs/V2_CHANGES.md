# v2.0.0 — targets 15/60/180, uplift floor 0.01, session-end truncation, where-it-works map

Changes on top of the frozen v1.2.1 snapshot (the lifecycle, near-tie rule, holdout rules, viability floor, CPCV and lockbox are unchanged):

* **Targets:** `DIR_RETURN_15`, `DIR_RETURN_60`, `DIR_RETURN_180`, `DIR_PATH_SKEW_60` (24 trials as before). `DIR_RETURN_30` is gone; no 120-minute target.
* **Session end:** windows that would cross the RTH close are truncated at the close (not dropped) and flagged `truncated`; only events with no complete forward bar before the close are ineligible.
  CPCV embargo = max primary horizon = 180 bars.
* **Uplift floor 0.10 -> 0.01** (IS gates and the informational holdout evidence gates). All null-based and consistency gates, the 1/week frequency floor, BH/Bonferroni, year/fold/model rules and the viability floor are unchanged.
* **IS report section WM (where it works / where it does not):** per top group, by calendar year, exchange-local hour and full-vs-truncated horizon, from out-of-fold DEVELOPMENT_CV events. Descriptive only: it creates no trial and selects nothing.
* **Not changed / not added:** no costs gate (3-tick round trip is for the later bracketing study), no coarse-to-fine stage (the engine never had one), the path-diagnostics horizons (5/15/30/60/120) stay diagnostic only.

Interpretation notes: the planted-momentum example now shows 15-minute and path-skew candidates, 60-minute candidates that the old 0.10 floor rejected, and 180-minute rejected by the null tests.
`frozen/v1/` keeps its directory name although the content is the v2 specification.

## v2.1.0 — fold gate replaced by batch/year concentration

* **Removed:** "≥ 4 of 5 DEVELOPMENT_CV folds positive" and "all 5 folds evaluated" (`INSUFFICIENT_DEVELOPMENT_FOLD_EVIDENCE`). Folds are still computed (they produce the out-of-fold predictions) and reported, but gate nothing.
* **Added:** the out-of-fold selected trades, in time order, are cut into 10 equal-count batches. The best batch may carry at most 35% of the total uplift mass (`batch_best_share`), and with ≥ 2 eligible years the uplift mass without the best year must stay positive (`year_best_share` < 1). Two new trial columns record both shares.
* **Unchanged:** the 0.01 uplift floor, 1/week frequency floor, null tests, BH/Bonferroni, ≥ 70% positive years, 2-of-3 models, verification, sensitivity, near-tie rule, holdout viability floor, CPCV (still the expensive, 6-group robustness veto), lockbox.
* **Guidance:** `GUIDE.md` replaces the old rigid `AGENTS.md` rule list: LLMs are encouraged to propose events/filters (consulting the literature), interpret reports and challenge the engine; only a short list of integrity rules is non-negotiable. `AGENTS.md` / `CLAUDE.md` point to it.

## v2.2.0 — t >= 3 raw-p hurdle replaces the Bonferroni gates; 20000 permutations

* **Problem:** the permutation p is `(1 + #{perm >= observed}) / (reps + 1)`; at 2000 reps the smallest raw p is ≈ 0.0005. The campaign Bonferroni p is `raw_p × 24 × E`, so a 20-experiment campaign (480 trials) had a floor of 0.24 and 5 experiments a floor of 0.06: only campaigns of ≤ 4 experiments could ever pass, whatever the effect.
* **Change (human decision):** the experiment- and campaign-level Bonferroni gates are replaced by one fixed hurdle on the raw permutation p: `raw_p <= 0.00135`, the one-sided tail of t = 3 (Harvey, Liu & Zhu 2016 use t > 3.0 as the bar for new findings under multiple testing). It is the same at every experiment and campaign size. Permutations rise to 20000 (raw p resolution ≈ 0.00005): a trial passes only if at most 26 of 20000 shuffles match or beat the observed uplift.
* **Unchanged:** BH q ≤ 0.05 at the experiment and campaign level (still retroactive over all revealed trials), the Bonferroni columns (still computed and reported, no longer gating), the 24-trial / 20-experiment limits, the selection-holdout Bonferroni evidence labels, all other gates and the lifecycle.
* **Trade-offs:** the hurdle does not tighten as trials accumulate (only BH does). A result right at the line is noisy (the count has SD ≈ 5 near 27). The permutation step is ~10× slower (measured ≈ 0.3 s → 2.5 s per panel on 4000 synthetic events).
