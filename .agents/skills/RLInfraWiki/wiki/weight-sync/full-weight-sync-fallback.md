---
id: weight-sync-full-weight-sync-fallback
title: Full Weight Sync Fallback
type: weight-sync
frameworks:
- slime
- vllm
- sglang
backends:
- vllm
- sglang
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
- doc-sglang-rl-systems
- repo-sglang-readme
version_sensitive:
- vs-slime-main-2026-06-12
- vs-sglang-main-2026-06-12
created_at: '2026-06-12'
updated_at: '2026-06-13'
summary: >-
  Full weight sync fallback is the recovery path for any optimized weight update
  mode: publish a known-good checkpoint, reload SGLang engines, flush cache,
  confirm version, and resume rollout only after all engines agree.
risks:
- partial-weight-update
- version-mismatch
- cache-staleness
- rollback-gap
---

# Full Weight Sync Fallback

Full weight sync fallback is required whenever the primary path is tensor, distributed group, or delta. The fallback is not just "save a checkpoint"; it is a recovery sequence that prevents mixed-version rollout data from entering training.

## Evidence Basis

- `weight-sync-disk-checkpoint-sync` cites `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_disk.py:61` for versioned full checkpoint publication and reload.
- `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_distributed.py:247` shows why optimized broadcast paths need failure handling around bucket-level updates and locks.
- `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_distributed_delta.py:568` shows delta sync depends on a seeded snapshot and therefore needs resync when baseline integrity is in doubt.
- `doc-sglang-rl-systems` (`../sglang/docs/advanced_features/sglang_for_rl.md:82`) documents disk reload with `weight_version` and `flush_cache`.
- `doc-sglang-rl-systems` (`../sglang/docs/advanced_features/sglang_for_rl.md:107`) documents the Python engine API `engine.update_weights_from_disk(model_path, load_format=None)`.

## Design Implications

- Full fallback should point at an immutable, complete checkpoint directory that survives primary-path cleanup.
- Rollout ingestion should stop until every engine confirms the fallback `weight_version`.
- Destroy or quarantine failed distributed groups before invoking fallback reload.
- Cache flush should default to true after fallback because fallback usually follows an inconsistency event.
- The fallback path should be tested even if the primary path is expected to be reliable.

## Failure Modes

- Fallback checkpoint was written after the failed partial update and is not actually known-good.
- The plan reloads engines but keeps accepting rollout samples from the failed version window.
- Cleanup removes the fallback directory.
- Router or PD deployment continues routing to engines that did not complete reload.
- The fallback load format differs from the primary model format and fails under pressure.

## Validation Ideas

- Keep at least one previous known-good checkpoint until the next version has completed rollout validation.
- After fallback, run an engine version fanout check and discard rollout data from the failed window.
- Include a rollback runbook in the design packet: stop ingestion, pause engines, reload checkpoint, flush cache, verify version, resume.
- Review whether router health checks can isolate engines that fail fallback reload.

## Open Gaps

- No automated review gate currently enforces that every optimized path names a full fallback.
- Cluster-specific checkpoint retention and router isolation policies must be supplied by the task owner.

All capability statements on this page are source-reported unless explicitly marked otherwise. Local throughput or quality claims require separate evidence.
