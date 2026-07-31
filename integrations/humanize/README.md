# Humanize Integration

This directory contains templates for a Humanize-compatible RLCR loop. Humanize is optional: the scripts here generate the same durable artifacts even when the plugin is unavailable.

## Claude Code Prerequisites

The repository can prepare Humanize-compatible workspaces without the Humanize plugin, but Claude Code can only run `/humanize:*` commands after registration. `HUMANIZE_PLUGIN_ROOT=/path/to/humanize` makes the generated launcher register local source with `--plugin-dir`; otherwise install the marketplace plugin.

Install Humanize once inside Claude Code:

```text
/plugin marketplace add PolyArch/humanize
/plugin install humanize@PolyArch
```

If `/humanize:start-rlcr-loop` is reported as an unknown command, install or update the plugin, restart Claude Code, and retry. The correct command prefix is `/humanize`; `/hunmanize` is a typo.

Suggested commands in Claude Code:

```bash
/humanize:gen-plan --input docs/draft.md --output docs/plan.md
/humanize:refine-plan --input docs/plan.md
/humanize:start-rlcr-loop docs/plan.md
```

For a real code-changing task, first prepare the staging workspace:

```bash
make prepare-humanize-task \
  CONTRACT=examples/task_contracts/training-rollout-mismatch-debug.yaml \
  HUMANIZE_WORKSPACE=/tmp/rlinfra-humanize-task-workspace \
  TARGET_REPO=/path/to/target/repo \
  DIFF_BASE=main
```

Both `prepare-humanize-task` and `start-humanize-task` preserve existing human docs by default. Use `HUMANIZE_OVERWRITE_DOCS=1` only when intentionally resetting the scaffold.

For design-only tasks that do not edit a separate target repository, open Claude Code in `/tmp/rlinfra-humanize-task-workspace` and run:

```text
/humanize:start-rlcr-loop docs/plan.md
```

For real code-changing tasks, open Claude Code from the target repository instead. Humanize Stop hooks use the Claude Code session root, so starting Claude in `/tmp/rlinfra-humanize-task-workspace` and later switching to the target repo inside Bash can make review gating look at the wrong project.

Recommended target-repo sequence:

```bash
cd /path/to/target/repo
mkdir -p docs/superpowers/rlcr
cp /tmp/rlinfra-humanize-task-workspace/docs/plan.md docs/superpowers/rlcr/<task-name>-plan.md
git add docs/superpowers/rlcr/<task-name>-plan.md
git commit -m "Add RLCR plan for <task-name>"
cd /path/to/rl-infra-design-agents
make start-humanize-task \
  CONTRACT=examples/task_contracts/training-rollout-mismatch-debug.yaml \
  HUMANIZE_WORKSPACE=/tmp/rlinfra-humanize-task-workspace \
  TARGET_REPO=/path/to/target/repo \
  TARGET_PLAN=docs/superpowers/rlcr/<task-name>-plan.md \
  HUMANIZE_PLUGIN_ROOT=../humanize \
  DIFF_BASE=<diff-base> \
  ROUND=1
/tmp/rlinfra-humanize-task-workspace/launch_humanize.sh
```

Then run in Claude Code:

```text
/humanize:start-rlcr-loop docs/superpowers/rlcr/<task-name>-plan.md --track-plan-file --base-branch <diff-base>
```

Keep `.humanize/rlcr/` local-only. Do not commit round summaries, state files, contracts, or goal trackers, and never use `git add -f .humanize`. Do not use `.humanize/plan.md` with `--track-plan-file`; tracked plans should live in a normal path such as `docs/superpowers/rlcr/...`.

The start wrapper rerenders generated context while preserving refined human docs by default, refreshes the plan lock, verifies target hygiene, and validates the selected Humanize runtime against `humanize-gate-invariants-v1`. `HUMANIZE_PLUGIN_ROOT=../humanize` uses local development source and makes the launcher pass `--plugin-dir`; otherwise the wrapper validates enabled `humanize@PolyArch` from `claude plugin list --json`. Runtime identity includes a SHA256 fingerprint of the gate-aware contract files because a development checkout and an older installed plugin may report the same version. This check is recorded as `static_contract_probe`; it does not execute the Stop hook. Target runtime incompatibility exits `2` without publishing a replacement launcher/operator bundle; a prior validated bundle is preserved. Hygiene failure exits `3` and clears invalidated generated artifacts.

Preserve `context/context_bundle.md`, `context/context_bundle.json`, `context/context_sources.yaml`, RLInfraWiki page/source IDs, non-claims, validation evidence, and risk updates through the Humanize loop. Use `.humanize/rlinfra_bridge.json` to recover bridge schema v2, execution mode, main-repo commit, pinned `RLInfraWiki` commit, target repo/diff-base validation status, and command provenance for round import.

After Humanize writes `.humanize/rlcr/<timestamp>/round-N-summary.md` and `round-N-review-result.md`, import the round:

```bash
make import-humanize-round \
  HUMANIZE_WORKSPACE=/tmp/rlinfra-humanize-task-workspace \
  ROUND=1
```

Bridge schema v2 searches only the configured target repository's `.humanize/rlcr/` automatically and never falls back to the staging workspace. Operator schema v3 requires a valid gate verdict before import; legacy v1/v2 reviews without one warn, while any review that tells Claude to track or commit `.humanize/` is rejected before partial writes. Valid imports preserve raw output and let the existing gate reason about P0/P1/P2 findings:

```bash
python .agents/skills/RLInfraWiki/scripts/validate_review_gate.py \
  --workspace /tmp/rlinfra-humanize-task-workspace \
  --require-review
```

IMP-016 remains the boundary for deciding whether to automate more of the interactive Humanize execution. The generated launcher deliberately does not send the slash command.

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
