"""Registry of campaigns, experiments, selection trials, observations, the SELECTION HOLDOUT access ledger, the final-config ledger and CPCV results.

What it proves:
  * a campaign holds at most 20 experiments => at most 480 selection trials (campaign universe = 24 x E revealed);
  * every experiment holds EXACTLY 24 pre-registered selection trials (4 targets x 3 models x 2 states), each with a
    selection_opportunity_number, written at freeze BEFORE any result exists; there is no API for a 25th;
  * the 24 result rows of a revealed experiment are hash-sealed (trial_ledger_hash); only the retroactive campaign-level
    adjusted values and decisions may legitimately change afterwards;
  * campaign_q / campaign_bonferroni_p are recomputed over EVERY revealed trial of the campaign after each reveal and all
    earlier experiments are re-evaluated (an earlier candidate can lose eligibility);
  * selection_holdout_access.csv is an append-only hash chain: an experiment present there has SPENT its SELECTION HOLDOUT.
"""
from __future__ import annotations

import csv
import hashlib
import itertools
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from engine.acceptance import (NO_CANDIDATE, PROVISIONAL, SHORTLIST, decide_experiment, is_status_of,
                               lifecycle_from_is_status)
from engine.common import (CODE_ROOT, EngineError, Frozen, canonical_json, load_frozen, model_names, now_utc_iso,
                           primary_target_names)
from engine.multiplicity import benjamini_hochberg
from engine.partitions import parse_partitions

CAMPAIGN_COLS = ["campaign_id", "development_end", "selection_holdout_end", "lockbox_start", "max_experiments", "created_at", "status",
                 "selection_holdout_freeze_hash", "selection_holdout_spent_at"]
CAMPAIGN_STATUSES = ("OPEN", "SELECTION_HOLDOUT_FROZEN", "SELECTION_HOLDOUT_SPENT")      # OPEN -> (human) freeze -> SELECTION_HOLDOUT_FROZEN -> (human) open once -> SELECTION_HOLDOUT_SPENT
EXPERIMENT_COLS = ["experiment_id", "campaign_id", "sequence_in_campaign", "status", "is_status", "lineage_parent",
                   "created_at", "frozen_at", "revealed_at", "event_hash", "manifest_hash", "manifest_sha256",
                   "engine_version", "n_selection_trials", "cumulative_campaign_selection_trials", "trial_ledger_hash",
                   "sensitivity_json", "verification_json", "research_verification", "is_report_sha256", "status_history"]
TRIAL_COLS = ["campaign_id", "experiment_id", "trial_id", "target", "model", "state", "manifest_hash", "event_hash",
              "feature_bank_hash", "target_bank_hash", "model_bank_hash", "trial_policy_hash", "is_data_hash",
              "train_period", "validation_period", "selection_opportunity_number", "cumulative_campaign_selection_trials",
              "n_parent_events", "n_selected_events", "parent_frequency", "selected_frequency", "retention_ratio",
              "parent_effect", "selected_effect", "uplift", "standardized_uplift", "bootstrap_ci_low", "bootstrap_ci_high",
              "raw_p", "experiment_q", "experiment_bonferroni_p", "campaign_q", "campaign_bonferroni_p",
              "positive_years", "positive_uplift_years", "eligible_years", "folds_evaluated", "positive_effect_folds",
              "positive_uplift_folds", "year_concentration_share", "year_concentration_warning",
              "decision", "rejection_reason", "status", "registered_at", "revealed_at", "target_sd", "n_cv_weeks"]
OBS_COLS = ["observation_id", "campaign_id", "experiment_id", "created_at", "category", "description",
            "metric_name", "metric_value", "eligible_for_promotion", "diagnostic_label", "note"]
# ONE row per campaign: the shared selection holdout partition is opened exactly once for the whole campaign.
SELECTION_HOLDOUT_ACCESS_COLS = ["campaign_id", "freeze_hash", "open_approval_file_hash", "experiments", "approved_experiment_groups",
                   "n_holdout_evaluations", "selection_holdout_start", "selection_holdout_end", "unlock_timestamp", "code_hash", "prev_row_hash", "row_hash"]
SELECTION_HOLDOUT_TRIAL_COLS = ["campaign_id", "experiment_id", "selection_holdout_trial_id", "group_id", "target", "state", "model", "n_parent_events",
                  "n_selected_events", "parent_frequency", "selected_frequency", "retention_ratio", "parent_effect",
                  "selected_effect", "uplift", "standardized_uplift", "bootstrap_ci_low", "bootstrap_ci_high", "raw_p",
                  "selection_holdout_q", "selection_holdout_bonferroni_p", "selection_holdout_trials_in_family", "gates_pass", "decision", "rejection_reason", "revealed_at"]
CPCV_COLS = ["campaign_id", "experiment_id", "group_id", "target", "state", "model", "n_valid_splits", "median_effect",
             "median_uplift", "p10_uplift", "p90_uplift", "fraction_effect_positive", "fraction_uplift_positive",
             "worst_split", "best_split", "cpcv_pass", "group_cpcv_pass", "pbo_diagnostic", "revealed_at"]
