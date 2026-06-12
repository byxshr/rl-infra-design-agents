# Review Gates

Defines P0 through P3 severity, blocking behavior, waiver policy, and promotion readiness.

## Operating Rules

- Keep workflow artifacts task-agnostic in this repository.
- Keep task-specific implementation, benchmark output, model data, and private logs in external task workspaces.
- Cite RLInfraWiki page IDs and source IDs for framework-specific claims.
- Treat upstream claims as `source-reported` unless local evidence proves otherwise.
- Record validation commands and evidence paths before asking for review.

## Severity Policy

- P0/P1 issues block promotion until `resolved`, `fixed`, or `closed`; `waived` and `backlog` do not bypass these severities.
- P2 issues block promotion unless fixed or paired with an approved row in `review_waivers.jsonl`.
- P3 issues may remain open as warnings, and may be deferred with `waived` or `backlog`.
- Unknown severities or statuses fail closed.

## RLCR Notes

The default loop is Claude Builder, Codex Reviewer, and Human Architect. The builder may update implementation strategy with evidence, but objective, acceptance criteria, non-goals, and review gate thresholds require explicit amendment.
