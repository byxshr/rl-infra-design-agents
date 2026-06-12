# Page Authoring Guide

How to author wiki pages with frontmatter, source IDs, and risks.

Always cite page IDs and source IDs. Avoid marking source-reported claims as verified unless local reproduction evidence is present.

## Evidence-Led Page Shape

RLInfraWiki follows the same layered discipline as KernelWiki, adapted for RL infrastructure:

- `sources/` holds traceable upstream repository and documentation manifests.
- `wiki/` holds synthesized design knowledge.
- `queries/` holds generated indices and must not be edited manually.

Wiki pages should summarize evidence; they should not copy large upstream source files, README sections, or docs. A review-ready page should include these sections:

- `Evidence Basis`: source IDs, source categories, local clone paths, symbols, and line anchors when useful.
- `Design Implications`: what the evidence means for architecture choices.
- `Failure Modes`: concrete ways the design can break.
- `Validation Ideas`: smoke tests, review checks, or runtime assertions the design should include.
- `Open Gaps`: facts that still need local reproduction, benchmark data, or upstream refresh.

## Evidence Citation Format

Use compact bullets that let another agent verify the claim quickly:

```text
- source_id: doc-sglang-rl-systems
  evidence_type: upstream-doc
  local_path: ../sglang/docs/advanced_features/sglang_for_rl.md:63
  symbols: POST /update_weights_from_disk, POST /update_weights_from_distributed
  observation: SGLang documents disk, tensor, and distributed refit paths with weight_version and flush_cache controls.
```

For local code evidence, include the repo-relative path and the class, function, or config name:

```text
- source_id: repo-thudm-slime-readme
  evidence_type: upstream-code
  local_path: ../slime/slime/backends/megatron_utils/update_weight/update_weight_from_distributed.py:102
  symbols: UpdateWeightFromDistributed.update_weights
  observation: slime pauses generation, flushes rollout caches, sends converted HF weight buckets, then resumes generation.
```

Use `confidence: source-reported` for upstream docs and code-reading claims. Use `confidence: inferred` when the page combines multiple systems into a design recommendation. Reserve `confidence: verified` for claims backed by local command output, hardware/context, and logs or artifacts.

## Review-Ready Checklist

Before promoting a page in `docs/rlinfrawiki-content-status.md`:

- The frontmatter `sources:` list resolves through `get_page.py --follow-sources`.
- The body cites at least one concrete path or symbol for each major system claim.
- The page states cache, version, rollback, and observability implications when weight sync is involved.
- The page avoids local performance or quality claims unless a `local_evidence` block exists.
- `updated_at` and the ledger `last_reviewed` date are current.
