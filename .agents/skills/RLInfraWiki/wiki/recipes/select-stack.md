---
id: recipe-select-stack
title: Select Stack
type: recipe
frameworks:
- slime
- verl
- areal
- roll
backends:
- sglang
- vllm
- megatron
- fsdp
components:
- training
- rollout
- scheduler
algorithms:
- ppo
- grpo
- rlvr
deployment_modes:
- colocated
- disaggregated
- async
tags:
- recipe
- playbook
confidence: inferred
reproducibility: concept
sources:
- repo-thudm-slime-readme
- repo-verl-readme
- repo-inclusionai-areal-readme
- repo-alibaba-roll-readme
- repo-vllm-readme
- repo-sglang-readme
- repo-nvidia-megatron-lm-readme
version_sensitive:
- vs-slime-main-2026-06-12
- vs-verl-main-2026-06-12
- vs-areal-main-2026-06-12
- vs-roll-main-2026-06-12
- vs-vllm-main-2026-06-12
- vs-sglang-main-2026-06-12
- vs-megatron-main-2026-06-12
created_at: '2026-06-12'
updated_at: '2026-06-12'
summary: Recipe for selecting framework, trainer, rollout backend, orchestration,
  and validation strategy.
risks:
- provenance-gap
- rollback-gap
- observability-gap
---

# Select Stack

Recipe for selecting framework, trainer, rollout backend, orchestration, and validation strategy.

## Steps

1. State objective, non-goals, and acceptance criteria.
2. Query RLInfraWiki and list page IDs plus source IDs.
3. Draw sample lifecycle from prompt source to metrics/traces.
4. Choose primary path and fallback path.
5. Add validation commands and evidence paths.
6. Prepare the Codex review packet.

All capability statements on this page are source-reported unless explicitly marked otherwise. Local throughput or quality claims require separate evidence.