NUMERIC_TRIAL_COLS = ["selection_opportunity_number", "cumulative_campaign_selection_trials", "n_parent_events",
                      "n_selected_events", "parent_frequency", "selected_frequency", "retention_ratio", "parent_effect",
                      "selected_effect", "uplift", "standardized_uplift", "bootstrap_ci_low", "bootstrap_ci_high", "raw_p",
                      "experiment_q", "experiment_bonferroni_p", "campaign_q", "campaign_bonferroni_p", "positive_years",
                      "positive_uplift_years", "eligible_years", "folds_evaluated", "positive_effect_folds",
                      "positive_uplift_folds", "year_concentration_share", "target_sd", "n_cv_weeks"]
# fields sealed by trial_ledger_hash at reveal (campaign-adjusted values and decisions are retroactive by design)
SEALED_TRIAL_FIELDS = ["campaign_id", "experiment_id", "trial_id", "target", "model", "state", "manifest_hash", "event_hash",
                       "feature_bank_hash", "target_bank_hash", "model_bank_hash", "trial_policy_hash", "is_data_hash",
                       "train_period", "validation_period", "selection_opportunity_number",
                       "cumulative_campaign_selection_trials", "n_parent_events", "n_selected_events", "parent_frequency",
                       "selected_frequency", "retention_ratio", "parent_effect", "selected_effect", "uplift",
                       "standardized_uplift", "bootstrap_ci_low", "bootstrap_ci_high", "raw_p", "experiment_q",
                       "experiment_bonferroni_p", "positive_years", "positive_uplift_years", "eligible_years",
                       "folds_evaluated", "positive_effect_folds", "positive_uplift_folds", "year_concentration_share",
                       "year_concentration_warning", "revealed_at", "target_sd", "n_cv_weeks"]
FINAL_CONFIG_COLS = ["campaign_id", "experiment_id", "event", "selected_config_id", "is_rank", "near_tie_cluster", "selection_holdout_used",
                     "selection_holdout_rank", "human_selection_file_hash", "manifest_hash", "frozen_at", "cpcv_status", "prev_row_hash", "row_hash"]
# Experiment lifecycle (v1.2). Every status below is explicit; nothing is called "confirmed" unless it is the final untouched lockbox.
LIFECYCLE = ["DRAFT", "FROZEN", "IS_REJECTED", "IS_PROVISIONAL_CANDIDATE", "IS_SHORTLIST_ELIGIBLE",
             "NEAR_TIE_REVIEW_REQUIRED", "AWAITING_HUMAN_SELECTION_HOLDOUT_APPROVAL", "SELECTION_HOLDOUT_FROZEN", "SELECTION_HOLDOUT_SPENT",
             "AWAITING_HUMAN_FINAL_CONFIG_SELECTION", "SELECTION_HOLDOUT_SKIPPED", "FINAL_CONFIG_FROZEN", "HUMAN_DECLINED",
             "CPCV_REJECTED", "CPCV_CONFIRMED", "AWAITING_FINAL_LOCKBOX_APPROVAL", "LOCKBOX_REJECTED", "LOCKBOX_CONFIRMED",
             "SELECTION_HOLDOUT_CONTAMINATED"]
# AWAITING_HUMAN_SELECTION_HOLDOUT_APPROVAL is a documented ALIAS of NEAR_TIE_REVIEW_REQUIRED (the engine assigns NEAR_TIE_REVIEW_REQUIRED
# when IS finds a near-tie cluster; the holdout approval is a human file validated at the campaign freeze).
STATUS_ALIASES = {"AWAITING_HUMAN_SELECTION_HOLDOUT_APPROVAL": "NEAR_TIE_REVIEW_REQUIRED"}
IS_STAGE = ("IS_REJECTED", "IS_PROVISIONAL_CANDIDATE", "AWAITING_HUMAN_FINAL_CONFIG_SELECTION", "NEAR_TIE_REVIEW_REQUIRED")
OBS_NOTE = "DIAGNOSTIC - CANNOT INFLUENCE PROMOTION IN THE GENERATING EXPERIMENT; lead for a NEW experiment only"
DIAG_LABEL = "DIAGNOSTIC ONLY — NOT A SELECTION TRIAL"


class SelectionHoldoutContaminated(EngineError):
    """The shared selection holdout partition was already spent (by this campaign or an overlapping one)."""


class CampaignClosed(EngineError):
    """The campaign's SELECTION HOLDOUT is frozen or spent: no new experiment, verification or IS report may change it."""


class CampaignLimitExceeded(EngineError):
    pass


class RegistryIntegrityError(EngineError):
    pass


@dataclass
class Workspace:
    """Where registry/, experiments/ and approvals/ live. Frozen specs and engine code always come from CODE_ROOT."""
    root: Path

    def __post_init__(self):
        self.root = Path(self.root)

    @property
    def registry(self) -> Path:
        return self.root / "registry"

    @property
    def experiments(self) -> Path:
        return self.root / "experiments"

    @property
    def approvals(self) -> Path:
        return self.root / "approvals"

    def path(self, name: str) -> Path:
        return self.registry / name

    def init(self) -> "Workspace":
        self.registry.mkdir(parents=True, exist_ok=True)
        self.experiments.mkdir(parents=True, exist_ok=True)
        self.approvals.mkdir(parents=True, exist_ok=True)
        for name, cols in (("campaigns.csv", CAMPAIGN_COLS), ("experiments.csv", EXPERIMENT_COLS),
                           ("selection_trials.csv", TRIAL_COLS), ("observations.csv", OBS_COLS),
                           ("selection_holdout_access.csv", SELECTION_HOLDOUT_ACCESS_COLS), ("selection_holdout_trials.csv", SELECTION_HOLDOUT_TRIAL_COLS),
                           ("cpcv_results.csv", CPCV_COLS), ("final_configs.csv", FINAL_CONFIG_COLS)):
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


