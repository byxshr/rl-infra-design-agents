# Humanize Integration

This directory contains templates for a Humanize-compatible RLCR loop. Humanize is optional: the scripts here generate the same durable artifacts even when the plugin is unavailable.

Suggested commands in Claude Code:

```bash
/humanize:gen-plan --input docs/draft.md --output docs/plan.md
/humanize:refine-plan --input docs/plan.md
/humanize:start-rlcr-loop docs/plan.md
```

Preferred bridge from this repository:

```bash
make prepare-humanize-task \
  CONTRACT=examples/task_contracts/training-rollout-mismatch-debug.yaml \
  HUMANIZE_WORKSPACE=/tmp/rlinfra-humanize-task-workspace \
  TARGET_REPO=/path/to/target/repo \
  DIFF_BASE=main
```

Then open Claude Code in `/tmp/rlinfra-humanize-task-workspace` and run:

```text
/humanize:start-rlcr-loop docs/plan.md
```

The bridge prepares the workspace only; it does not start Claude Code or import Humanize review rounds. Round import/export remains the IMP-014 boundary. Preserve `context/context_bundle.md`, `context/context_bundle.json`, `context/context_sources.yaml`, RLInfraWiki page/source IDs, non-claims, validation evidence, and risk updates through the Humanize loop. Use `.humanize/rlinfra_bridge.json` to recover the bridge schema version, main-repo commit, pinned `RLInfraWiki` commit, target repo/diff-base validation status, and command provenance for later import.

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
