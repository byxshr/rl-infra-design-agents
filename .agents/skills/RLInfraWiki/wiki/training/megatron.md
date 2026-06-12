---
id: training-megatron
title: Megatron-LM / Megatron Core
type: training
frameworks:
- megatron-lm
backends:
- megatron
components:
- training
- checkpoint
algorithms:
- rlhf
- grpo
deployment_modes:
- colocated
- disaggregated
tags:
- megatron-lm
- tp
- pp
- dp
- ep
- cp
confidence: source-reported
reproducibility: concept
sources:
- repo-nvidia-megatron-lm-readme
- doc-megatron-fsdp
version_sensitive:
- vs-megatron-main-2026-06-12
created_at: '2026-06-12'
updated_at: '2026-06-13'
summary: >-
  Megatron-LM is the trainer side of the P0 path: its RL example documents GRPO,
  HF-to-Megatron checkpoint conversion, TP/PP settings, and checkpoint directories
  that slime must convert or stream into SGLang rollout engines.
risks:
- version-mismatch
- rollback-gap
---

# Megatron-LM / Megatron Core

Megatron-LM / Megatron Core is the training backend in the P0 slime + SGLang design. The review focus is not generic training capability; it is whether Megatron parameter layout, checkpoint format, and parallelism choices can be converted or streamed safely into SGLang rollout engines.

## Evidence Basis

- `repo-nvidia-megatron-lm-readme` (`../Megatron-LM/README.md:20`) describes Megatron Core as a library for custom training frameworks with TP, PP, DP, EP, CP, mixed precision, and model building blocks.
- `../Megatron-LM/examples/rl/README.md:3` states the example is a GRPO implementation within Megatron-LM.
- `../Megatron-LM/examples/rl/README.md:36` points to `tools/checkpoint/convert.py` for Hugging Face to Megatron conversion.
- `../Megatron-LM/examples/rl/README.md:66` and `:67` expose `--tensor-model-parallel-size` and `--pipeline-model-parallel-size` in the RL experiment command.
- `../Megatron-LM/examples/rl/README.md:98` uses `--pretrained-checkpoint`, while `:169` to `:176` include TensorBoard, sequence parallel, save/load, and checkpoint interval settings.
- `doc-megatron-fsdp` (`../Megatron-LM/docs/user-guide/features/megatron_fsdp.md:221`) documents distributed checkpointing support and conversion considerations for FSDP-style checkpoints.

## Design Implications

- The design must record TP, PP, EP, DP, and CP choices because slime's update path gathers TP/EP shards and treats PP source ranks specially.
- HF-to-Megatron conversion is not the same as Megatron-to-HF rollout refit. The rollout sync plan needs an explicit direction for each conversion boundary.
- Checkpoint directories are operational state, not just training artifacts. Disk fallback should point at versioned, immutable directories.
- Megatron-FSDP and Megatron Core checkpoint formats can differ; a design should avoid assuming one universal checkpoint loader.

## Failure Modes

- Parameter names can diverge between Megatron and Hugging Face/SGLang loaders, causing missing or misapplied tensors.
- Wrong TP/PP/EP metadata can create shape mismatches or incomplete expert parameter updates.
- Checkpoint conversion may succeed structurally but produce a rollout model with different tokenizer/config assumptions.
- FSDP/DCP checkpoint formats can introduce extra prefixes or sharding assumptions that a rollout backend cannot consume directly.

## Validation Ideas

- Include a conversion dry-run or manifest check that lists parameter names before and after Megatron-to-HF conversion.
- Validate that the selected slime update path handles both non-expert and expert parameters for the target model.
- Store the Megatron commit, checkpoint format, TP/PP/EP sizes, and tokenizer path in the review packet.
- When disk fallback is used, confirm the fallback checkpoint is readable by the same SGLang load format named in the primary design.

## Open Gaps

- No local checkpoint conversion was executed in this content pass.
- RLInfraWiki still needs a dedicated page for Megatron checkpoint naming and conversion edge cases if future tasks focus on FSDP or MoE.

All capability statements on this page are source-reported unless explicitly marked otherwise. Local throughput or quality claims require separate evidence.
