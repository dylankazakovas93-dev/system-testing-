"""Registry of campaigns, experiments, selection trials and observations (CSV, append-only by API).

The registry is what makes the number of selection opportunities auditable:
  * a campaign holds at most ``max_experiments_per_campaign`` (20) experiments;
  * every experiment holds EXACTLY 24 selection trials (4 targets x 3 models x 2 states),
    pre-registered at freeze time, BEFORE any result exists;
  * there is no function that creates a 25th trial; ``integrity_check`` detects hand-edited CSVs.
"""
from __future__ import annotations

import csv
import itertools
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from engine.acceptance import decide_experiment
from engine.common import (CODE_ROOT, EngineError, Frozen, load_frozen, model_names, now_utc_iso,
                           primary_target_names)
from engine.multiplicity import benjamini_hochberg

CAMPAIGN_COLS = ["campaign_id", "lockbox_start", "max_experiments", "created_at", "status"]
EXPERIMENT_COLS = ["experiment_id", "campaign_id", "sequence_in_campaign", "status", "lineage_parent",
                   "created_at", "frozen_at", "revealed_at", "event_hash", "manifest_hash", "engine_version",
                   "n_selection_trials", "sensitivity_json", "research_verification"]
TRIAL_COLS = ["campaign_id", "experiment_id", "trial_id", "target", "model", "state", "event_hash",
              "feature_bank_hash", "target_bank_hash", "model_bank_hash", "trial_policy_hash", "train_period",
              "oos_period", "n_parent_events", "n_selected_events", "parent_frequency", "selected_frequency",
              "retention_ratio", "parent_effect", "selected_effect", "uplift", "standardized_uplift",
              "bootstrap_ci_low", "bootstrap_ci_high", "raw_p", "experiment_q", "campaign_q", "positive_years",
              "eligible_years", "decision", "rejection_reason",
              "status", "registered_at", "revealed_at", "target_sd", "n_oos_weeks"]
OBS_COLS = ["observation_id", "campaign_id", "experiment_id", "created_at", "category", "description",
            "metric_name", "metric_value", "eligible_for_promotion", "note"]
NUMERIC_TRIAL_COLS = ["n_parent_events", "n_selected_events", "parent_frequency", "selected_frequency",
                      "retention_ratio", "parent_effect", "selected_effect", "uplift", "standardized_uplift",
                      "bootstrap_ci_low", "bootstrap_ci_high", "raw_p", "experiment_q", "campaign_q",
                      "positive_years", "eligible_years", "target_sd", "n_oos_weeks"]
OBS_NOTE = "DIAGNOSTIC - CANNOT INFLUENCE PROMOTION IN THE GENERATING EXPERIMENT; lead for a NEW experiment only"


class CampaignLimitExceeded(EngineError):
    pass


class RegistryIntegrityError(EngineError):
    pass


@dataclass
class Workspace:
    """Where registry/ and experiments/ live. Frozen specs and engine code always come from CODE_ROOT."""
    root: Path

    def __post_init__(self):
        self.root = Path(self.root)

    @property
    def registry(self) -> Path:
        return self.root / "registry"

    @property
    def experiments(self) -> Path:
        return self.root / "experiments"

    def path(self, name: str) -> Path:
        return self.registry / name

    def init(self) -> "Workspace":
        self.registry.mkdir(parents=True, exist_ok=True)
        self.experiments.mkdir(parents=True, exist_ok=True)
        for name, cols in (("campaigns.csv", CAMPAIGN_COLS), ("experiments.csv", EXPERIMENT_COLS),
                           ("selection_trials.csv", TRIAL_COLS), ("observations.csv", OBS_COLS)):
            p = self.path(name)
            if not p.exists():
                _write(p, pd.DataFrame(columns=cols), cols)
        return self


def default_workspace() -> Workspace:
    return Workspace(CODE_ROOT).init()


# ---------------------------------------------------------------------------- CSV helpers
def _write(path: Path, df: pd.DataFrame, cols: list[str]) -> None:
    df = df.reindex(columns=cols)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    os.close(fd)
    df.to_csv(tmp, index=False, quoting=csv.QUOTE_MINIMAL)
    os.replace(tmp, path)


def _read(path: Path, cols: list[str]) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=cols)
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    return df.reindex(columns=cols).fillna("")