def read_selection_holdout_access(ws: Workspace) -> pd.DataFrame:
    return _read(ws.path("selection_holdout_access.csv"), SELECTION_HOLDOUT_ACCESS_COLS)


def read_selection_holdout_trials(ws: Workspace) -> pd.DataFrame:
    return _read(ws.path("selection_holdout_trials.csv"), SELECTION_HOLDOUT_TRIAL_COLS)


def read_final_configs(ws: Workspace) -> pd.DataFrame:
    return _read(ws.path("final_configs.csv"), FINAL_CONFIG_COLS)


def read_cpcv(ws: Workspace) -> pd.DataFrame:
    return _read(ws.path("cpcv_results.csv"), CPCV_COLS)


def numeric_trials(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for c in NUMERIC_TRIAL_COLS:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["year_concentration_warning"] = df["year_concentration_warning"].astype(str).str.lower() == "true"
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


def group_id(target: str, state: str) -> str:
    return f"{target}|{state}"


# ---------------------------------------------------------------------------- campaigns / experiments
def create_campaign(ws: Workspace, campaign_id: str, partitions: dict, frozen: Frozen | None = None) -> None:
    """Open a campaign = one development / selection-holdout / final-lockbox generation with frozen partition dates."""
    frozen = frozen or load_frozen()
    p = parse_partitions(partitions)                          # validates chronology and non-overlap
    df = read_campaigns(ws)
    if campaign_id in set(df["campaign_id"]):
        raise EngineError(f"campaign {campaign_id} already exists")
    assert_selection_holdout_partition_untouched(ws, p.as_dict())
    d = p.as_dict()
    row = {"campaign_id": campaign_id, **d, "max_experiments": str(frozen.trial_policy["max_experiments_per_campaign"]),
           "created_at": now_utc_iso(), "status": "OPEN", "selection_holdout_freeze_hash": "", "selection_holdout_spent_at": ""}
    _write(ws.path("campaigns.csv"), pd.concat([df, pd.DataFrame([row])], ignore_index=True), CAMPAIGN_COLS)


def campaign_row(ws: Workspace, campaign_id: str) -> dict:
    df = read_campaigns(ws)
    hit = df[df["campaign_id"] == campaign_id]
    if hit.empty:
        raise EngineError(f"unknown campaign {campaign_id}; create it explicitly with --new-campaign")
    return hit.iloc[0].to_dict()


def update_campaign(ws: Workspace, campaign_id: str, **fields) -> None:
    df = read_campaigns(ws)
    i = df.index[df["campaign_id"] == campaign_id]
    if len(i) != 1:
        raise EngineError(f"unknown campaign {campaign_id}")
    for k, v in fields.items():
        if k == "status" and v not in CAMPAIGN_STATUSES:
            raise EngineError(f"unknown campaign status {v}")
        df.loc[i[0], k] = str(v)
    _write(ws.path("campaigns.csv"), df, CAMPAIGN_COLS)


def assert_campaign_open(ws: Workspace, campaign_id: str, action: str) -> None:
    """Campaign-level SELECTION HOLDOUT accounting: once the campaign's SELECTION HOLDOUT is frozen or spent nothing in the campaign may change."""
    st = campaign_row(ws, campaign_id)["status"]
    if st == "SELECTION_HOLDOUT_SPENT":
        raise SelectionHoldoutContaminated(f"CAMPAIGN SELECTION HOLDOUT HAS BEEN SPENT ({campaign_id}): cannot {action}. The shared selection holdout partition is "
                              f"no longer untouched; new research needs a NEW campaign with a new, non-overlapping SELECTION HOLDOUT partition")
    if st != "OPEN":
        raise CampaignClosed(f"campaign {campaign_id} is {st}: cannot {action}")


def _intervals_overlap(a: dict, b: dict) -> bool:
    import pandas as _pd
    a0, a1 = _pd.Timestamp(a["development_end"]), _pd.Timestamp(a["selection_holdout_end"])
    b0, b1 = _pd.Timestamp(b["development_end"]), _pd.Timestamp(b["selection_holdout_end"])
    return a0 < b1 and b0 < a1                                 # half-open [development_end, selection_holdout_end)


def assert_selection_holdout_partition_untouched(ws: Workspace, partitions: dict, exclude_campaign: str = "") -> None:
    """Refuse any campaign whose selection-holdout interval overlaps the SELECTION HOLDOUT interval of an already SPENT campaign."""
    for _, c in read_campaigns(ws).iterrows():
        if c["campaign_id"] != exclude_campaign and c["status"] == "SELECTION_HOLDOUT_SPENT" and _intervals_overlap(c.to_dict(), partitions):
            raise SelectionHoldoutContaminated(
                f"SELECTION HOLDOUT CONTAMINATED: selection holdout [{partitions['development_end']}, {partitions['selection_holdout_end']}) overlaps the SELECTION HOLDOUT partition "
                f"[{c['development_end']}, {c['selection_holdout_end']}) already spent by campaign {c['campaign_id']}; it cannot be claimed as untouched confirmation")


def campaign_partitions(ws: Workspace, campaign_id: str) -> dict:
    c = campaign_row(ws, campaign_id)
    return {k: c[k] for k in ("development_end", "selection_holdout_end", "lockbox_start")}


def register_experiment(ws: Workspace, campaign_id: str, lineage_parent: str = "",
                        frozen: Frozen | None = None) -> str:
    """Allocate the next experiment id inside a campaign. Fails on the 21st experiment of a campaign."""
    frozen = frozen or load_frozen()
    campaign_row(ws, campaign_id)
    assert_campaign_open(ws, campaign_id, "register a new experiment")
    limit = int(frozen.trial_policy["max_experiments_per_campaign"])
    exps = read_experiments(ws)
    used = int((exps["campaign_id"] == campaign_id).sum())
    if used >= limit:
        raise CampaignLimitExceeded(
            f"campaign {campaign_id} already holds {used} experiments (MAX_EXPERIMENTS_PER_CAMPAIGN={limit}); "
            f"a new campaign must be created explicitly")
    if lineage_parent and lineage_parent not in set(exps["experiment_id"]):
        raise EngineError(f"unknown lineage parent {lineage_parent}")
    if lineage_parent and final_config_of(ws, lineage_parent) is not None:
        raise EngineError(f"{lineage_parent} already froze its final configuration (CPCV or lockbox stage): this lineage STOPS. "
                          f"Using another configuration needs a new explicitly registered research lineage/campaign, not a child of {lineage_parent}")
    nums = [int(e.split("_")[1]) for e in exps["experiment_id"]] or [0]
    exp_id = f"EXP_{max(nums) + 1:04d}"
    row = {"experiment_id": exp_id, "campaign_id": campaign_id, "sequence_in_campaign": str(used + 1),
           "status": "DRAFT", "is_status": "", "lineage_parent": lineage_parent, "created_at": now_utc_iso(),
           "engine_version": (CODE_ROOT / "ENGINE_VERSION").read_text().strip(), "n_selection_trials": "0",
           "sensitivity_json": "{}", "verification_json": "{}", "research_verification": "NOT_RUN",
           "status_history": json.dumps([["DRAFT", now_utc_iso(), "created"]])}
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


def set_status(ws: Workspace, experiment_id: str, status: str, note: str = "") -> None:
    """Move an experiment along its lifecycle (history is appended, never rewritten)."""
    if status not in LIFECYCLE:
        raise EngineError(f"unknown lifecycle status {status}")
    exp = experiment_row(ws, experiment_id)
    hist = json.loads(exp["status_history"] or "[]")
    if exp["status"] != status:
        hist.append([status, now_utc_iso(), note])
    update_experiment(ws, experiment_id, status=status, status_history=json.dumps(hist))


def is_revealed(exp: dict) -> bool:
    return bool(exp["revealed_at"])


# ---------------------------------------------------------------------------- pre-registration
def preregister_trials(ws: Workspace, experiment_id: str, *, event_hash: str, manifest_hash: str, manifest_sha256: str = "",
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
    seq = int(exp["sequence_in_campaign"])
    n_tr = frozen.trial_policy["expected_trials_per_experiment"]
    rows = []
    for i, spec in enumerate(trial_specs(frozen)):
        rows.append({"campaign_id": exp["campaign_id"], "experiment_id": experiment_id,
                     "trial_id": trial_id(experiment_id, i), **spec, "manifest_hash": manifest_hash,
                     "event_hash": event_hash, "feature_bank_hash": hashes["feature_bank_hash"],
                     "target_bank_hash": hashes["target_bank_hash"], "model_bank_hash": hashes["model_bank_hash"],
                     "trial_policy_hash": hashes["trial_policy_hash"],
                     "selection_opportunity_number": str(n_tr * (seq - 1) + i + 1),
                     "decision": "PENDING", "rejection_reason": "", "status": "PREREGISTERED", "registered_at": now})
    new = pd.concat([trials, pd.DataFrame(rows)], ignore_index=True)
    _assert_trial_set(new, frozen)
    _write(ws.path("selection_trials.csv"), new, TRIAL_COLS)
    update_experiment(ws, experiment_id, event_hash=event_hash, manifest_hash=manifest_hash,
                      manifest_sha256=manifest_sha256, frozen_at=now, n_selection_trials=len(rows))
    set_status(ws, experiment_id, "FROZEN", "frozen; 24 selection trials pre-registered")
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
    opp = pd.to_numeric(trials["selection_opportunity_number"], errors="coerce")
    if opp.isna().any() or opp.duplicated().any():
        # opportunity numbers are only unique within a campaign
        for c, g in trials.groupby("campaign_id"):
            o = pd.to_numeric(g["selection_opportunity_number"], errors="coerce")
            if o.isna().any() or o.duplicated().any():
                raise RegistryIntegrityError(f"campaign {c}: selection_opportunity_number missing or duplicated")


def trial_ledger_hash(trial_rows: pd.DataFrame) -> str:
    """Hash of the sealed (result) fields of one experiment's 24 trials, in trial_id order."""
    g = trial_rows.sort_values("trial_id")
    payload = [{k: str(r[k]) for k in SEALED_TRIAL_FIELDS} for _, r in g.iterrows()]
    return hashlib.sha256(canonical_json(payload).encode()).hexdigest()


# ---------------------------------------------------------------------------- reveal
_RESULT_MAP = [("n_parent", "n_parent_events"), ("n_selected", "n_selected_events"), ("parent_frequency", "parent_frequency"),
               ("selected_frequency", "selected_frequency"), ("retention_ratio", "retention_ratio"),
               ("parent_effect", "parent_effect"), ("selected_effect", "selected_effect"), ("uplift", "uplift"),
               ("standardized_uplift", "standardized_uplift"), ("bootstrap_ci_low", "bootstrap_ci_low"),
               ("bootstrap_ci_high", "bootstrap_ci_high"), ("raw_p", "raw_p"), ("positive_years", "positive_years"),
               ("positive_uplift_years", "positive_uplift_years"), ("eligible_years", "eligible_years"),
               ("folds_evaluated", "folds_evaluated"), ("positive_effect_folds", "positive_effect_folds"),
               ("positive_uplift_folds", "positive_uplift_folds"), ("year_concentration_share", "year_concentration_share"),
               ("target_sd", "target_sd"), ("n_cv_weeks", "n_cv_weeks")]


def _fmt(v) -> str:
    if isinstance(v, (int, np.integer)) and not isinstance(v, bool):
        return str(int(v))
    return repr(float(v))


def reveal_experiment(ws: Workspace, experiment_id: str, results: dict[str, dict], *, train_period: str,
                      validation_period: str, is_data_hash: str = "", frozen: Frozen | None = None) -> pd.DataFrame:
    """Fill the pre-registered rows with IS results (keyed by trial_id), compute experiment BH + Bonferroni over ALL 24,
    seal the ledger, then recompute the whole campaign. Refuses unknown/missing trial ids and double reveals."""
    frozen = frozen or load_frozen()
    assert_campaign_open(ws, experiment_row(ws, experiment_id)["campaign_id"], f"reveal IS results of {experiment_id}")
    trials = read_trials(ws)
    m = trials["experiment_id"] == experiment_id
    mine = trials[m]
    n_tr = frozen.trial_policy["expected_trials_per_experiment"]
    if len(mine) != n_tr:
        raise RegistryIntegrityError(f"{experiment_id} has {len(mine)} registered trials, not {n_tr}")
    if set(results) != set(mine["trial_id"]):
        raise RegistryIntegrityError("results must be supplied for exactly the 24 pre-registered trials")
    if (mine["status"] != "PREREGISTERED").any():
        raise EngineError(f"{experiment_id} results were already revealed")
    camp = mine["campaign_id"].iloc[0]
    already = int((trials[(trials["campaign_id"] == camp)]["status"] == "REVEALED").sum())
    now = now_utc_iso()
    trials = trials.copy()
    for idx in trials.index[m]:
        r = results[trials.at[idx, "trial_id"]]
        trials.at[idx, "train_period"], trials.at[idx, "validation_period"] = train_period, validation_period
        trials.at[idx, "is_data_hash"] = is_data_hash
        for src, dst in _RESULT_MAP:
            trials.at[idx, dst] = _fmt(r[src])
        trials.at[idx, "year_concentration_warning"] = str(bool(r.get("year_concentration_warning", False)))
        trials.at[idx, "cumulative_campaign_selection_trials"] = str(already + n_tr)
        trials.at[idx, "status"], trials.at[idx, "revealed_at"] = "REVEALED", now
    p = pd.to_numeric(trials.loc[m, "raw_p"]).to_numpy()
    trials.loc[m, "experiment_q"] = [repr(float(q)) for q in benjamini_hochberg(p)]
    trials.loc[m, "experiment_bonferroni_p"] = [repr(float(min(x * n_tr, 1.0))) for x in p]
    ledger = trial_ledger_hash(trials[m])
    _write(ws.path("selection_trials.csv"), trials, TRIAL_COLS)
    update_experiment(ws, experiment_id, revealed_at=now, trial_ledger_hash=ledger,
                      cumulative_campaign_selection_trials=already + n_tr)
    return recompute_campaign(ws, camp, frozen)[lambda d: d["experiment_id"] == experiment_id]


def recompute_campaign(ws: Workspace, campaign_id: str, frozen: Frozen | None = None) -> pd.DataFrame:
    """RETROACTIVE campaign adjustment: reload every revealed trial of the campaign, recompute campaign BH and campaign
    Bonferroni (universe = all revealed trials = 24 x E), rewrite every historical adjusted value and re-evaluate the status
    of every experiment still at the IS stage. Earlier candidates may lose (or gain) eligibility."""
    frozen = frozen or load_frozen()
    trials = read_trials(ws)
    exps = read_experiments(ws).set_index("experiment_id")
    rev = (trials["campaign_id"] == campaign_id) & (trials["status"] == "REVEALED")
    if rev.any():
        p = pd.to_numeric(trials.loc[rev, "raw_p"]).to_numpy()
        trials.loc[rev, "campaign_q"] = [repr(float(q)) for q in benjamini_hochberg(p)]
        trials.loc[rev, "campaign_bonferroni_p"] = [repr(float(min(x * len(p), 1.0))) for x in p]
    status_updates = {}
    for exp_id in trials.loc[rev, "experiment_id"].unique():
        mm = (trials["experiment_id"] == exp_id) & rev
        rows = numeric_trials(trials[mm]).to_dict("records")
        sens = json.loads(exps.at[exp_id, "sensitivity_json"] or "{}")
        ver = json.loads(exps.at[exp_id, "verification_json"] or "{}")
        decided = decide_experiment(rows, frozen.acceptance, sens, ver)
        trials.loc[mm, "decision"] = [d["decision"] for d in decided]
        trials.loc[mm, "rejection_reason"] = [d["rejection_reason"] for d in decided]
        status_updates[exp_id] = is_status_of(d["decision"] for d in decided)
    _write(ws.path("selection_trials.csv"), trials, TRIAL_COLS)
    for exp_id, st in status_updates.items():
        update_experiment(ws, exp_id, is_status=st)
        cur = experiment_row(ws, exp_id)["status"]
        if cur in IS_STAGE + ("FROZEN",):
            new = lifecycle_from_is_status(st)
            if cur == "NEAR_TIE_REVIEW_REQUIRED" and new == "AWAITING_HUMAN_FINAL_CONFIG_SELECTION":
                new = cur                                           # the near-tie review is re-derived by the IS report, never silently dropped here
            set_status(ws, exp_id, new, f"IS status {st} at campaign universe {int(rev.sum())} revealed trials")
    return numeric_trials(read_trials(ws))[lambda d: d["campaign_id"] == campaign_id]


def set_sensitivity(ws: Workspace, experiment_id: str, status_by_group: dict[str, str],
                    frozen: Frozen | None = None) -> pd.DataFrame:
    frozen = frozen or load_frozen()
    exp = experiment_row(ws, experiment_id)
    assert_campaign_open(ws, exp["campaign_id"], "change a sensitivity verdict")
    cur = json.loads(exp["sensitivity_json"] or "{}")
    cur.update(status_by_group)
    update_experiment(ws, experiment_id, sensitivity_json=json.dumps(cur, sort_keys=True))
    return recompute_campaign(ws, exp["campaign_id"], frozen)


def set_verification(ws: Workspace, experiment_id: str, paths: dict[str, dict], overall: str = "",
                     frozen: Frozen | None = None) -> pd.DataFrame:
    """Record external-verifier results per model path ('TARGET|MODEL' -> {label, mode}) and re-decide the campaign."""
    frozen = frozen or load_frozen()
    exp = experiment_row(ws, experiment_id)
    assert_campaign_open(ws, exp["campaign_id"], "record external verification")
    cur = json.loads(exp["verification_json"] or "{}")
    cur.update(paths)
    fields = {"verification_json": json.dumps(cur, sort_keys=True)}
    if overall:
        fields["research_verification"] = overall
    update_experiment(ws, experiment_id, **fields)
    if is_revealed(exp):
        return recompute_campaign(ws, exp["campaign_id"], frozen)
    return pd.DataFrame()


def experiment_trials(ws: Workspace, experiment_id: str) -> pd.DataFrame:
    df = numeric_trials(read_trials(ws))
    return df[df["experiment_id"] == experiment_id].reset_index(drop=True)


# ---------------------------------------------------------------------------- observations (diagnostics)
def add_observation(ws: Workspace, experiment_id: str, category: str, description: str,
                    metric_name: str = "", metric_value: float | str = "") -> str:
    """Diagnostics are stored separately from selection trials and can never promote anything."""
    exp = experiment_row(ws, experiment_id)                   # must reference the generating experiment
    df = read_observations(ws)
    oid = f"OBS_{len(df) + 1:05d}"
    row = {"observation_id": oid, "campaign_id": exp["campaign_id"], "experiment_id": experiment_id,
           "created_at": now_utc_iso(), "category": category, "description": description,
           "metric_name": metric_name, "metric_value": str(metric_value), "eligible_for_promotion": "False",
           "diagnostic_label": DIAG_LABEL, "note": OBS_NOTE}
    _write(ws.path("observations.csv"), pd.concat([df, pd.DataFrame([row])], ignore_index=True), OBS_COLS)
    return oid


def log_exploratory_observation(ws: Workspace, experiment_id: str, description: str, *, diagnostic_only: bool,
                                category: str = "exploratory", metric_name: str = "", metric_value=""):
    """The ONLY sanctioned way to record an unexpected exploratory analysis. It must declare diagnostic_only=True and is
    technically unable to alter any trial row, decision or lifecycle status of the current experiment."""
    if diagnostic_only is not True:
        raise EngineError("exploratory analyses are allowed only with diagnostic_only=True. If the result can influence "
                          "which configuration is selected it is a SELECTION OPPORTUNITY and needs a NEW pre-registered experiment")
    return add_observation(ws, experiment_id, category, description, metric_name, metric_value)


# ---------------------------------------------------------------------------- SELECTION HOLDOUT access ledger (append-only hash chain)
def _row_hash(prev: str, row: dict) -> str:
    body = {k: row[k] for k in SELECTION_HOLDOUT_ACCESS_COLS if k not in ("prev_row_hash", "row_hash")}
    return hashlib.sha256((prev + canonical_json(body)).encode()).hexdigest()


def campaign_selection_holdout_spent(ws: Workspace, campaign_id: str) -> bool:
    df = read_selection_holdout_access(ws)
    return bool((df["campaign_id"] == campaign_id).any())


def selection_holdout_spent(ws: Workspace, experiment_id: str) -> bool:
    """True iff the experiment's CAMPAIGN has spent the shared selection holdout (accounting is campaign-wide)."""
    return campaign_selection_holdout_spent(ws, experiment_row(ws, experiment_id)["campaign_id"])


def append_selection_holdout_access(ws: Workspace, **fields) -> dict:
    """Append the campaign's single unlock record. Refuses a second unlock of the same campaign ('SELECTION HOLDOUT HAS BEEN SPENT')."""
    df = read_selection_holdout_access(ws)
    if (df["campaign_id"] == fields["campaign_id"]).any():
        raise SelectionHoldoutContaminated(f"CAMPAIGN SELECTION HOLDOUT HAS BEEN SPENT for {fields['campaign_id']} (see registry/selection_holdout_access.csv); it cannot be opened again")
    row = {k: str(fields.get(k, "")) for k in SELECTION_HOLDOUT_ACCESS_COLS if k not in ("prev_row_hash", "row_hash")}
    prev = df["row_hash"].iloc[-1] if len(df) else "GENESIS"
    row["prev_row_hash"] = prev
    row["row_hash"] = _row_hash(prev, row)
    _write(ws.path("selection_holdout_access.csv"), pd.concat([df, pd.DataFrame([row])], ignore_index=True), SELECTION_HOLDOUT_ACCESS_COLS)
    return row


def verify_selection_holdout_ledger(ws: Workspace) -> int:
    df = read_selection_holdout_access(ws)
    prev = "GENESIS"
    seen = set()
    for _, r in df.iterrows():
        row = r.to_dict()
        if row["prev_row_hash"] != prev or row["row_hash"] != _row_hash(prev, row):
            raise RegistryIntegrityError("registry/selection_holdout_access.csv was edited, reordered or truncated (hash chain broken)")
        if row["campaign_id"] in seen:
            raise RegistryIntegrityError(f"campaign SELECTION HOLDOUT opened twice for {row['campaign_id']}")
        seen.add(row["campaign_id"])
        prev = row["row_hash"]
    return len(df)


def _final_row_hash(prev: str, row: dict) -> str:
    body = {k: row[k] for k in FINAL_CONFIG_COLS if k not in ("prev_row_hash", "row_hash")}
    return hashlib.sha256((prev + canonical_json(body)).encode()).hexdigest()


def final_config_of(ws: Workspace, experiment_id: str) -> dict | None:
    df = read_final_configs(ws)
    hit = df[(df["experiment_id"] == experiment_id) & (df["event"] == "FINAL_CONFIG_FROZEN")]
    return hit.iloc[0].to_dict() if len(hit) else None


def append_final_config(ws: Workspace, **fields) -> dict:
    """Append-only hash-chained final-configuration ledger. ONE FINAL_CONFIG_FROZEN row per experiment, ever (no switching, no fallback
    to a runner-up); one CPCV_RESULT row per experiment after it."""
    df = read_final_configs(ws)
    exp, ev = fields["experiment_id"], fields["event"]
    mine = df[df["experiment_id"] == exp]
    if ev == "FINAL_CONFIG_FROZEN" and (mine["event"] == "FINAL_CONFIG_FROZEN").any():
        raise EngineError(f"{exp} already froze its final configuration {mine['selected_config_id'].iloc[0]}; it can never be replaced "
                          f"(no fallback to a runner-up after any later evidence)")
    if ev == "CPCV_RESULT" and ((mine["event"] == "CPCV_RESULT").any() or not (mine["event"] == "FINAL_CONFIG_FROZEN").any()):
        raise EngineError(f"{exp}: CPCV_RESULT needs exactly one prior FINAL_CONFIG_FROZEN row and may be recorded once")
    row = {k: str(fields.get(k, "")) for k in FINAL_CONFIG_COLS if k not in ("prev_row_hash", "row_hash")}
    prev = df["row_hash"].iloc[-1] if len(df) else "GENESIS"
    row["prev_row_hash"] = prev
    row["row_hash"] = _final_row_hash(prev, row)
    _write(ws.path("final_configs.csv"), pd.concat([df, pd.DataFrame([row])], ignore_index=True), FINAL_CONFIG_COLS)
    return row


def verify_final_config_ledger(ws: Workspace) -> int:
    df = read_final_configs(ws)
    prev = "GENESIS"
    for _, r in df.iterrows():
        row = r.to_dict()
        if row["prev_row_hash"] != prev or row["row_hash"] != _final_row_hash(prev, row):
            raise RegistryIntegrityError("registry/final_configs.csv was edited, reordered or truncated (hash chain broken)")
        prev = row["row_hash"]
    if (df[df["event"] == "FINAL_CONFIG_FROZEN"]["experiment_id"].duplicated()).any():
        raise RegistryIntegrityError("an experiment froze two final configurations")
    return len(df)


def append_table(ws: Workspace, name: str, cols: list[str], rows: list[dict]) -> None:
    """Append-only helper for selection_holdout_trials.csv / cpcv_results.csv."""
    df = _read(ws.path(name), cols)
    _write(ws.path(name), pd.concat([df, pd.DataFrame([{k: str(v) for k, v in r.items()} for r in rows])],
                                    ignore_index=True), cols)


# ---------------------------------------------------------------------------- integrity / summary
def integrity_check(ws: Workspace, frozen: Frozen | None = None) -> dict:
    """Raises RegistryIntegrityError if the registry violates the frozen opportunity accounting. Catches: missing trial,
    duplicate trial, trial 25, changed trial spec, edited historical result (ledger hash), broken SELECTION HOLDOUT ledger chain."""
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
    n_tr = frozen.trial_policy["expected_trials_per_experiment"]
    per_exp = trials.groupby("experiment_id").size()
    if (per_exp != n_tr).any():
        raise RegistryIntegrityError("an experiment does not have exactly 24 selection trials")
    cap = frozen.trial_policy["max_selection_trials_per_campaign"]
    if (trials.groupby("campaign_id").size() > cap).any():
        raise RegistryIntegrityError(f"campaign exceeds {cap} selection trials")
    revealed = trials[trials["status"] == "REVEALED"]
    if (pd.to_numeric(revealed["raw_p"], errors="coerce").isna()).any():
        raise RegistryIntegrityError("revealed trial without raw_p")
    for exp_id, g in revealed.groupby("experiment_id"):
        sealed = exps.set_index("experiment_id").at[exp_id, "trial_ledger_hash"]
        if len(g) != n_tr or trial_ledger_hash(g) != sealed:
            raise RegistryIntegrityError(f"{exp_id}: historical IS result rows were edited (trial_ledger_hash mismatch)")
    for c, g in revealed.groupby("campaign_id"):
        if len(g) % n_tr:
            raise RegistryIntegrityError(f"campaign {c}: revealed trials are not a multiple of 24")
    if not set(obs["experiment_id"]) <= known:
        raise RegistryIntegrityError("observation references an unknown experiment")
    if (obs["eligible_for_promotion"] != "False").any():
        raise RegistryIntegrityError("observations can never be eligible for promotion")
    n_selection_holdout = verify_selection_holdout_ledger(ws)
    camps = read_campaigns(ws)
    ledger = set(read_selection_holdout_access(ws)["campaign_id"])
    if ledger - set(camps["campaign_id"]):
        raise RegistryIntegrityError(f"selection_holdout_access.csv references unknown campaigns {ledger - set(camps['campaign_id'])}")
    spent = set(camps[camps["status"] == "SELECTION_HOLDOUT_SPENT"]["campaign_id"])
    if spent != ledger:
        raise RegistryIntegrityError(f"campaign status and SELECTION HOLDOUT ledger disagree: SELECTION_HOLDOUT_SPENT campaigns {sorted(spent)} vs ledger {sorted(ledger)}")
    n_final = verify_final_config_ledger(ws)
    return {"experiments": int(len(exps)), "selection_trials": int(len(trials)), "final_config_rows": n_final,
            "revealed_trials": int(len(revealed)), "observations": int(len(obs)), "selection_holdout_unlocks": n_selection_holdout}


def campaign_summary(ws: Workspace, campaign_id: str, frozen: Frozen | None = None) -> dict:
    frozen = frozen or load_frozen()
    camp = campaign_row(ws, campaign_id)
    exps = read_experiments(ws)
    exps = exps[exps["campaign_id"] == campaign_id]
    trials = numeric_trials(read_trials(ws))
    trials = trials[trials["campaign_id"] == campaign_id]
    limit = int(frozen.trial_policy["max_experiments_per_campaign"])
    revealed = int((trials["status"] == "REVEALED").sum())
    return {"campaign_id": campaign_id, "partitions": {k: camp[k] for k in ("development_end", "selection_holdout_end", "lockbox_start")},
            "experiments_used": int(len(exps)), "experiments_max": limit,
            "selection_trials_registered": int(len(trials)),
            "selection_trials_max": int(frozen.trial_policy["max_selection_trials_per_campaign"]),
            "selection_trials_revealed": revealed, "statistical_selection_opportunities_exposed": revealed,
            "shortlist_eligible_trials": int((trials["decision"] == SHORTLIST).sum()),
            "provisional_trials": int((trials["decision"] == PROVISIONAL).sum()),
            "selection_holdout_unlocks": int((read_selection_holdout_access(ws)["campaign_id"] == campaign_id).sum()),
            "campaign_status": camp["status"], "campaign_selection_holdout_spent": campaign_selection_holdout_spent(ws, campaign_id),
            "experiments": exps[["experiment_id", "status", "is_status", "lineage_parent", "research_verification"]].to_dict("records")}
