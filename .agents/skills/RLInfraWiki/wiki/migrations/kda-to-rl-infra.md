---
id: migration-kda-to-rl-infra
title: KDA To RL Infra
type: migration
frameworks:
- slime
- verl
- areal
- roll
backends:
- sglang
- vllm
- megatron
components:
- training
- rollout
- observability
algorithms:
- rlvr
deployment_modes:
- colocated
- disaggregated
- async
tags:
- migration
- workflow
confidence: inferred
reproducibility: concept
sources:
- repo-thudm-slime-readme
- repo-verl-readme
- repo-inclusionai-areal-readme
- repo-alibaba-roll-readme
version_sensitive:
- vs-slime-main-2026-06-12
- vs-verl-main-2026-06-12
- vs-areal-main-2026-06-12
- vs-roll-main-2026-06-12
created_at: '2026-06-12'
updated_at: '2026-06-12'
summary: 'Map KDA workflow concepts to RL infrastructure design workspaces: wiki query,
  draft, plan, candidate, validation, evidence, review, and promotion.'
risks:
- provenance-gap
---

# KDA To RL Infra

This migration keeps the reusable workflow repository separate from task workspaces. Kernel-specific pages become RL infrastructure pages, and benchmark evidence becomes design validation evidence.

## Mapping

| KDA concept | RL infra equivalent |
|---|---|
| KernelWiki | RLInfraWiki |
| kernel candidate | design candidate or task implementation batch |
| benchmark evidence | validation matrix and evidence logs |
| promotion | review-gated candidate acceptance |

All capability statements on this page are source-reported unless explicitly marked otherwise. Local throughput or quality claims require separate evidence.
