# AGENTS.md

## Project identity

This repository is a task-agnostic workflow and knowledge-base repository for RL infrastructure design agents.

The default implementation workflow is Humanize-compatible RLCR: Claude implements, Codex independently reviews, and the human remains the architect.

## Canonical Codex skill

Use `.agents/skills/RLInfraWiki/` as the canonical Codex skill location.

## Repository rules

- Do not implement an RL framework in this repository.
- Do not clone large upstream repositories into this repository.
- Do not add model weights, datasets, private benchmark logs, generated training outputs, or task-specific implementations.
- Do not make performance claims without source, hardware/context, confidence, and reproducibility fields.
- Do not mark upstream README claims as `verified`; use `source-reported` unless locally reproduced.
- Do not manually edit generated query indices. Run `generate_indices.py` instead.

## Review guidelines

When acting as Codex Reviewer, review the diff against:

1. `docs/goal.md` and `goal_versions.jsonl`.
2. `docs/plan.md` and `.humanize/plan.lock.md`.
3. `docs/validation_matrix.md`.
4. `review_issues.jsonl` and unresolved prior issues.
5. RLInfraWiki source and claim provenance.

Flag as P0/P1:

- Silent change to objective, acceptance criteria, non-goals, or review gate.
- Missing validation for a promoted candidate.
- Claim marked `verified` without local reproduction evidence.
- Broken source IDs, missing provenance, or generated index drift.
- Private data, model weights, benchmark logs, or task-specific artifacts added to the workflow repo.
- Implementation that bypasses rollback, observability, or failure handling required by the goal.

Flag as P2:

- Weak tests or incomplete validation matrix.
- Ambiguous interface boundary.
- Missing risk entry for a meaningful failure mode.
- Poor maintainability or unclear task decomposition.

Flag as P3:

- Style, wording, naming, or documentation polish.

In review mode, do not modify files. Report findings with severity, file/path, evidence, and suggested fix.

## Commands before finishing

```bash
python .agents/skills/RLInfraWiki/scripts/validate.py
python .agents/skills/RLInfraWiki/scripts/generate_indices.py --check
python .agents/skills/RLInfraWiki/scripts/repo_status.py
python .agents/skills/RLInfraWiki/scripts/validate_review_gate.py --workspace <task-workspace>
pytest -q
```

## Done means

- All touched wiki pages pass schema validation.
- Every claim cites existing source IDs.
- Version-sensitive claims resolve through `data/version_claims.yaml`.
- Query indices are regenerated or verified.
- Goal contract is active, completed, blocked, or explicitly amended.
- Review gate passes or unresolved issues are documented with waivers.
- Tests pass.
