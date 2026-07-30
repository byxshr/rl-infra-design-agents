# Humanize Integration

This directory contains templates for a Humanize-compatible RLCR loop. Humanize is optional: the scripts here generate the same durable artifacts even when the plugin is unavailable.

## Claude Code Prerequisites

The repository can prepare Humanize-compatible workspaces without the Humanize plugin, but Claude Code can only run `/humanize:*` slash commands after the plugin is installed. A local `humanize/` source checkout only helps the bridge discover instruction files; it does not automatically register Claude Code commands.

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
  DIFF_BASE=<diff-base> \
  ROUND=1
/tmp/rlinfra-humanize-task-workspace/launch_humanize.sh
```

Then run in Claude Code:

```text
/humanize:start-rlcr-loop docs/superpowers/rlcr/<task-name>-plan.md --track-plan-file --base-branch <diff-base>
```

Keep `.humanize/rlcr/` local-only. Do not commit round summaries, state files, contracts, or goal trackers, and never use `git add -f .humanize`. Do not use `.humanize/plan.md` with `--track-plan-file`; tracked plans should live in a normal path such as `docs/superpowers/rlcr/...`.

The start wrapper rerenders generated context while preserving refined human docs by default, refreshes the plan lock, verifies that the target plan is tracked, clean, and byte-identical to both `docs/plan.md` and the lock hash, rejects tracked `.humanize/` state and dirty target files, and ensures anchored `/.humanize/` coverage through local `.git/info/exclude`. `HUMANIZE_OVERWRITE_DOCS=1` is an explicit scaffold reset and requires resynchronizing the committed target plan. The wrapper does not start Claude Code automatically. On success it writes `launch_humanize.sh`, `humanize_operator.md`, and `.humanize/rlinfra_operator.json`; the launcher repeats preflight, starts Claude Code with the target repository as its session root, and forwards optional CLI arguments. It is an initial clean-tree guard, not a dirty-tree mid-loop relaunch command. A hygiene failure exits with code `3`, retains `.humanize/rlinfra_target_preflight.json`, and does not generate launcher/operator artifacts.

Preserve `context/context_bundle.md`, `context/context_bundle.json`, `context/context_sources.yaml`, RLInfraWiki page/source IDs, non-claims, validation evidence, and risk updates through the Humanize loop. Use `.humanize/rlinfra_bridge.json` to recover bridge schema v2, execution mode, main-repo commit, pinned `RLInfraWiki` commit, target repo/diff-base validation status, and command provenance for round import.

After Humanize writes `.humanize/rlcr/<timestamp>/round-N-summary.md` and `round-N-review-result.md`, import the round:

```bash
make import-humanize-round \
  HUMANIZE_WORKSPACE=/tmp/rlinfra-humanize-task-workspace \
  ROUND=1
```

Bridge schema v2 searches only the configured target repository's `.humanize/rlcr/` automatically and never falls back to the staging workspace. If more than one target loop exists, pass `HUMANIZE_LOOP_DIR=/path/to/target/repo/.humanize/rlcr/<timestamp>`; any deliberate cross-root import must also be explicit. The importer remains compatible with bridge schema v1, validates bridge provenance, warns when copied workspace metadata is stale, writes `review_rounds/round-001/`, updates `review_issues.jsonl`, preserves raw Humanize review output, and lets the existing gate reason about imported P0/P1/P2 findings:

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
