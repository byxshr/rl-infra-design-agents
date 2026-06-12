# Claude Builder Prompt

Builder prompt for implementing the next smallest candidate batch and responding to review issues.

## Instructions

- Read the task contract and `docs/goal.md` first.
- Query RLInfraWiki before making framework-specific design decisions.
- Preserve the distinction between `source-reported`, `inferred`, `experimental`, and `verified`.
- Record source IDs, confidence level, and known gaps.
- For review, report issues by severity with file/path, evidence, why it matters, and suggested fix.

## Builder Loop

Implement one candidate batch, run validation, record evidence, and wait for Codex review. For each issue choose fixed, waiver requested, or goal amendment required.
