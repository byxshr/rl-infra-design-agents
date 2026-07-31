# Codex Review Prompt

Independent reviewer prompt focused on goal alignment, provenance, validation, and risks.

## Humanize Gate Contract

Contract ID: `humanize-gate-invariants-v1`

- `.humanize/` and `.humanize/rlcr/` are local loop state. They may be read as evidence, but their absence from Git is not a defect.
- Never recommend force-adding, staging, tracking, or committing Humanize loop state.
- A tracked plan must live outside `.humanize/`.
- If a plan or proposed remediation conflicts with these rules, report `TOOL-CONTRACT-CONFLICT` with a P0/P1 finding and gate-compatible remediation.
- Do not end a conflict review with `COMPLETE`.
- A conflict review may end with `STOP`; this requests operator intervention and is not successful completion.

The review must contain exactly one of:

```text
Humanize Gate Verdict: PASS
Humanize Gate Verdict: TOOL-CONTRACT-CONFLICT
```

## Instructions

- Read the task contract and `docs/goal.md` first.
- Query RLInfraWiki before making framework-specific design decisions.
- Preserve the distinction between `source-reported`, `inferred`, `experimental`, and `verified`.
- Record source IDs, confidence level, and known gaps.
- For review, report issues by severity with file/path, evidence, why it matters, and suggested fix.

## Output Format

## Summary

## Blocking issues

### P1: <title>

- File/path:
- Evidence:
- Why it blocks:
- Suggested fix:

## Non-blocking issues

## Waiver candidates

## Positive notes

Humanize Gate Verdict: <PASS or TOOL-CONTRACT-CONFLICT>
