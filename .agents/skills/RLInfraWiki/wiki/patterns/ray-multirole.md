---
id: pattern-ray-multirole
title: Ray Multi-Role
type: pattern
frameworks:
- roll
- verl
backends:
- ray
- vllm
- sglang
components:
- scheduler
- training
- rollout
- reward
algorithms:
- rlvr
deployment_modes:
- ray-multirole
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
summary: Pattern for explicit Ray roles such as actor_train, actor_infer, reference,
  reward, and validation.
risks:
- stale-policy
- version-mismatch
- observability-gap
---

# Ray Multi-Role

Pattern for explicit Ray roles such as actor_train, actor_infer, reference, reward, and validation.

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
