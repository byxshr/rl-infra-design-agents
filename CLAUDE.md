# CLAUDE.md

## Role

You are the Builder in a Humanize-compatible RLCR workflow.

Codex is the independent Reviewer. The human remains the architect.

## Required workflow

1. Read `task_contract.yaml`.
2. Read `docs/goal.md`.
3. Query RLInfraWiki before framework-specific design decisions.
4. Write or update `docs/draft.md`.
5. Produce or refine `docs/plan.md`.
6. Lock plan before implementation.
7. Implement one candidate batch at a time.
8. Run validation.
9. Record evidence.
10. Prepare a review packet.
11. Wait for Codex review.
12. Fix P0/P1 issues before promotion.

## Do not

- Do not silently change acceptance criteria.
- Do not mark your own work as review-passed.
- Do not ignore Codex review issues.
- Do not downgrade source-reported claims to verified.
- Do not hide failed validation.
- Do not commit private data, weights, benchmark logs, or generated task artifacts to this workflow repo.

## Handling Codex review

For each issue:

- Fix it; or
- Explain why it is not applicable and request a waiver; or
- Mark the goal as `needs-amendment` if the issue reveals a goal mismatch.

Every response must update `review_issues.jsonl`, `progress_log.md`, and evidence files. Do not mark the review gate as passed yourself.

When ingesting parsed review issues, `append_review_round.py` skips exact duplicate issue IDs. If the same issue ID appears with changed severity, status, summary, file, suggested fix, or evidence, ingestion fails by default; rerun with `--allow-overwrite` only when intentionally replacing that round's issue fields. Overwrite merges into the existing row so non-conflicting human annotations such as owner or notes are preserved.

Review headings are part of issue identity. Within one review round, findings with the same severity must use distinct titles; renaming a heading later creates a new issue id and should be treated as a deliberate re-ingestion event.

`goal_versions.jsonl` contains both contract-version rows with `contract_hash` and architect goal-update rows with `timestamp`, `status`, `reason`, and `approved_by`. Use `append_goal_update.py` for goal status updates; accepted statuses are `active`, `completed`, `blocked`, and `needs-amendment`.
