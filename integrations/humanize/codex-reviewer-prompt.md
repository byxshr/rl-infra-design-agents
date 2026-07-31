# Codex Reviewer Prompt

Use the corresponding root prompt as the canonical wording: `prompts/codex-review-prompt.md`.

Apply contract `humanize-gate-invariants-v1`. Humanize adapters may read `.humanize/` as local evidence, but must never recommend tracking or committing it. Durable exported artifacts belong under `review_rounds/`, `review_issues.jsonl`, `review_waivers.jsonl`, and `evidence/`; `.humanize/rlcr/` remains local loop state. For `TOOL-CONTRACT-CONFLICT`, a final `STOP` requests operator intervention and must not be interpreted as successful completion.
