# Code Review — rl-infra-design-agents

- Date: 2026-06-12
- Scope: full repository (no upstream commits yet — initial scaffold)
- Reference: `docs/ai-agent-code-review-reference.md`
- Reviewer posture: independent gatekeeper (no files modified)

## Validation Run

| Command | Result |
|---|---|
| `python .agents/skills/RLInfraWiki/scripts/validate.py` | PASS — `RLInfraWiki validation passed` |
| `python .agents/skills/RLInfraWiki/scripts/generate_indices.py --check` | PASS — `generated query indices are current` |
| `pytest -q` | PASS — 7 passed |
| `render_task_bundle.py` → `lock_plan.py` → `render_rlcr_context.py --round 1` → `validate_review_gate.py` | PASS — gate passed (with WARN for missing `codex_review.md`, expected) |

Baseline counts vs reference §"Current Expected Baseline":

| Artifact | Expected | Actual | OK |
|---|---|---|---|
| Wiki pages | ~33 | 37 (incl. README placeholders) | yes |
| Source manifests | 12 | 12 | yes |
| Version claim records | 7 | 7 | yes |
| Generated query indices | 9 | 9 | yes |
| Python scripts | 23 | 23 | yes |
| Pytest tests | 7 | 7 | yes |

Workspace contract: every required path in reference §"Task Workspace Contract" is produced by `render_task_bundle.py` + `lock_plan.py`. The `skills/` symlink correctly points to `.agents/skills/RLInfraWiki` (no duplicate source of truth).

## Findings

### P0: Review gate treats "waived" / "backlog" as resolved for all severities, including P0/P1

- File/path: `.agents/skills/RLInfraWiki/scripts/validate_review_gate.py:26` (relies on `_rlinfra.RESOLVED_STATUSES` at `.agents/skills/RLInfraWiki/scripts/_rlinfra.py:21`)
- Evidence:
  - `_rlinfra.py:21` — `RESOLVED_STATUSES = {"resolved", "fixed", "closed", "waived", "backlog"}`
  - `validate_review_gate.py:24-28`:
    ```python
    status = issue.get("status", "open")
    severity = issue.get("severity")
    if status in RESOLVED_STATUSES:
        continue
    if severity in {"P0", "P1"}:
        errors.append(...)
    ```
  - The status filter runs BEFORE the severity branch, so a `severity: P0, status: waived` row is dropped silently. The rendered policy in `.humanize/rlcr_config.yaml` (written by `render_task_bundle.py:107-109`) explicitly says `waiver_allowed_for: [P2]` and `backlog_allowed_for: [P3]` — code and policy disagree.
- Why it blocks: Reference §"Blocking Review Checks" lists "Weakens `validate_review_gate.py` so unresolved P0/P1 issues no longer block promotion." A reviewer (or automation) can mark an unresolved P0 with `status: waived` and the gate prints "Review gate passed."
- Suggested fix: split the resolution policy by severity. Use a per-severity allow-set: `{P0, P1}` only honor `{resolved, fixed, closed}`; `{waived, backlog}` allowed only for P2/P3 (with `P2` requiring an approved waiver in `review_waivers.jsonl`). Reorder the loop so severity is inspected first.

### P0: `render_task_bundle.py` re-render truncates the entire RLCR ledger

- File/path: `.agents/skills/RLInfraWiki/scripts/render_task_bundle.py:115-116`
- Evidence:
  ```python
  for rel in [".humanize/codex_invocations.jsonl",
              ".humanize/claude_iterations.jsonl",
              "review_issues.jsonl",
              "review_waivers.jsonl",
              "candidates.jsonl"]:
      write(output / rel, "")
  ```
  `write()` (line 12-14) calls `path.write_text(...)`, which overwrites unconditionally. Re-running `render_task_bundle.py --output <existing-workspace>` zeros all five JSONLs, including `review_issues.jsonl` — the file `validate_review_gate.py` keys off.
- Why it blocks: Wiping `review_issues.jsonl` makes an unresolved P0 disappear and the gate then reports "passed" with no evidence anything was lost. Matches reference blockers "Lets a candidate promote without required validation evidence" and "Causes `render_task_bundle.py` ... to produce incomplete RLCR workspaces."
- Suggested fix: Only seed empty JSONLs when the file does not yet exist (`if not p.exists(): p.write_text("")`), or refuse to re-render an existing workspace unless `--force` is passed and emit a list of files that would be overwritten.

