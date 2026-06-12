# Humanize Integration

This directory contains templates for a Humanize-compatible RLCR loop. Humanize is optional: the scripts here generate the same durable artifacts even when the plugin is unavailable.

Suggested commands in Claude Code:

```bash
/humanize:gen-plan --input docs/draft.md --output docs/plan.md
/humanize:refine-plan --input docs/plan.md
/humanize:start-rlcr-loop docs/plan.md
```

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
