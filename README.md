# RL-infra-design-agents

`RL-infra-design-agents` is a lightweight workflow and knowledge-base repository for RL, RLHF, RLVR, and agentic-RL infrastructure design tasks. It is not an RL framework and does not wrap slime, verl, AReaL, ROLL, vLLM, SGLang, or Megatron-LM.

The default workflow is Humanize-compatible RLCR:

1. Human Architect defines the task contract and acceptance criteria.
2. Claude Builder drafts the plan and implements one candidate batch at a time.
3. Codex Reviewer independently checks goal alignment, provenance, validation, risks, and diff quality.
4. Review issues are normalized into JSONL and resolved, waived, or escalated as goal amendments.

## Repository Layout

- `.agents/skills/RLInfraWiki/`: canonical Codex skill, wiki, scripts, data, and tests.
- `docs/`: workflow documentation for goal contracts, RLCR, review gates, evidence, and sandboxing.
- `integrations/humanize/`: adapter prompts and config templates for a Claude Builder + Codex Reviewer loop.
- `examples/task_contracts/`: starter contracts that render complete task workspaces.
- `schemas/`: JSON schemas for task contracts, goals, wiki pages, evidence, candidates, and review artifacts.

## Quick Start

```bash
python -m pip install -e ".[dev]"
python .agents/skills/RLInfraWiki/scripts/query.py "Megatron SGLang rollout" --limit 5
python .agents/skills/RLInfraWiki/scripts/render_task_bundle.py \
  --contract examples/task_contracts/slime-weight-sync.yaml \
  --output /tmp/rl-infra-task-workspace
python .agents/skills/RLInfraWiki/scripts/lock_plan.py --workspace /tmp/rl-infra-task-workspace
python .agents/skills/RLInfraWiki/scripts/render_rlcr_context.py --workspace /tmp/rl-infra-task-workspace --round 1
python .agents/skills/RLInfraWiki/scripts/validate_review_gate.py --workspace /tmp/rl-infra-task-workspace
```

`render_task_bundle.py` writes only into an empty workspace by default. Re-render an existing scaffold with `--force`; review ledgers and scaffolded docs under `docs/` are preserved unless destructive reset flags such as `--reset-ledgers` or `--overwrite-human-docs` are explicit. If the task contract changed and docs are preserved, the renderer warns and the review gate requires `docs/validation_matrix.md` to include every contract validation command.

## Validation

```bash
python .agents/skills/RLInfraWiki/scripts/validate.py
python .agents/skills/RLInfraWiki/scripts/generate_indices.py --check
python .agents/skills/RLInfraWiki/scripts/repo_status.py
pytest -q
```

All upstream capability claims are treated as `source-reported` unless this repository has local reproduction evidence with command, hardware, commit, log, and result.
