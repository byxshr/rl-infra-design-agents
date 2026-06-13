# RL-infra-design-agents

[![validate](https://github.com/byxshr/rl-infra-design-agents/actions/workflows/validate.yml/badge.svg)](https://github.com/byxshr/rl-infra-design-agents/actions/workflows/validate.yml)

`RL-infra-design-agents` is a lightweight workflow and knowledge-base repository for RL, RLHF, RLVR, and agentic-RL infrastructure design tasks. It is not an RL framework and does not wrap slime, verl, AReaL, ROLL, vLLM, SGLang, or Megatron-LM.

The default workflow is Humanize-compatible RLCR:

1. Human Architect defines the task contract and acceptance criteria.
2. Claude Builder drafts the plan and implements one candidate batch at a time.
3. Codex Reviewer independently checks goal alignment, provenance, validation, risks, and diff quality.
4. Review issues are normalized into JSONL and resolved, waived, or escalated as goal amendments.

## Repository Layout

- `.agents/skills/RLInfraWiki/`: standalone RLInfraWiki dependency pinned by this repo; the root is the skill root.
- `docs/`: workflow documentation for goal contracts, RLCR, review gates, evidence, and sandboxing.
- `integrations/humanize/`: adapter prompts and config templates for a Claude Builder + Codex Reviewer loop.
- `examples/task_contracts/`: starter contracts that render complete task workspaces.
- `schemas/`: JSON schemas for task contracts, goals, wiki pages, evidence, candidates, and review artifacts.

## Quick Start

Initialize the RLInfraWiki dependency first:

```bash
git submodule update --init --recursive
```

`.gitmodules` uses the relative URL `../RLInfraWiki`, which resolves to the sibling GitHub repository `https://github.com/byxshr/RLInfraWiki` when this repo is cloned from `https://github.com/byxshr/rl-infra-design-agents`. This also preserves fork-friendly submodule behavior. In the original authoring workspace, `.git/config` may still contain a local override to the sibling checkout; run `git submodule sync` to reset local config back to `.gitmodules`.

To force an explicit absolute URL instead of the relative sibling URL:

```bash
git config -f .gitmodules 'submodule..agents/skills/RLInfraWiki.url' https://github.com/byxshr/RLInfraWiki
git submodule sync .agents/skills/RLInfraWiki
git submodule update --init --recursive
```

Run the P0 demo:

```bash
conda run -n rl-infra-design-agents make demo
```

Expected result: checks pass, `/tmp/rl-infra-task-workspace` is rendered, `Review gate passed` is printed, and the workspace contains:

- `context/context_bundle.md`
- `context/context_bundle.json`
- `context/context_sources.yaml`
- `docs/draft.md` and `docs/plan.md` with primary sync path, full fallback, `weight_version`, `flush_cache`, failure modes, Wiki page IDs, and source IDs.

Run the slime GRPO/RLVR data-contract demo:

```bash
conda run -n rl-infra-design-agents make demo-slime-grpo-contract
```

Expected result: `/tmp/slime-grpo-rlvr-data-contract-workspace` is rendered and `Review gate passed` is printed. This task designs a slime-compatible algorithm data contract for rollout outputs, reward/verifier results, policy-version metadata, grouped GRPO samples, and trainer inputs. It is not a full GRPO/RLVR implementation and does not claim runtime, GPU, distributed, throughput, latency, or production verification.

Manual sequence:

```bash
python -m pip install -e ".[dev]"
python .agents/skills/RLInfraWiki/scripts/query.py "Megatron SGLang rollout" --limit 5
python .agents/skills/RLInfraWiki/scripts/compose_context.py \
  --target-framework slime \
  --task "Design a weight synchronization path between Megatron training and SGLang rollout for an RL pipeline." \
  --mode design \
  --output /tmp/rl-infra-context.md
python .agents/skills/RLInfraWiki/scripts/validate_context_bundle.py /tmp/rl-infra-context.md
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
python .agents/skills/RLInfraWiki/scripts/compose_context.py --target-framework verl --task "add SGLang rollout backend with weight sync" --mode design --output /tmp/context_bundle.md
python .agents/skills/RLInfraWiki/scripts/validate_context_bundle.py /tmp/context_bundle.md
python .agents/skills/RLInfraWiki/scripts/validate.py
python .agents/skills/RLInfraWiki/scripts/generate_indices.py --check
python .agents/skills/RLInfraWiki/scripts/repo_status.py
pytest -q
```

All upstream capability claims are treated as `source-reported` unless this repository has local reproduction evidence with command, hardware, commit, log, and result.
