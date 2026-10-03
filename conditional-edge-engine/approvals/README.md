# approvals/ — HUMAN-written decision files ONLY

No script, test fixture in production code, or LLM may create, edit or delete a file here (AGENTS.md rule 1). Get the exact hashes with the
read-only `python scripts/show_approval_hashes.py ...`.

| human decision | file | engine may create it? |
|---|---|---|
| define / confirm the event premise | (freeze) | no |
| run development IS | explicit `run_experiment.py` | no |
| open the SELECTION HOLDOUT | `EXP_xxxx_SELECTION_HOLDOUT_APPROVAL.yaml` per experiment + `CAMPAIGN_<id>_SELECTION_HOLDOUT_OPEN_APPROVAL.yaml` | never |
| choose the ONE final configuration | `EXP_xxxx_FINAL_CONFIG_SELECTION.yaml` | never |
| fixed CPCV | none — runs automatically after `FINAL_CONFIG_FROZEN` | n/a |
| open the final lockbox | (not implemented; `confirm_lockbox.py` is a stub) | never |

The SELECTION HOLDOUT (1 or 2 calendar years immediately after DEVELOPMENT) is **selection data**: it is used to choose among configurations that
were frozen before it was read. It is **not** final confirmation; only the untouched FINAL_LOCKBOX is.

## 1. `EXP_xxxx_SELECTION_HOLDOUT_APPROVAL.yaml` (optional; only for a near-tie cluster)
Template `templates/approval/SELECTION_HOLDOUT_APPROVAL.template.yaml`. Valid only for the EXACT frozen state it references:

| field | must equal |
|---|---|
| `experiment_id`, `campaign_id` | the experiment / its campaign |
| `manifest_sha256` | sha256 of the exact `FROZEN_MANIFEST.json` bytes |
| `is_report_sha256` | sha256 of the exact `results/IS_REPORT.json` |
| `near_tie_cluster_id` | a cluster listed in the IS report section CONFIGURATION UNCERTAINTY / NEAR-TIES |
| `approved` | `true` (`false` records HUMAN_DECLINED) |
| `approved_by` | exactly `HUMAN_USER` |
| `approved_configs` | 1–2 config ids `<experiment>|<TARGET>|<STATE>`, from the top 2 (frozen IS ranking) of that cluster; ≤ 6 over the whole campaign; all 3 models run for each |
| `approval_note` | non-empty |

## 2. `CAMPAIGN_<id>_SELECTION_HOLDOUT_OPEN_APPROVAL.yaml`
Written after `scripts/freeze_campaign_selection_holdout.py` froze ALL approved configs of the campaign together (before any holdout byte is read) and
printed the freeze hash. Keys `campaign_id`, `selection_holdout_freeze_sha256`, `approved_by: HUMAN_USER`, `approved: true`, `approval_note`. The holdout is
opened exactly once per campaign (≤ 6 configs × 3 models = 18 evaluations, one shared interval, no sequential A-then-B).

## 3. `EXP_xxxx_FINAL_CONFIG_SELECTION.yaml`
Template `templates/approval/FINAL_CONFIG_SELECTION.template.yaml`; hashes from `show_approval_hashes.py --experiment EXP_xxxx --final`. Exactly ONE
`selected_config_id` (or `DECLINE`). If the holdout was used it must have been frozen and evaluated there (`selection_holdout_report_sha256` = the report
the human saw; `HOLDOUT_PREFERRED_CONFIG` is advisory only). If the holdout was skipped the config must be IS-eligible and `selection_holdout_report_sha256`
is `null` (`SELECTION_HOLDOUT_SKIPPED`; the unused holdout stays unread). `scripts/finalize_final_config.py` validates, freezes
(`FINAL_CONFIG_FROZEN`, ledger `registry/final_configs.csv`) and then runs CPCV automatically. There is never a fallback to a runner-up after a CPCV failure.
