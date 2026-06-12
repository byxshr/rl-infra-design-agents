---
id: pattern-disaggregated-train-rollout
title: Disaggregated Train Rollout
type: pattern
frameworks:
- slime
- roll
- areal
backends:
- sglang
- vllm
- megatron
components:
- training
- rollout
- weight-sync
algorithms:
- ppo
- grpo
deployment_modes:
- disaggregated
tags:
- pattern
- architecture
confidence: inferred
reproducibility: concept
sources:
- repo-thudm-slime-readme
- repo-verl-readme
- repo-inclusionai-areal-readme
- repo-alibaba-roll-readme
- repo-vllm-readme
- repo-sglang-readme
version_sensitive:
- vs-slime-main-2026-06-12
- vs-verl-main-2026-06-12
- vs-areal-main-2026-06-12
- vs-roll-main-2026-06-12
- vs-vllm-main-2026-06-12
- vs-sglang-main-2026-06-12
created_at: '2026-06-12'
updated_at: '2026-06-12'
summary: Pattern for separate training and rollout resources with explicit weight
  version and transport boundary.
risks:
- stale-policy
- version-mismatch
- observability-gap
---

# Disaggregated Train Rollout

Pattern for separate training and rollout resources with explicit weight version and transport boundary.

## Use When

- The task objective names these frameworks or components.
- The acceptance criteria require explicit failure modes, rollback, and observability.
- The rollout and training surfaces have different latency, memory, or scaling needs.

## Validation Ideas

- Version monotonicity test.
- Cache flush or cache namespace test.
- Rollout/train logprob mismatch smoke test.
- Failure injection for sync timeout or partial reward.

All capability statements on this page are source-reported unless explicitly marked otherwise. Local throughput or quality claims require separate evidence.
