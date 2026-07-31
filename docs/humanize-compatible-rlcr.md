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

The start wrapper prepares files only. It does not install Humanize or start Claude Code. An explicit `HUMANIZE_PLUGIN_ROOT` is validated and registered by the generated launcher through `--plugin-dir`; without one, Claude Code needs a compatible marketplace plugin installed before `/humanize:*` commands are available.

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
  HUMANIZE_PLUGIN_ROOT=../humanize \
  DIFF_BASE=<diff-base> \
  ROUND=1
/tmp/rlinfra-humanize-task-workspace/launch_humanize.sh
```

```text
/humanize:start-rlcr-loop docs/superpowers/rlcr/<task-name>-plan.md --track-plan-file --base-branch <diff-base>
```

`start-humanize-task` preserves refined human docs, checks the committed target plan, and validates the selected Humanize runtime against `humanize-gate-invariants-v1`. Use `HUMANIZE_PLUGIN_ROOT=../humanize` for the local development runtime; otherwise the wrapper validates enabled `humanize@PolyArch` from `claude plugin list --json`. Target mode fails closed with exit `2` when the runtime is incompatible. It records a SHA256 contract fingerprint and `static_contract_probe` validation kind in addition to the plugin version, and does not destroy a previously validated operator bundle when a later runtime probe fails. Static compatibility does not prove that the hook executes successfully.

`launch_humanize.sh` repeats the hygiene preflight, starts Claude Code from the target repository root, and forwards optional Claude CLI arguments. The preflight rejects dirty target trees, target-plan/lock drift, unresolved local base branches, or tracked `.humanize/` state. It adds only the anchored `/.humanize/` rule to local `.git/info/exclude` when needed and never changes tracked `.gitignore`. The launcher is an initial clean-tree guard; after implementation edits begin, resume the existing Claude session or launch Claude directly from the target root.

Do not use `.humanize/plan.md` with `--track-plan-file`: Humanize treats `.humanize/` as local runtime state and its gate blocks tracked `.humanize/` files. Keep `.humanize/rlcr/` local-only; do not commit round summaries, state files, contracts, or goal trackers, and never use `git add -f .humanize`.

After Humanize produces a round under `.humanize/rlcr/<timestamp>/`, import it back into this repository's RLCR workspace:

```bash
conda run -n rl-infra-design-agents make import-humanize-round \
  HUMANIZE_WORKSPACE=/tmp/rlinfra-humanize-task-workspace \
  ROUND=1
```

Bridge schema v2 automatically searches only the configured target repository. It does not fall back to staging-workspace rounds. If target-loop discovery is ambiguous, pass `HUMANIZE_LOOP_DIR=/path/to/target/repo/.humanize/rlcr/<timestamp>`; any deliberate import from another root must also be explicit.

The importer validates the bridge and review contract before writing. Operator schema v3 requires exactly one `Humanize Gate Verdict`; legacy v1/v2 rounds without one warn, but explicit instructions to track or commit `.humanize/` are always rejected. Valid rounds preserve raw output, normalize findings, record review-contract provenance, and then update `review_issues.jsonl`.

Run the gate in review-required mode after import:

```bash
conda run -n rl-infra-design-agents python .agents/skills/RLInfraWiki/scripts/validate_review_gate.py \
  --workspace /tmp/rlinfra-humanize-task-workspace \
  --require-review
```

COMPLETE/no-finding rounds can pass the review-required gate; imported open P0/P1/P2 findings still block promotion. Hygiene failures return exit code `3` and retain `.humanize/rlinfra_target_preflight.json` without writing a launcher or operator artifacts. Keep RLInfraWiki page/source IDs, non-claims, validation evidence, and risk-register updates intact throughout the Humanize loop. IMP-016 remains the deferred boundary for a fuller operator loop that might send the slash command automatically.
