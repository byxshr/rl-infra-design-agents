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

## Humanize-ready Workspace Bridge

Use the bridge when a real RL infra task contract should become a Claude Code workspace for Humanize:

```bash
conda run -n rl-infra-design-agents make prepare-humanize-task \
  CONTRACT=examples/task_contracts/training-rollout-mismatch-debug.yaml \
  HUMANIZE_WORKSPACE=/tmp/rlinfra-humanize-task-workspace \
  TARGET_REPO=/path/to/target/repo \
  DIFF_BASE=main
```

The bridge renders the task bundle through the pinned `RLInfraWiki` dependency, validates `context/context_bundle.md`, preserves the JSON/source sidecars, locks `docs/plan.md`, and runs `validate_review_gate.py` without `--require-review`. It then writes `humanize_start.md` and `.humanize/rlinfra_bridge.json` with schema version, main-repo commit, pinned `RLInfraWiki` commit, target repo/diff-base validation status, context paths, plan lock path, prerequisite warnings, and commands run.

This is a preparation step, not an automatic Humanize launch. Enter the prepared workspace in Claude Code and run:

```text
/humanize:start-rlcr-loop docs/plan.md
```

Humanize rounds are still external to this repository's review ledger until IMP-014. Keep RLInfraWiki page/source IDs, non-claims, validation evidence, and risk-register updates intact so those rounds can be imported later without losing provenance.
