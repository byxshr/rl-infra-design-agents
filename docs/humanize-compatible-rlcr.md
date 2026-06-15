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

After Humanize produces a round under `.humanize/rlcr/<timestamp>/`, import it back into this repository's RLCR workspace:

```bash
conda run -n rl-infra-design-agents make import-humanize-round \
  HUMANIZE_WORKSPACE=/tmp/rlinfra-humanize-task-workspace \
  ROUND=1
```

The importer validates the bridge schema, warns when copied workspace metadata still points at an older path, reads `round-N-summary.md` and `round-N-review-result.md`, writes `review_rounds/round-001/claude_response.md`, `codex_review.md`, `parsed_issues.jsonl`, and `humanize_round_metadata.json`, then updates the workspace-level `review_issues.jsonl` through the existing parser and append scripts. It preserves raw Humanize output while normalizing findings into the parser-compatible `### P1:` style used by the review gate, and records whether source text needed UTF-8 replacement characters.

Run the gate in review-required mode after import:

```bash
conda run -n rl-infra-design-agents python .agents/skills/RLInfraWiki/scripts/validate_review_gate.py \
  --workspace /tmp/rlinfra-humanize-task-workspace \
  --require-review
```

COMPLETE/no-finding rounds can pass the review-required gate; imported open P0/P1/P2 findings still block promotion. Keep RLInfraWiki page/source IDs, non-claims, validation evidence, and risk-register updates intact throughout the Humanize loop. IMP-015 remains the boundary for a stricter one-command start wrapper.
