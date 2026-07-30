# Humanize-Compatible RLCR

Maps this repository onto a Claude Builder plus Codex Reviewer workflow without making Humanize a hard dependency.

## Operating Rules

- Keep workflow artifacts task-agnostic in this repository.
- Keep task-specific implementation, benchmark output, model data, and private logs in external task workspaces.
- Cite RLInfraWiki page IDs and source IDs for framework-specific claims.
- Treat upstream claims as `source-reported` unless local evidence proves otherwise.
- Record validation commands and evidence paths before asking for review.

## RLCR Notes

The default loop is Claude Builder, Codex Reviewer, and Human Architect. The builder may update implementation strategy with evidence, but objective, acceptance criteria, non-goals, and review gate thresholds require explicit amendment.

## Humanize-ready Task Start

For a real code-changing task, first prepare the staging workspace:

```bash
conda run -n rl-infra-design-agents make prepare-humanize-task \
  CONTRACT=examples/task_contracts/training-rollout-mismatch-debug.yaml \
  HUMANIZE_WORKSPACE=/tmp/rlinfra-humanize-task-workspace \
  TARGET_REPO=/path/to/target/repo \
  DIFF_BASE=main
```

Copy `docs/plan.md` to a normal path in the target repository, commit it, then run `make start-humanize-task` with the same inputs plus `TARGET_PLAN=docs/superpowers/rlcr/<task-name>-plan.md`. The start wrapper rerenders the staging workspace and requires the target plan to be tracked, clean, and byte-identical before it writes operator artifacts.

Both Make targets preserve existing human docs by default. `HUMANIZE_OVERWRITE_DOCS=1` is reserved for an intentional scaffold reset.

## Humanize Plugin Prerequisites

The start wrapper prepares files only. It does not install Humanize and does not start Claude Code. A local `humanize/` checkout is useful for instruction discovery, but Claude Code still needs the Humanize plugin installed before `/humanize:*` commands are available.

Install Humanize from Claude Code:

```text
/plugin marketplace add PolyArch/humanize
/plugin install humanize@PolyArch
```

If `/humanize:start-rlcr-loop` fails with an unknown command, install or update the plugin, restart Claude Code, and run it again. The command prefix is `/humanize`, not `/hunmanize`.

This is a preparation and instruction step, not an automatic Humanize launch.

For design-only tasks that do not edit a separate target repository, enter the prepared workspace in Claude Code and run:

```bash
cd /tmp/rlinfra-humanize-task-workspace
```

```text
/humanize:start-rlcr-loop docs/plan.md
```

For real code-changing tasks, use this complete sequence:

```bash
cd /path/to/target/repo
mkdir -p docs/superpowers/rlcr
cp /tmp/rlinfra-humanize-task-workspace/docs/plan.md docs/superpowers/rlcr/<task-name>-plan.md
git add docs/superpowers/rlcr/<task-name>-plan.md
git commit -m "Add RLCR plan for <task-name>"
cd /path/to/rl-infra-design-agents
conda run -n rl-infra-design-agents make start-humanize-task \
  CONTRACT=examples/task_contracts/training-rollout-mismatch-debug.yaml \
  HUMANIZE_WORKSPACE=/tmp/rlinfra-humanize-task-workspace \
  TARGET_REPO=/path/to/target/repo \
  TARGET_PLAN=docs/superpowers/rlcr/<task-name>-plan.md \
  DIFF_BASE=<diff-base> \
  ROUND=1
/tmp/rlinfra-humanize-task-workspace/launch_humanize.sh
```

```text
/humanize:start-rlcr-loop docs/superpowers/rlcr/<task-name>-plan.md --track-plan-file --base-branch <diff-base>
```

`start-humanize-task` preserves refined human docs by default, refreshes the plan lock, and checks the committed target plan against both staged `docs/plan.md` and the lock hash. `HUMANIZE_OVERWRITE_DOCS=1` is an explicit destructive scaffold reset and requires the target plan to be reviewed and recommitted afterward.

`launch_humanize.sh` repeats the hygiene preflight, starts Claude Code from the target repository root, and forwards optional Claude CLI arguments. The preflight rejects dirty target trees, target-plan/lock drift, unresolved local base branches, or tracked `.humanize/` state. It adds only the anchored `/.humanize/` rule to local `.git/info/exclude` when needed and never changes tracked `.gitignore`. The launcher is an initial clean-tree guard; after implementation edits begin, resume the existing Claude session or launch Claude directly from the target root.

Do not use `.humanize/plan.md` with `--track-plan-file`: Humanize treats `.humanize/` as local runtime state and its gate blocks tracked `.humanize/` files. Keep `.humanize/rlcr/` local-only; do not commit round summaries, state files, contracts, or goal trackers, and never use `git add -f .humanize`.

After Humanize produces a round under `.humanize/rlcr/<timestamp>/`, import it back into this repository's RLCR workspace:

```bash
conda run -n rl-infra-design-agents make import-humanize-round \
  HUMANIZE_WORKSPACE=/tmp/rlinfra-humanize-task-workspace \
  ROUND=1
```

Bridge schema v2 automatically searches only the configured target repository. It does not fall back to staging-workspace rounds. If target-loop discovery is ambiguous, pass `HUMANIZE_LOOP_DIR=/path/to/target/repo/.humanize/rlcr/<timestamp>`; any deliberate import from another root must also be explicit.

The importer validates the bridge schema, warns when copied workspace metadata still points at an older path, reads `round-N-summary.md` and `round-N-review-result.md`, writes `review_rounds/round-001/claude_response.md`, `codex_review.md`, `parsed_issues.jsonl`, and `humanize_round_metadata.json`, then updates the workspace-level `review_issues.jsonl` through the existing parser and append scripts. It preserves raw Humanize output while normalizing findings into the parser-compatible `### P1:` style used by the review gate, and records whether source text needed UTF-8 replacement characters.

Run the gate in review-required mode after import:

```bash
conda run -n rl-infra-design-agents python .agents/skills/RLInfraWiki/scripts/validate_review_gate.py \
  --workspace /tmp/rlinfra-humanize-task-workspace \
  --require-review
```

COMPLETE/no-finding rounds can pass the review-required gate; imported open P0/P1/P2 findings still block promotion. Hygiene failures return exit code `3` and retain `.humanize/rlinfra_target_preflight.json` without writing a launcher or operator artifacts. Keep RLInfraWiki page/source IDs, non-claims, validation evidence, and risk-register updates intact throughout the Humanize loop. IMP-016 remains the deferred boundary for a fuller operator loop that might send the slash command automatically.
