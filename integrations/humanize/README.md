# Humanize Integration

This directory contains templates for a Humanize-compatible RLCR loop. Humanize is optional: the scripts here generate the same durable artifacts even when the plugin is unavailable.

Suggested commands in Claude Code:

```bash
/humanize:gen-plan --input docs/draft.md --output docs/plan.md
/humanize:refine-plan --input docs/plan.md
/humanize:start-rlcr-loop docs/plan.md
```

Preferred start wrapper from this repository:

```bash
make start-humanize-task \
  CONTRACT=examples/task_contracts/training-rollout-mismatch-debug.yaml \
  HUMANIZE_WORKSPACE=/tmp/rlinfra-humanize-task-workspace \
  TARGET_REPO=/path/to/target/repo \
  DIFF_BASE=main \
  ROUND=1
```

Then open Claude Code in `/tmp/rlinfra-humanize-task-workspace` and run:

```text
/humanize:start-rlcr-loop docs/plan.md
```

The wrapper prepares the workspace only; it does not start Claude Code. It writes `humanize_operator.md` and `.humanize/rlinfra_operator.json` with the exact start/import/gate commands. Preserve `context/context_bundle.md`, `context/context_bundle.json`, `context/context_sources.yaml`, RLInfraWiki page/source IDs, non-claims, validation evidence, and risk updates through the Humanize loop. Use `.humanize/rlinfra_bridge.json` to recover the bridge schema version, main-repo commit, pinned `RLInfraWiki` commit, target repo/diff-base validation status, and command provenance for round import.

After Humanize writes `.humanize/rlcr/<timestamp>/round-N-summary.md` and `round-N-review-result.md`, import the round:

```bash
make import-humanize-round \
  HUMANIZE_WORKSPACE=/tmp/rlinfra-humanize-task-workspace \
  ROUND=1
```

If more than one Humanize loop directory exists and auto-discovery is ambiguous, pass `HUMANIZE_LOOP_DIR=/tmp/rlinfra-humanize-task-workspace/.humanize/rlcr/<timestamp>`. The importer validates the bridge schema, warns when copied workspace metadata is stale, writes `review_rounds/round-001/`, updates `review_issues.jsonl`, preserves raw Humanize review output, and lets the existing gate reason about imported P0/P1/P2 findings:

```bash
python .agents/skills/RLInfraWiki/scripts/validate_review_gate.py \
  --workspace /tmp/rlinfra-humanize-task-workspace \
  --require-review
```

IMP-016 remains the boundary for deciding whether to wrap more of the interactive Humanize execution.

Repository-compatible commands:

```bash
python .agents/skills/RLInfraWiki/scripts/render_task_bundle.py \
  --contract examples/task_contracts/slime-weight-sync.yaml \
  --output /tmp/task
python .agents/skills/RLInfraWiki/scripts/lock_plan.py --workspace /tmp/task
python .agents/skills/RLInfraWiki/scripts/render_rlcr_context.py --workspace /tmp/task --round 1
python .agents/skills/RLInfraWiki/scripts/validate_review_gate.py --workspace /tmp/task
```

Use `--force` only for intentional scaffold regeneration into an existing workspace. Ledgers and goal/plan docs are preserved by default; add `--reset-ledgers` only when intentionally starting the RLCR ledger over.
