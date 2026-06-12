---
id: system-slime
title: slime
type: system
frameworks:
- slime
backends:
- sglang
- megatron
components:
- training
- rollout
- data-buffer
- weight-sync
- router
algorithms:
- ppo
- grpo
deployment_modes:
- colocated
- disaggregated
- async
tags:
- slime
- sglang
- megatron-lm
- weight-sync
- agentic
confidence: source-reported
reproducibility: concept
sources:
- repo-thudm-slime-readme
- repo-sglang-readme
- repo-nvidia-megatron-lm-readme
version_sensitive:
- vs-slime-main-2026-06-12
- vs-sglang-main-2026-06-12
- vs-megatron-main-2026-06-12
created_at: '2026-06-12'
updated_at: '2026-06-12'
summary: slime is an LLM post-training framework centered on Megatron training, SGLang
  rollout/router, and a Data Buffer path.
risks:
- partial-weight-update
- version-mismatch
- long-tail-rollout
---

# slime

slime is useful when the design wants to stay close to Megatron training and SGLang serving surfaces rather than introduce a lowest-common-denominator backend abstraction.

## Design Notes

- Treat Megatron arguments, SGLang arguments, Data Buffer flow, rollout customization, and weight sync as first-class interfaces.
- For disaggregated rollout, include full checkpoint fallback even when delta sync is the target path.
- For agentic tasks, keep the custom rollout function and reward/verifier path explicit.

## Risks

Version tagging, partial updates, router affinity, and rollout/train mismatch should be represented in the validation matrix.

All capability statements on this page are source-reported unless explicitly marked otherwise. Local throughput or quality claims require separate evidence.