### P0: `render_task_bundle.py` silently overwrites human-edited workspace docs on re-render

- File/path: `.agents/skills/RLInfraWiki/scripts/render_task_bundle.py:21, 24, 93-95, 96-114, 117-119`
- Evidence: `docs/goal.md`, `docs/plan.md`, `docs/draft.md`, `docs/validation_matrix.md`, `docs/risk_register.md`, `docs/goal_status.md`, `.humanize/rlcr_config.yaml`, `.humanize/loop_state.json`, `goal_versions.jsonl`, `progress_log.md`, `metrics.csv` are all written via `write()` (overwriting) on every call. `goal_versions.jsonl` is also clobbered to a single bootstrap line, dropping the goal-amendment history.
- Why it blocks: Reference §"Blocking Review Checks" first item — "Silently changes objective, acceptance criteria, non-goals, or review gate behavior." After the human or Claude refines `docs/goal.md` (acceptance criteria, non-goals) or `goal_versions.jsonl` (amendments), a subsequent `make render-example` reverts them with no warning. Same hazard for `rlcr_config.yaml` (changes to blocker_severities are silently re-stamped) and `loop_state.json` (round counter reset to 0).
- Suggested fix: `render_task_bundle.py` should write only into an empty directory by default. If `output/` exists, exit with a list of files that would be touched and require `--force`. Better: make a re-render idempotent by writing only files that do not yet exist for human-editable docs, and append new `goal_versions.jsonl` entries instead of replacing.

### P1: `verified` confidence accepts a truthy `local_evidence`, not the required subfields

- File/path: `.agents/skills/RLInfraWiki/scripts/validate.py:59`
- Evidence:
  ```python
  if fm.get("confidence") == "verified" and not fm.get("local_evidence"):
      errors.append(f"{rel}: verified claim requires local_evidence")
  ```
  Any truthy value (`local_evidence: see notes`) passes.
- Why it blocks: Reference §"Provenance Rules" — "Local evidence must include command, commit, hardware/context, log or artifact path, and result." The check satisfies the letter, not the spirit. Combined with the lack of runtime schema validation (next finding), `confidence: verified` can be added with empty/placeholder evidence and CI signs off.
- Suggested fix: Require `local_evidence` to be a mapping with non-empty `{command, commit, hardware|context, log|artifact_path, result}`. Push this constraint into `schemas/wiki_page.schema.json` so both the static schema and `validate.py` share one source of truth.

### P1: `validate.py` never validates artifacts against their JSON schemas at runtime

- File/path: `.agents/skills/RLInfraWiki/scripts/validate.py:16-22`
- Evidence:
  ```python
  def validate_schemas(errors):
      for path in sorted((PROJECT_ROOT / "schemas").glob("*.json")):
          schema = json.loads(path.read_text(encoding="utf-8"))
          jsonschema.Draft202012Validator.check_schema(schema)
  ```
  This only confirms each schema is itself well-formed. Wiki frontmatter, source manifests, version claims, task contracts, and `review_issues.jsonl` rows are checked only against hand-coded `REQUIRED_*_FIELDS` lists (lines 12-13, 90), so schema-level constraints (enums, sub-shapes, additionalProperties) never run.
- Why it blocks: Reference §"Blocking Review Checks" — "Breaks source IDs, version claim IDs, wiki frontmatter, schemas, or generated index checks." The schemas are aspirational without a runtime path. A frontmatter change that violates `wiki_page.schema.json` (wrong `type` enum, malformed `local_evidence`, etc.) passes today.
- Suggested fix: After `check_schema`, instantiate `Draft202012Validator(schema)` and validate the matching artifact set: wiki frontmatter → `wiki_page.schema.json`; `sources/**/*.yaml` → `source.schema.json`; `examples/task_contracts/*.yaml` → `task_contract.schema.json`; rows of `review_issues.jsonl` → `review_issue.schema.json`. Surface schema errors through the same `errors` list.

### P1: Review gate accepts unknown / mistyped severity values silently

- File/path: `.agents/skills/RLInfraWiki/scripts/validate_review_gate.py:25-31`
- Evidence:
  ```python
  severity = issue.get("severity")
  ...
  if severity in {"P0", "P1"}:
      errors.append(...)
  elif severity == "P2" and issue.get("id") not in waivers:
      warnings.append(...)
  ```
  An issue with `severity: null`, `severity: p1`, `severity: critical`, or `severity: P5` falls through both branches without producing an error or warning. `schemas/review_issue.schema.json` does not constrain `severity` to an enum, so JSON-level validation cannot save this either.
