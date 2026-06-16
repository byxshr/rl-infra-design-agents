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

Run the rollout backend selection demo:

```bash
conda run -n rl-infra-design-agents make demo-rollout-backend-selection
```

Expected result: `/tmp/rollout-backend-selection-workspace` is rendered and `Review gate passed` is printed. This task designs a target-aware, cross-framework selection packet for SGLang versus vLLM as a rollout backend for verl RLVR/GRPO. The rendered plan includes `primary_backend`, `fallback_backend`, primary weight update path, full fallback, `weight_version`, cache policy, logprob policy, failure modes, Wiki page IDs, source IDs, and explicit non-claims for GPU/NCCL/multi-node/performance/production verification.

Run the training/rollout mismatch debugging demo:

```bash
conda run -n rl-infra-design-agents make demo-training-rollout-mismatch-debug
```

Expected result: `/tmp/training-rollout-mismatch-debug-workspace` is rendered and `Review gate passed` is printed. This task designs a source-traceable debugging packet for slime training/rollout mismatch, including `policy_version`, `weight_version`, stale KV cache, rollout `old_logprob` versus trainer recompute, token/mask/schema drift, reward/data-buffer handoff, Wiki page IDs, source IDs, and explicit non-claims for GPU/NCCL/multi-node/performance/production verification.

## Humanize-ready task

Use the start wrapper as the recommended entry for a real RL infra task contract:

```bash
conda run -n rl-infra-design-agents make start-humanize-task \
  CONTRACT=examples/task_contracts/training-rollout-mismatch-debug.yaml \
  HUMANIZE_WORKSPACE=/tmp/rlinfra-humanize-task-workspace \
  TARGET_REPO=/path/to/target/repo \
  DIFF_BASE=main \
  ROUND=1
```

This command runs the IMP-013 preparation flow, then prints and records the operator steps needed to start Humanize in Claude Code, import the produced round, and run the review gate. It writes:

- `/tmp/rlinfra-humanize-task-workspace/humanize_operator.md`
- `/tmp/rlinfra-humanize-task-workspace/humanize_start.md`
- `/tmp/rlinfra-humanize-task-workspace/.humanize/rlinfra_operator.json`
- `/tmp/rlinfra-humanize-task-workspace/.humanize/rlinfra_bridge.json`

The wrapper does not automatically start Claude Code or run the Humanize plugin. It prepares the workspace and prints the next commands. Open Claude Code in the prepared workspace, then run:

```bash
cd /tmp/rlinfra-humanize-task-workspace
```

```text
/humanize:start-rlcr-loop docs/plan.md
```

After Humanize writes `.humanize/rlcr/<timestamp>/round-N-summary.md` and `round-N-review-result.md`, import the round back into this workspace's RLCR ledger:

```bash
conda run -n rl-infra-design-agents make import-humanize-round \
  HUMANIZE_WORKSPACE=/tmp/rlinfra-humanize-task-workspace \
  ROUND=1
```

If more than one loop directory exists, add `HUMANIZE_LOOP_DIR=/tmp/rlinfra-humanize-task-workspace/.humanize/rlcr/<timestamp>`.

Then require a Codex review artifact in the local gate:

```bash
conda run -n rl-infra-design-agents python .agents/skills/RLInfraWiki/scripts/validate_review_gate.py \
  --workspace /tmp/rlinfra-humanize-task-workspace \
  --require-review
```

The importer validates the bridge schema, copies the Humanize summary/review into `review_rounds/round-001/`, normalizes `[P0]` to `[P3]` findings into parser-compatible headings, preserves the raw Humanize review output, writes `humanize_round_metadata.json` with file hashes, bridge provenance, stale-workspace warnings, and UTF-8 replacement markers, and updates `review_issues.jsonl`. COMPLETE/no-finding rounds satisfy `--require-review`; open P0/P1/P2 findings still block promotion through the existing review gate.

The operator metadata mirrors the bridge metadata path and records schema version, contract, workspace, target repo, diff base, round, prerequisite warnings, and the exact prepare/start/import/gate commands. If Humanize or the `codex` CLI is unavailable, preparation still succeeds by default and records prerequisite warnings in `.humanize/rlinfra_bridge.json` and `.humanize/rlinfra_operator.json`. Add `--strict-prereqs` when missing local Humanize/Codex prerequisites should fail the wrapper with the same exit code as `prepare_humanize_task.py`.

The lower-level preparation entry remains available when the operator guide is not needed:

```bash
conda run -n rl-infra-design-agents make prepare-humanize-task \
  CONTRACT=examples/task_contracts/training-rollout-mismatch-debug.yaml \
  HUMANIZE_WORKSPACE=/tmp/rlinfra-humanize-task-workspace \
  TARGET_REPO=/path/to/target/repo \
  DIFF_BASE=main
```

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