def read_campaigns(ws: Workspace) -> pd.DataFrame:
    return _read(ws.path("campaigns.csv"), CAMPAIGN_COLS)


def read_experiments(ws: Workspace) -> pd.DataFrame:
    return _read(ws.path("experiments.csv"), EXPERIMENT_COLS)


def read_trials(ws: Workspace) -> pd.DataFrame:
    return _read(ws.path("selection_trials.csv"), TRIAL_COLS)


def read_observations(ws: Workspace) -> pd.DataFrame:
    return _read(ws.path("observations.csv"), OBS_COLS)


def numeric_trials(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for c in NUMERIC_TRIAL_COLS:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


# ---------------------------------------------------------------------------- trial set
def trial_specs(frozen: Frozen | None = None) -> list[dict]:
    """The ONE predefined selection-trial set: targets x models x states (= 24). Order is frozen."""
    frozen = frozen or load_frozen()
    specs = [{"target": t, "model": m, "state": s}
             for t, m, s in itertools.product(primary_target_names(frozen), model_names(frozen),
                                              frozen.trial_policy["states"])]
    expected = frozen.trial_policy["expected_trials_per_experiment"]
    if len(specs) != expected:
        raise EngineError(f"frozen bank implies {len(specs)} trials, policy says {expected}")
    return specs


def trial_id(experiment_id: str, index: int) -> str:
    return f"{experiment_id}_T{index + 1:02d}"


# ---------------------------------------------------------------------------- campaigns / experiments
def create_campaign(ws: Workspace, campaign_id: str, lockbox_start: str, frozen: Frozen | None = None) -> None:
    frozen = frozen or load_frozen()
    pd.Timestamp(lockbox_start)                               # validates the date
    df = read_campaigns(ws)
    if campaign_id in set(df["campaign_id"]):
        raise EngineError(f"campaign {campaign_id} already exists")
    row = {"campaign_id": campaign_id, "lockbox_start": lockbox_start,
           "max_experiments": str(frozen.trial_policy["max_experiments_per_campaign"]),
           "created_at": now_utc_iso(), "status": "OPEN"}
    _write(ws.path("campaigns.csv"), pd.concat([df, pd.DataFrame([row])], ignore_index=True), CAMPAIGN_COLS)


def campaign_row(ws: Workspace, campaign_id: str) -> dict:
    df = read_campaigns(ws)
    hit = df[df["campaign_id"] == campaign_id]
    if hit.empty:
        raise EngineError(f"unknown campaign {campaign_id}; create it explicitly with --new-campaign")
    return hit.iloc[0].to_dict()


def register_experiment(ws: Workspace, campaign_id: str, lineage_parent: str = "",
                        frozen: Frozen | None = None) -> str:
    """Allocate the next experiment id inside a campaign. Fails on the 21st experiment of a campaign."""
    frozen = frozen or load_frozen()
    camp = campaign_row(ws, campaign_id)
    limit = int(frozen.trial_policy["max_experiments_per_campaign"])
    exps = read_experiments(ws)
    used = int((exps["campaign_id"] == campaign_id).sum())
    if used >= limit:
        raise CampaignLimitExceeded(
            f"campaign {campaign_id} already holds {used} experiments (MAX_EXPERIMENTS_PER_CAMPAIGN={limit}); "
            f"a new campaign must be created explicitly")
    if lineage_parent and lineage_parent not in set(exps["experiment_id"]):
        raise EngineError(f"unknown lineage parent {lineage_parent}")
    nums = [int(e.split("_")[1]) for e in exps["experiment_id"]] or [0]
    exp_id = f"EXP_{max(nums) + 1:04d}"
    row = {"experiment_id": exp_id, "campaign_id": campaign_id, "sequence_in_campaign": str(used + 1),
           "status": "DRAFT", "lineage_parent": lineage_parent, "created_at": now_utc_iso(),
           "engine_version": (CODE_ROOT / "ENGINE_VERSION").read_text().strip(), "n_selection_trials": "0",
           "sensitivity_json": "{}", "research_verification": "NOT_RUN"}
    _write(ws.path("experiments.csv"), pd.concat([exps, pd.DataFrame([row])], ignore_index=True), EXPERIMENT_COLS)
    return exp_id


def experiment_row(ws: Workspace, experiment_id: str) -> dict:
    df = read_experiments(ws)
    hit = df[df["experiment_id"] == experiment_id]
    if hit.empty:
        raise EngineError(f"unknown experiment {experiment_id}")
    return hit.iloc[0].to_dict()


def update_experiment(ws: Workspace, experiment_id: str, **fields) -> None:
    df = read_experiments(ws)
    m = df["experiment_id"] == experiment_id
    if not m.any():
        raise EngineError(f"unknown experiment {experiment_id}")
    for k, v in fields.items():
        if k not in EXPERIMENT_COLS:
            raise EngineError(f"unknown experiment column {k}")
        df.loc[m, k] = str(v)
    _write(ws.path("experiments.csv"), df, EXPERIMENT_COLS)


# ---------------------------------------------------------------------------- pre-registration
def preregister_trials(ws: Workspace, experiment_id: str, *, event_hash: str, manifest_hash: str,
                       hashes: dict[str, str], frozen: Frozen | None = None) -> list[str]:
    """Write the complete 24-trial set BEFORE any result exists. Callable exactly once per experiment."""
    frozen = frozen or load_frozen()
    exp = experiment_row(ws, experiment_id)
    if exp["status"] != "DRAFT":
        raise EngineError(f"{experiment_id} is {exp['status']}; trials can only be registered once, at freeze")
    trials = read_trials(ws)
    if (trials["experiment_id"] == experiment_id).any():
        raise EngineError(f"{experiment_id} already has registered trials; there is no API to add more")
    now = now_utc_iso()
    rows = []
    for i, spec in enumerate(trial_specs(frozen)):
        rows.append({"campaign_id": exp["campaign_id"], "experiment_id": experiment_id,
                     "trial_id": trial_id(experiment_id, i), **spec, "event_hash": event_hash,
                     "feature_bank_hash": hashes["feature_bank_hash"], "target_bank_hash": hashes["target_bank_hash"],
                     "model_bank_hash": hashes["model_bank_hash"], "trial_policy_hash": hashes["trial_policy_hash"],
                     "decision": "PENDING", "rejection_reason": "", "status": "PREREGISTERED",
                     "registered_at": now})
    new = pd.concat([trials, pd.DataFrame(rows)], ignore_index=True)
    _assert_trial_set(new, frozen)
    _write(ws.path("selection_trials.csv"), new, TRIAL_COLS)
    update_experiment(ws, experiment_id, status="FROZEN", frozen_at=now, event_hash=event_hash,
                      manifest_hash=manifest_hash, n_selection_trials=len(rows))
    return [r["trial_id"] for r in rows]


def _assert_trial_set(trials: pd.DataFrame, frozen: Frozen) -> None:
    expected = trial_specs(frozen)
    for exp_id, g in trials.groupby("experiment_id", sort=False):
        got = list(zip(g["target"], g["model"], g["state"]))
        want = [(s["target"], s["model"], s["state"]) for s in expected]
        if got != want:
            raise RegistryIntegrityError(f"{exp_id}: trial set is not exactly the frozen 24-trial product")
        if list(g["trial_id"]) != [trial_id(exp_id, i) for i in range(len(want))]:
            raise RegistryIntegrityError(f"{exp_id}: trial ids are not T01..T24 in frozen order")
    if trials["trial_id"].duplicated().any():
        raise RegistryIntegrityError("duplicate trial_id in registry")


# ---------------------------------------------------------------------------- reveal
def reveal_experiment(ws: Workspace, experiment_id: str, results: dict[str, dict], *, train_period: str,
                      oos_period: str, frozen: Frozen | None = None) -> pd.DataFrame:
    """Fill the pre-registered rows with results (keyed by trial_id), then recompute q-values and decisions.

    Refuses unknown trial ids, missing trials, or already revealed experiments.
    """
    frozen = frozen or load_frozen()
    trials = read_trials(ws)
    m = trials["experiment_id"] == experiment_id
    mine = trials[m]
    if len(mine) != frozen.trial_policy["expected_trials_per_experiment"]:
        raise RegistryIntegrityError(f"{experiment_id} has {len(mine)} registered trials, not 24")
    if set(results) != set(mine["trial_id"]):
        raise RegistryIntegrityError("results must be supplied for exactly the 24 pre-registered trials")
    if (mine["status"] != "PREREGISTERED").any():
        raise EngineError(f"{experiment_id} results were already revealed")
    now = now_utc_iso()
    trials = trials.copy()
    for idx in trials.index[m]:
        r = results[trials.at[idx, "trial_id"]]
        trials.at[idx, "train_period"], trials.at[idx, "oos_period"] = train_period, oos_period
        for src, dst in (("n_parent", "n_parent_events"), ("n_selected", "n_selected_events"),
                         ("parent_frequency", "parent_frequency"), ("selected_frequency", "selected_frequency"),
                         ("retention_ratio", "retention_ratio"), ("parent_effect", "parent_effect"),
                         ("selected_effect", "selected_effect"), ("uplift", "uplift"),
                         ("standardized_uplift", "standardized_uplift"), ("bootstrap_ci_low", "bootstrap_ci_low"),
                         ("bootstrap_ci_high", "bootstrap_ci_high"), ("raw_p", "raw_p"),
                         ("positive_years", "positive_years"), ("eligible_years", "eligible_years"),
                         ("target_sd", "target_sd"), ("n_oos_weeks", "n_oos_weeks")):
            trials.at[idx, dst] = repr(float(r[src])) if not isinstance(r[src], (int, np.integer)) else str(int(r[src]))
        trials.at[idx, "status"], trials.at[idx, "revealed_at"] = "REVEALED", now
    # experiment-level BH over ALL 24 trials (never only the winners)
    p = pd.to_numeric(trials.loc[m, "raw_p"]).to_numpy()
    trials.loc[m, "experiment_q"] = [repr(float(q)) for q in benjamini_hochberg(p)]
    _write(ws.path("selection_trials.csv"), trials, TRIAL_COLS)
    update_experiment(ws, experiment_id, status="REVEALED", revealed_at=now)
    return recompute_campaign(ws, mine["campaign_id"].iloc[0], frozen)[lambda d: d["experiment_id"] == experiment_id]


def recompute_campaign(ws: Workspace, campaign_id: str, frozen: Frozen | None = None) -> pd.DataFrame:
    """campaign_q = BH over EVERY revealed selection trial of the campaign; then re-decide all its experiments."""
    frozen = frozen or load_frozen()
    trials = read_trials(ws)
    exps = read_experiments(ws).set_index("experiment_id")
    rev = (trials["campaign_id"] == campaign_id) & (trials["status"] == "REVEALED")
    if rev.any():
        p = pd.to_numeric(trials.loc[rev, "raw_p"]).to_numpy()
        trials.loc[rev, "campaign_q"] = [repr(float(q)) for q in benjamini_hochberg(p)]
    for exp_id in trials.loc[rev, "experiment_id"].unique():
        mm = (trials["experiment_id"] == exp_id) & rev
        rows = numeric_trials(trials[mm]).to_dict("records")
        sens = json.loads(exps.at[exp_id, "sensitivity_json"] or "{}")
        decided = decide_experiment(rows, frozen.acceptance, sens)
        trials.loc[mm, "decision"] = [d["decision"] for d in decided]
        trials.loc[mm, "rejection_reason"] = [d["rejection_reason"] for d in decided]
    _write(ws.path("selection_trials.csv"), trials, TRIAL_COLS)
    return numeric_trials(read_trials(ws))[lambda d: d["campaign_id"] == campaign_id]


def set_sensitivity(ws: Workspace, experiment_id: str, status_by_group: dict[str, str],
                    frozen: Frozen | None = None) -> pd.DataFrame:
    """Store sensitivity verdicts (per 'TARGET|STATE' candidate group) and re-decide the campaign."""
    frozen = frozen or load_frozen()
    exp = experiment_row(ws, experiment_id)
    cur = json.loads(exp["sensitivity_json"] or "{}")
    cur.update(status_by_group)
    update_experiment(ws, experiment_id, sensitivity_json=json.dumps(cur, sort_keys=True))
    return recompute_campaign(ws, exp["campaign_id"], frozen)


def experiment_trials(ws: Workspace, experiment_id: str) -> pd.DataFrame:
    df = numeric_trials(read_trials(ws))
    return df[df["experiment_id"] == experiment_id].reset_index(drop=True)


# ---------------------------------------------------------------------------- observations
def add_observation(ws: Workspace, experiment_id: str, category: str, description: str,
                    metric_name: str = "", metric_value: float | str = "") -> str:
    """Diagnostics are stored separately from selection trials and can never promote anything."""
    exp = experiment_row(ws, experiment_id)                   # must reference the generating experiment
    df = read_observations(ws)
    oid = f"OBS_{len(df) + 1:05d}"
    row = {"observation_id": oid, "campaign_id": exp["campaign_id"], "experiment_id": experiment_id,
           "created_at": now_utc_iso(), "category": category, "description": description,
           "metric_name": metric_name, "metric_value": str(metric_value), "eligible_for_promotion": "False",
           "note": OBS_NOTE}
    _write(ws.path("observations.csv"), pd.concat([df, pd.DataFrame([row])], ignore_index=True), OBS_COLS)
    return oid


# ---------------------------------------------------------------------------- integrity / summary
def integrity_check(ws: Workspace, frozen: Frozen | None = None) -> dict:
    """Raises RegistryIntegrityError if the registry does not satisfy the frozen opportunity accounting."""
    frozen = frozen or load_frozen()
    exps, trials, obs = read_experiments(ws), read_trials(ws), read_observations(ws)
    limit = int(frozen.trial_policy["max_experiments_per_campaign"])
    per_camp = exps.groupby("campaign_id").size()
    if (per_camp > limit).any():
        raise RegistryIntegrityError(f"campaign exceeds {limit} experiments: {per_camp[per_camp > limit].to_dict()}")
    if exps["experiment_id"].duplicated().any():
        raise RegistryIntegrityError("duplicate experiment ids")
    known = set(exps["experiment_id"])
    if not set(trials["experiment_id"]) <= known:
        raise RegistryIntegrityError("selection trials reference unknown experiments")
    _assert_trial_set(trials, frozen)
    per_exp = trials.groupby("experiment_id").size()
    if (per_exp != frozen.trial_policy["expected_trials_per_experiment"]).any():
        raise RegistryIntegrityError("an experiment does not have exactly 24 selection trials")
    cap = frozen.trial_policy["max_selection_trials_per_campaign"]
    if (trials.groupby("campaign_id").size() > cap).any():
        raise RegistryIntegrityError(f"campaign exceeds {cap} selection trials")
    revealed = trials[trials["status"] == "REVEALED"]
    if (pd.to_numeric(revealed["raw_p"], errors="coerce").isna()).any():
        raise RegistryIntegrityError("revealed trial without raw_p")
    if not set(obs["experiment_id"]) <= known:
        raise RegistryIntegrityError("observation references an unknown experiment")
    if (obs["eligible_for_promotion"] != "False").any():
        raise RegistryIntegrityError("observations can never be eligible for promotion")
    return {"experiments": int(len(exps)), "selection_trials": int(len(trials)),
            "revealed_trials": int(len(revealed)), "observations": int(len(obs))}


def campaign_summary(ws: Workspace, campaign_id: str, frozen: Frozen | None = None) -> dict:
    frozen = frozen or load_frozen()
    camp = campaign_row(ws, campaign_id)
    exps = read_experiments(ws)
    exps = exps[exps["campaign_id"] == campaign_id]
    trials = numeric_trials(read_trials(ws))
    trials = trials[trials["campaign_id"] == campaign_id]
    limit = int(frozen.trial_policy["max_experiments_per_campaign"])
    return {"campaign_id": campaign_id, "lockbox_start": camp["lockbox_start"],
            "experiments_used": int(len(exps)), "experiments_max": limit,
            "selection_trials_registered": int(len(trials)),
            "selection_trials_max": int(frozen.trial_policy["max_selection_trials_per_campaign"]),
            "selection_trials_revealed": int((trials["status"] == "REVEALED").sum()),
            "promotable_trials": int((trials["decision"] == "PROMOTABLE").sum()),
            "pending_sensitivity": int((trials["decision"] == "PROMOTABLE_PENDING_SENSITIVITY").sum()),
            "experiments": exps[["experiment_id", "status", "lineage_parent", "research_verification"]].to_dict("records")}