- Why it blocks: An issue inadvertently emitted with the wrong severity casing silently bypasses the gate — same effective behavior as reference's "weakens validate_review_gate.py" blocker, just by a different mechanism.
- Suggested fix: Add `properties.severity.enum: [P0, P1, P2, P3]` and `properties.status.enum: [...]` to `schemas/review_issue.schema.json`; in the gate, normalize to upper case, and treat any value outside the enum as a fail-closed P0 (with a clear "unknown severity" error message).

### P1: `generate_indices.py --check` does not detect orphan / hand-written index files

- File/path: `.agents/skills/RLInfraWiki/scripts/generate_indices.py:71` (the `--check` loop)
- Evidence: the loop iterates `for name, content in outputs.items():` — so any file in `queries/` that the generator does not emit (e.g., a hand-authored `queries/by-foo.md`) is invisible to `--check`.
- Why it blocks: Reference §"Blocking Review Checks" — "Manually edits generated query indices instead of regenerating them." A contributor can drop a hand-written index and CI silently approves; the reference explicitly forbids this.
- Suggested fix: After comparing expected outputs, walk `QUERIES_DIR.glob("*.md")` and treat any file whose name is not in the expected-output set (allowlist obvious non-generated like `README.md`) as drift. Exit non-zero.

### P2: `parse_codex_review.py` HEADING_RE matches narrative lines

- File/path: `.agents/skills/RLInfraWiki/scripts/parse_codex_review.py:10`
- Evidence:
  ```python
  HEADING_RE = re.compile(r"^(?:#{2,4}\s*)?(P[0-3])\s*[:\-]\s*(.+)$", re.IGNORECASE)
  ```
  The heading prefix is optional and the line is `.strip()`-ed, so any narrative line beginning with `P1: ...` (e.g., a sentence in a Summary or a recap of a suggested fix) is parsed as a brand-new issue heading. Each spurious match becomes an `open` row in `review_issues.jsonl`, and `validate_review_gate.py` then refuses to pass.
- Why it blocks: Inflates the unresolved-P0/P1 count and corrupts gate integrity in the false-positive direction (and a misclassified `P0` in body text could outright block promotion). Adjacent risk to the P0 gate-bypass since both feed the same ledger.
- Suggested fix: drop the optional heading group: `^#{2,4}\s+(P[0-3])\s*[:\-]\s*(.+)$`. Add a unit test that supplies a packet with `P1: foo` inside narrative text and asserts zero issues are parsed.

### P2: `task_contract.schema.json` and `validate.py` disagree on required fields

- File/path: `schemas/task_contract.schema.json:5-10` vs `.agents/skills/RLInfraWiki/scripts/validate.py:90`
- Evidence: schema requires `[task_name, objective, deliverables, promotion_criteria]`; runtime requires `[task_name, objective, deliverables, required_wiki_queries, promotion_criteria]`. A contract missing `required_wiki_queries` passes the schema but fails `validate.py`. Schema also has `additionalProperties: true` and no `properties` block (no type enforcement, no list-shape).
- Why it blocks: Schema-only consumers (CI, IDEs, third-party validators) accept contracts that fail at runtime. Combined with the lack of schema validation in `render_task_bundle.py`, an under-specified contract renders a workspace whose `goal.md` says "unnamed-task" and whose validation matrix is empty — a silent task-contract regression.
- Suggested fix: Add `required_wiki_queries` to the schema's `required` array, declare types under `properties`, and call the schema from `render_task_bundle.py` before rendering. Set `additionalProperties: false` once the property list is complete, or accept extras explicitly.

### P2: Wiki pages cite frameworks in body text without matching source IDs in frontmatter

- File/path: `.agents/skills/RLInfraWiki/wiki/systems/slime.md`, `.agents/skills/RLInfraWiki/wiki/systems/verl.md`
- Evidence:
  - `slime.md` frontmatter `sources: [repo-thudm-slime-readme]`; body cites Megatron and SGLang as first-class interfaces ("Megatron arguments, SGLang arguments, Data Buffer flow, rollout customization, and weight sync as first-class interfaces").
  - `verl.md` frontmatter `sources: [repo-verl-readme]`; body says "verl is a reference for designs that need backend choice across FSDP/FSDP2/Megatron training and vLLM/SGLang/HF rollout engines."
