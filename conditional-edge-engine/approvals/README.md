# approvals/ — human OOS approvals ONLY

`EXP_xxxx_OOS_APPROVAL.yaml` is written **by the human user**. No script, test fixture in production code, or LLM may create it
(AGENTS.md rule 1). Template: `templates/approval/OOS_APPROVAL.template.yaml`. Get the exact hashes with
`python scripts/show_approval_hashes.py --experiment EXP_xxxx` (read-only).

The approval is valid only for the EXACT frozen state it references:

| field | must equal |
|---|---|
| `experiment_id`, `campaign_id` | the experiment / its campaign |
| `experiment_manifest_sha256` | sha256 of the exact `FROZEN_MANIFEST.json` bytes (covers event.py, EVENT_SPEC.yaml incl. partitions, every frozen spec, engine code) |
| `is_report_sha256` | sha256 of the exact `results/IS_REPORT.json` (which embeds the IS_REPORT.md and results.json hashes) |
| `approved_by` | exactly `HUMAN_USER` |
| `approved` | `true` (`false` records OOS_NOT_APPROVED) |
| `approved_target_side_groups` | 1–2 ids `TARGET|STATE` taken from the report's TOP 5 IS GROUPS; all 3 models run for each |
| `approval_note` | non-empty |

Changing event.py, EVENT_SPEC.yaml, frozen specs, partitions, the IS results or regenerating the IS report invalidates the
approval. The groups must still be IS-shortlist-eligible under the campaign universe at unlock time, all three model paths must be
externally verified (strong mode), and the campaign must not already appear in `registry/oos_access.csv` (the shared OOS is opened once per campaign).

## Campaign-level opening

`approvals/CAMPAIGN_<id>_OOS_OPEN_APPROVAL.yaml` (template `templates/approval/CAMPAIGN_OOS_OPEN_APPROVAL.template.yaml`) is a second human file.
It is written after `scripts/freeze_campaign_oos.py` has closed the campaign and printed the freeze hash (also `show_approval_hashes.py --campaign <id>`):
keys `campaign_id`, `oos_freeze_sha256`, `approved_by: HUMAN_USER`, `approved: true`, `approval_note`. All per-experiment approvals are re-checked
against the freeze at opening; changing any of them, or any experiment, after the freeze refuses the opening. The opening happens exactly once per
campaign; afterwards no experiment can claim the shared OOS partition as untouched confirmation.
