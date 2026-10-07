# GUIDE — how to work on this repository (for any LLM: Claude, Codex, others)

This is a research factory for one question: **does the market state at a precisely defined event carry robust information about the next 15, 60 and 180 minutes?**
The human (the "owner") decides what to research and every approval. You are a collaborator, not a script: have opinions, challenge ideas,
propose better ones, and say plainly when something looks wrong. The rules below exist to keep results honest, not to stop you thinking.

## What you are encouraged to do
* **Propose events and filters, and consult the literature while doing it.** Before settling an event definition or adding a filter, look at what is known
  (opening-range breakout research, intraday momentum / time-series momentum, volatility and time-of-day effects, gap behaviour, microstructure papers, practitioner write-ups).
  Use web search if you have it, otherwise your own knowledge; say which. Put the references and the reasoning in `HYPOTHESIS.md`. A filter with a stated, sensible rationale is worth more than a lucky one.
* Clean data, design sweeps, run the pipeline, read the reports and **interpret them critically** (including the `WM` where-it-works section and the near-tie section).
* Suggest follow-up experiments, and explain what you would test next and why. Disagree with the engine's output when you have a reason.
* Work alongside another model on the same project: leave clear notes (what you ran, what you decided, what is open) in the experiment's `HYPOTHESIS.md` or `docs/`, and review the other model's work rather than assuming it is right.

## How the pipeline judges an idea (so you can reason about it)
1. The event fires; 56 market-state features and the forward outcomes are recorded. Targets: 15-, 60-, 180-minute directional returns (a window that would pass the 16:00 close is cut at the close and flagged `truncated`) and a 60-bar path skew.
2. Three models (Ridge, spline, XGBoost) are scored walk-forward (out-of-fold). The top and bottom half of scores are compared with all events: the **uplift**, standardised by the target's sd. 24 trials per experiment.
3. Evidence: weekly-block bootstrap interval, permutation null, BH (and reported Bonferroni) across the experiment's 24 trials **and** every trial in the campaign, plus a fixed raw-p hurdle of t >= 3 (p <= 0.00135).
4. A trial passes when the null is beaten (raw p <= 0.00135 i.e. t >= 3, BH q <= 0.05, interval above 0), the uplift is at least 0.01, at least 1 selected trade/week, the effect is positive, it holds across calendar years (>= 70% positive, and not carried by one year),
   **no small set of trades carries it** (the best of 10 time-ordered batches carries <= 35% of the uplift), and >= 2 of 3 models agree. Then external verification and the event-parameter sensitivity check (every numeric event/filter parameter is probed at x0.75 and x1.25; the effect must stay positive and keep >= 50% of the uplift). List every probeable base parameter in `sensitivity_parameters` or the spec is refused.
5. After IS the engine stops: the human picks a config directly, approves a near-tied pair for the selection holdout (selection data, not confirmation), or declines. The final config is exactly one; CPCV then runs automatically as a robustness veto; the lockbox stays sealed.
6. After CPCV passes, `scripts/run_monetisation_study.py` can search an ATR bracket grid on development data (net of the 3-tick cost) and propose a bracket only if its +-25% neighbours are stable; otherwise it says `NO_STABLE_BRACKET`. It is not a trial and not confirmation.

## Non-negotiables (these protect the validity of every result; please keep them even when it is inconvenient)
1. **Never write, edit or delete anything in `approvals/`.** Approvals are the human's. Never open the final lockbox (`confirm_lockbox.py` is a stub).
2. **Do not touch holdout / lockbox data outside the approved process.** Never load, print or summarise rows at/after `development_end` during IS.
3. **Every variant you try is a trial.** Keep the trial tracker, the Bonferroni/BH universes and the campaign limits intact (24 trials per experiment, 20 experiments per campaign). Do not run side analyses that choose between alternatives outside the registry; exploratory looks must be logged as diagnostic-only observations and can only inspire a *new* experiment.
4. **Do not edit `engine/`, `features/`, `frozen/` or `ENGINE_VERSION`, and do not change an experiment's `event.py` / `EVENT_SPEC.yaml` / partitions after `freeze`.** If you think a gate or a rule is wrong, say so to the human with evidence; changing methodology is a deliberate, versioned decision, not something done mid-experiment.
5. **No fallback after a CPCV failure, and the engine/LLM never makes the human's choices** (final config, holdout approval, near-tie resolution).
6. **Be honest in reports.** Say what was skipped, what failed, what is uncertain. Do not call selection data "confirmation". A rejected result is a result.

## Practical notes
* One direction per experiment (`_LONG` / `_SHORT` are two experiments). Use one long development window per idea (>= 3 calendar years) and decide the 1- or 2-year holdout before looking at any result.
* Do not slice one idea into many short windows: it multiplies trials, shrinks samples and makes every adjusted p-value 1.0.
* Read `RESEARCH_RULES.md` for the exact rules and `README.md` for commands. Start a campaign with `scripts/new_experiment.py --new-campaign C001 --development-end <date> --selection-holdout-years <1|2>`.
* Memory/compute: keep concurrent engine runs within the owner's memory budget (the owner has used a 5 GB cap).