- Why it blocks: Reference §"Provenance Rules" — "Do not accept pages that cite a framework in body text but omit the relevant source ID in frontmatter." Allowing this normalizes provenance gaps for cross-framework claims.
- Suggested fix: Either add the missing source IDs (`repo-vllm-readme`, `repo-sglang-readme`, `repo-nvidia-megatron-lm-readme`) and corresponding `version_sensitive` IDs to each page, or scope the body to claims the listed source actually attests. Long-term: extend `check_provenance.py` to scan body text for canonical framework tokens (using `data/aliases.yaml` + `data/tags.yaml`) and emit a provenance error when a token appears in body but not in frontmatter.

### P2: `render_rlcr_context.py` silently emits an empty `plan_lock_sha256` when the lock is missing

- File/path: `.agents/skills/RLInfraWiki/scripts/render_rlcr_context.py:38` (relies on `_rlinfra.sha256_file:62-65`)
- Evidence: `sha256_file` returns `""` when the path does not exist, so the review packet header renders `- plan_lock_sha256: ` with no warning. `rlcr_config.yaml` declares `plan_lock.enabled: true`, so reviewers expect a real hash.
- Why it blocks: Hides the fact that `lock_plan.py` was never run. Pairs with the P0 ledger-truncation: a re-render plus a missing lock leaves no way for the reviewer to know the workspace is incomplete.
- Suggested fix: Fail fast in `render_rlcr_context.py` if `.humanize/plan.lock.md` is missing (`SystemExit("plan.lock.md missing — run lock_plan.py first")`), or write `MISSING` instead of an empty hash.

### P2: `build_candidate_ledger.py` has a dead branch and never produces a ledger artifact

- File/path: `.agents/skills/RLInfraWiki/scripts/build_candidate_ledger.py:14`
- Evidence: the filename-based check (`if "candidate" in Path(__file__).name`) is permanently true, so the `else` branch is unreachable. `--dry-run` is parsed but never inspected. The script only prints to stdout — no candidate ledger file is written, despite the script's name.
- Why it blocks: Reference §"Important P2 Checks" — "duplicated schema logic or ad hoc parsing where existing helpers in `_rlinfra.py` should be reused." Looks like a stale copy/paste leftover. Dead code in a workflow-critical directory invites future bugs.
- Suggested fix: Remove the filename branch, drop unused `--dry-run`, and either rename the script to reflect that it summarizes (not builds a ledger), or persist a real summary artifact (e.g., `metrics/candidates_summary.json`).

## Open Questions

- Should `render_task_bundle.py` ever be allowed to run against a non-empty workspace? If yes, what is the explicit safe-overwrite list (only stub READMEs?)? If no, this should be enforced and tested.
- The reference's "P0/P1 cannot be waived" rule is stated implicitly via blocker semantics. Should `schemas/review_waiver.schema.json` add `properties.severity.enum: [P2, P3]` to make the constraint enforceable at the schema level?
- `_rlinfra.RESOLVED_STATUSES` is used in one place today (the gate). Should it be split into `TERMINAL_STATUSES` (resolved/fixed/closed) and `DEFERRED_STATUSES` (waived/backlog) so callers must opt in to the deferral semantics?
- `parse_codex_review.py` discards review-packet sections such as "Why it blocks" — is that intentional? Issue triage may want it.

## Summary

The scaffold is internally consistent: counts match the expected baseline, `validate`/`indices`/`pytest` are green, and the end-to-end render→lock→context→gate pipeline works on `slime-weight-sync.yaml`.

However, the workflow's most load-bearing scripts — `validate_review_gate.py` and `render_task_bundle.py` — have **three P0 issues** that together let a builder silently bypass the RLCR review gate:

1. P0/P1 issues marked `waived`/`backlog` are treated as resolved by the gate, even though the rendered config forbids that.
2. Re-running `render_task_bundle.py` truncates `review_issues.jsonl`, deleting the issues the gate is supposed to enforce.
3. Re-running `render_task_bundle.py` overwrites human-edited `goal.md` / `plan.md` / `goal_versions.jsonl`, silently changing acceptance criteria — exactly the first P0 trigger in the reference.

The four P1 findings (truthy-only `local_evidence`, no runtime schema validation, lax severity parsing in the gate, generate_indices `--check` blind to orphan files) each independently allow the provenance / schema / index guarantees the reference describes to be bypassed.

Recommend resolving the three P0s and the P1 schema-validation finding before any task workspace is promoted under this scaffold; the P2 items can be tracked as follow-up.
