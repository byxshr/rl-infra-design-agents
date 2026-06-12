---
id: weight-sync-disk-checkpoint-sync
title: Disk Checkpoint Sync
type: weight-sync
frameworks:
- slime
- vllm
- sglang
backends:
- sglang
- vllm
components:
- weight-sync
- checkpoint
algorithms:
- rlhf
deployment_modes:
- disaggregated
- external-service
tags:
- weight-sync
- checkpoint
confidence: inferred
reproducibility: concept
sources:
- repo-thudm-slime-readme
- doc-vllm-training-weight-transfer
- repo-sglang-readme
version_sensitive:
- vs-slime-main-2026-06-12
- vs-vllm-main-2026-06-12
- vs-sglang-main-2026-06-12
created_at: '2026-06-12'
updated_at: '2026-06-12'
summary: Use shared filesystem or object storage to publish full checkpoints or update
  files to rollout backends.
risks:
- partial-weight-update
- version-mismatch
- cache-staleness
- rollback-gap
---

# Disk Checkpoint Sync

Use shared filesystem or object storage to publish full checkpoints or update files to rollout backends.

## Required Fields In A Design

- `training_step_id` and `weight_version_id`.
- Primary sync path and full fallback path.
- Pause, abort, continue, and retry behavior.
- KV/prefix cache policy after weight update.
- Rollback procedure for partial or failed update.
- Evidence command proving version monotonicity and rollout backend freshness.

All capability statements on this page are source-reported unless explicitly marked otherwise. Local throughput or quality claims require separate evidence.
