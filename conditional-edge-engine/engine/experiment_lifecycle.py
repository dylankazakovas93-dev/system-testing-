"""Experiment lifecycle: create -> (edit 4 files) -> freeze -> run. Mutation after freeze is detected.

freeze: validates the spec, hashes event.py + EVENT_SPEC.yaml + every frozen v1 file (+ engine code),
pre-registers the complete 24-trial set in selection_trials.csv BEFORE any result exists, writes
FROZEN_MANIFEST.json and makes the four editable files read-only.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
from pathlib import Path

from engine import trial_registry as reg
from engine.common import (CODE_ROOT, EngineError, Frozen, canonical_json, engine_code_hash, frozen_files,
                           load_frozen, now_utc_iso, sha256_file)
from engine.event_contract import EventSpecError, load_spec, static_scan_event_source, validate_spec
from engine.partitions import parse_partitions

EDITABLE = ["HYPOTHESIS.md", "EVENT_SPEC.yaml", "event.py", "reference.pine"]
MANIFEST = "FROZEN_MANIFEST.json"


class MutationDetected(EngineError):
    pass


def experiment_dir(ws: reg.Workspace, experiment_id: str) -> Path:
    return ws.experiments / experiment_id


def create_experiment(ws: reg.Workspace, campaign_id: str | None = None, *, new_campaign: str | None = None,
                      partitions: dict | None = None, lineage_parent: str = "") -> str:
    """Register a new experiment (consumes one slot of the campaign) and copy the template.

    A NEW campaign needs explicit ``partitions`` = {development_end, oos_end, lockbox_start}; nothing infers or moves them.
    """
    frozen = load_frozen()
    if new_campaign:
        if not partitions:
            raise EngineError("a new campaign needs explicit partitions: --development-end, --oos-end, --lockbox-start "
                              "(DEVELOPMENT / CONFIRMATION OOS / FINAL LOCKBOX)")
        reg.create_campaign(ws, new_campaign, partitions, frozen)
        campaign_id = new_campaign
    if not campaign_id:
        raise EngineError("specify --campaign <id> or --new-campaign <id> with --development-end --oos-end --lockbox-start")
    exp_id = reg.register_experiment(ws, campaign_id, lineage_parent, frozen)   # raises on experiment 21
    dest = experiment_dir(ws, exp_id)
    shutil.copytree(CODE_ROOT / "templates" / "experiment", dest)
    spec_path = dest / "EVENT_SPEC.yaml"
    parts = reg.campaign_partitions(ws, campaign_id)
    text = (spec_path.read_text().replace("EXP_XXXX", exp_id).replace("C_XXXX", campaign_id)
            .replace("DEV_END_XXXX", parts["development_end"]).replace("OOS_END_XXXX", parts["oos_end"])
            .replace("LOCKBOX_XXXX", parts["lockbox_start"]))
    spec_path.write_text(text)
    hyp = dest / "HYPOTHESIS.md"
    hyp.write_text(hyp.read_text().replace("EXP_XXXX", exp_id))
    if lineage_parent:
        (dest / "LINEAGE.md").write_text(
            f"# Lineage\n\nThis experiment is a NEW lineage of {lineage_parent}. The parent's event/spec changed "
            f"after its results were revealed, so the parent stays as-is and this experiment consumes a new "
            f"campaign slot and a fresh set of 24 selection trials.\n")
    return exp_id


def validate_experiment(ws: reg.Workspace, experiment_id: str, frozen: Frozen | None = None) -> list[str]:
    frozen = frozen or load_frozen()
    d = experiment_dir(ws, experiment_id)
    errs: list[str] = []
    for f in EDITABLE:
        if not (d / f).exists():
            errs.append(f"missing {f}")
    if errs:
        return errs
    exp = reg.experiment_row(ws, experiment_id)
    try:
        spec = load_spec(d / "EVENT_SPEC.yaml")
    except Exception as e:  # noqa: BLE001
        return [f"EVENT_SPEC.yaml unreadable: {e}"]
    errs += validate_spec(spec, frozen, experiment_id=experiment_id, campaign_id=exp["campaign_id"],
                          campaign_partitions=reg.campaign_partitions(ws, exp["campaign_id"]))
    errs += [f"event.py: {m}" for m in static_scan_event_source((d / "event.py").read_text())]
    return errs


def _hash_bundle(ws: reg.Workspace, experiment_id: str) -> dict:
    d = experiment_dir(ws, experiment_id)
    frozen_hashes = {str(p.relative_to(CODE_ROOT)): sha256_file(p) for p in frozen_files()}
    return {
        "event_py": sha256_file(d / "event.py"),
        "event_spec": sha256_file(d / "EVENT_SPEC.yaml"),
        "frozen_files": frozen_hashes,
        "frozen_bundle_hash": hashlib.sha256(canonical_json(frozen_hashes).encode()).hexdigest(),
        "engine_code_hash": engine_code_hash(),
    }


def freeze(ws: reg.Workspace, experiment_id: str) -> dict:
    frozen = load_frozen()
    exp = reg.experiment_row(ws, experiment_id)
    if exp["status"] != "DRAFT":
        raise EngineError(f"{experiment_id} is {exp['status']}: it cannot be frozen again. Changing event.py or the "
                          f"spec after freezing requires a NEW experiment (scripts/new_experiment.py --lineage-of)")
    errs = validate_experiment(ws, experiment_id, frozen)
    if errs:
        raise EventSpecError("experiment cannot be frozen:\n  - " + "\n  - ".join(errs))
    d = experiment_dir(ws, experiment_id)
    bundle = _hash_bundle(ws, experiment_id)
    event_hash = hashlib.sha256((bundle["event_py"] + ":" + bundle["event_spec"]).encode()).hexdigest()
    spec = load_spec(d / "EVENT_SPEC.yaml")
    parts = parse_partitions(spec["partitions"])
    manifest = {
        "experiment_id": experiment_id, "campaign_id": exp["campaign_id"], "frozen_at": now_utc_iso(),
        "engine_version": (CODE_ROOT / "ENGINE_VERSION").read_text().strip(),
        "partitions": parts.as_dict(), "partitions_hash": parts.hash(),
        "hashes": bundle, "event_hash": event_hash, "frozen_spec_hashes": frozen.hashes(),
        "informational_hashes": {f: sha256_file(d / f) for f in ("HYPOTHESIS.md", "reference.pine")},
        "selection_trials": [{"trial_id": reg.trial_id(experiment_id, i), **s} for i, s in enumerate(reg.trial_specs(frozen))],
    }
    manifest["manifest_hash"] = hashlib.sha256(canonical_json(manifest).encode()).hexdigest()
    text = json.dumps(manifest, indent=2, sort_keys=True)
    # registry first: if pre-registration fails nothing is locked
    reg.preregister_trials(ws, experiment_id, event_hash=event_hash, manifest_hash=manifest["manifest_hash"],
                           manifest_sha256=hashlib.sha256(text.encode()).hexdigest(), hashes=frozen.hashes(), frozen=frozen)
    (d / MANIFEST).write_text(text)
    lock(d)
    return manifest


def lock(d: Path) -> None:
    for f in EDITABLE + [MANIFEST]:
        p = d / f
        if p.exists():
            os.chmod(p, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)


def verify_manifest(ws: reg.Workspace, experiment_id: str, *, raise_on_error: bool = True) -> dict:
    """Return {'errors': [...], 'warnings': [...]}; raises MutationDetected on errors by default."""
    d = experiment_dir(ws, experiment_id)
    errors, warnings = [], []
    mp = d / MANIFEST
    if not mp.exists():
        errors.append("FROZEN_MANIFEST.json missing: experiment is not frozen")
    else:
        manifest = json.loads(mp.read_text())
        body = {k: v for k, v in manifest.items() if k != "manifest_hash"}
        if hashlib.sha256(canonical_json(body).encode()).hexdigest() != manifest.get("manifest_hash"):
            errors.append("FROZEN_MANIFEST.json was edited (its own hash does not match)")
        exp = reg.experiment_row(ws, experiment_id)
        if exp["manifest_hash"] != manifest.get("manifest_hash"):
            errors.append("manifest hash differs from the registry (experiments.csv)")
        if exp["manifest_sha256"] and sha256_file(mp) != exp["manifest_sha256"]:
            errors.append("FROZEN_MANIFEST.json file bytes differ from the registry (manifest_sha256)")
        if parse_partitions(load_spec(d / "EVENT_SPEC.yaml")["partitions"]).hash() != manifest.get("partitions_hash"):
            errors.append("partitions changed after freeze")
        cur = _hash_bundle(ws, experiment_id)
        for key, label in (("event_py", "event.py"), ("event_spec", "EVENT_SPEC.yaml")):
            if cur[key] != manifest["hashes"][key]:
                errors.append(f"{label} changed after freeze")
        for rel, h in manifest["hashes"]["frozen_files"].items():
            p = CODE_ROOT / rel
            if not p.exists() or sha256_file(p) != h:
                errors.append(f"frozen specification changed after freeze: {rel}")
        if set(cur["frozen_files"]) != set(manifest["hashes"]["frozen_files"]):
            errors.append("the set of frozen v1 files changed after freeze")
        if cur["engine_code_hash"] != manifest["hashes"]["engine_code_hash"]:
            errors.append("engine/ or features/ code (or ENGINE_VERSION) changed after freeze")
        for f, h in manifest["informational_hashes"].items():
            if sha256_file(d / f) != h:
                warnings.append(f"{f} changed after freeze (narrative/reference only; does not alter results)")
        trials = reg.experiment_trials(ws, experiment_id)
        if len(trials) != 24 or set(trials["event_hash"]) != {manifest["event_hash"]}:
            errors.append("registry trials do not match the manifest event_hash / are not exactly 24")
    if errors and raise_on_error:
        raise MutationDetected("experiment mutated after freeze (this is a NEW experiment/lineage, never an edit):\n  - "
                               + "\n  - ".join(errors))
    return {"errors": errors, "warnings": warnings}
