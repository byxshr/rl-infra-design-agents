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
- doc-sglang-rl-systems
- repo-sglang-readme
version_sensitive:
- vs-slime-main-2026-06-12
- vs-sglang-main-2026-06-12
created_at: '2026-06-12'
updated_at: '2026-06-13'
summary: Disk checkpoint sync publishes a versioned HF checkpoint from slime and
  asks SGLang rollout engines to reload it, making it the safest full fallback
  for distributed, tensor, or delta sync.
risks:
- partial-weight-update
- version-mismatch
- cache-staleness
- rollback-gap
---

# Disk Checkpoint Sync

Disk checkpoint sync is the simplest full-weight path: the trainer writes a versioned model directory, rollout engines pause and flush cache, then each engine reloads the checkpoint. It is slower than direct tensor or NCCL transfer but gives the design an inspectable recovery point.

## Evidence Basis

- `repo-thudm-slime-readme` / upstream code `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_disk.py:61` increments `weight_version` and creates `weight_v%06d` under `args.update_weight_disk_dir`.
- `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_disk.py:71` pauses generation and flushes rollout caches before saving/reloading.
- `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_disk.py:78` saves an HF-format model directory through `save_hf_model_to_path`.
- `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_disk.py:87` calls `engine.update_weights_from_disk(model_path=..., weight_version=...)`.
- `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_disk.py:93` optionally removes the version directory after engines confirm the reload.
- `doc-sglang-rl-systems` (`../sglang/docs/advanced_features/sglang_for_rl.md:82`) documents `POST /update_weights_from_disk`, including `model_path`, `weight_version`, and `flush_cache`.

## Design Implications

- Use disk sync as the mandatory fallback for delta, tensor, and distributed primary paths.
- Treat checkpoint publication as atomic: engines should only see complete, immutable version directories.
- If files are deleted after update, keep a separate last known-good checkpoint for rollback.
- Disk sync is the easiest path for elastic rollout engines because new engines can load the same model path.

## Failure Modes

- Shared filesystem lag exposes a half-written checkpoint to rollout engines.
- Cleanup removes the only rollback checkpoint.
- One engine reloads successfully while another fails, leaving a mixed-version rollout fleet.
- SGLang load format or tokenizer/config metadata differs from the saved HF directory.

## Validation Ideas

- Validate that `weight_v000001` style directories are immutable before calling engine reload.
- Confirm every engine returns success for the same `weight_version` before resuming rollout ingestion.
- Simulate reload failure and verify the plan reloads the previous version or stops rollout.
- Record checkpoint path, file retention policy, and cleanup behavior in the review packet.

## Open Gaps

- This page does not prove filesystem durability semantics for a specific cluster.
- No local SGLang reload command was run; evidence is from slime code and SGLang docs.

All capability statements on this page are source-reported unless explicitly marked otherwise. Local throughput or quality claims require separate evidence.
