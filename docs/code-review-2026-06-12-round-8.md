# Code Review — Round 8 — rl-infra-design-agents

- Date: 2026-06-12
- Scope: triaged fix from `docs/code-review-2026-06-12-round-7.md` plus retrospective scan of `--overwrite-human-docs` semantics
- Reference: `docs/ai-agent-code-review-reference.md` §"Review Triage Notes"
- Reviewer posture: independent gatekeeper

## Validation Run

| Command | Result |
|---|---|
| `python .agents/skills/RLInfraWiki/scripts/validate.py` | PASS |
| `python .agents/skills/RLInfraWiki/scripts/generate_indices.py --check` | PASS |
| `pytest -q` | PASS — 33 passed (was 32) |
| Lock plan whose body contains `- plan_sha256: <example>` bullets → gate | PASS — gate exits 0 (no false drift) |
| Then overwrite `docs/plan.md` with `# different plan` → gate | PASS — gate fails with `plan.lock.md plan_sha256 does not match docs/plan.md` |

Baseline: 11 test files, 33 tests, all green. Round-7 added `test_review_gate_plan_lock_ignores_embedded_plan_hash_examples`.

## Round-7 Triage

| Round-7 finding | Status | Notes |
|---|---|---|
| P1 — `plan_lock_hashes()` reads beyond the `---` header into the plan body | **FIXED** | `validate_review_gate.py:29-30` adds `if text == "---": break`. The new test seeds a plan with example hash bullets in its body, locks, and asserts the gate passes — drift is still detected on real edits. |

The round-7 fix is clean. However, while doing the retrospective scan the team requested, one P1-class issue surfaced that survived all seven prior rounds: `--overwrite-human-docs` only protects 2 of 8 human-editable docs.

## New / Remaining Findings

### P1 (unfixed): `--force` silently overwrites human-edited `validation_matrix.md`, `risk_register.md`, and four other workspace docs; `--overwrite-human-docs` only protects `goal.md` and `plan.md`

- File/path: `.agents/skills/RLInfraWiki/scripts/render_task_bundle.py:108-183` (and the help text at line 265)
- Evidence:
  ```python
  doc_writer = write_if_missing if preserve_human_docs else write
  doc_writer(output / "docs" / "goal.md", render_goal(contract))     # ← protected
  ...
  write(output / "docs" / "draft.md", ...)                            # ← always written
  doc_writer(output / "docs" / "plan.md", ...)                        # ← protected
  ...
  for name, title in [("architecture.md", "Architecture"),
                      ("interfaces.md", "Interfaces"),
                      ("review.md", "Review"),
                      ("codex_tasks.md", "Codex Tasks")]:
      write(output / "docs" / name, f"# {title}\n\nPending RLCR iteration.\n")  # ← always written
  write(output / "docs" / "validation_matrix.md", ...)               # ← always written
  write(output / "docs" / "risk_register.md", ...)                   # ← always written
  write(output / "docs" / "goal_status.md", ...)                     # ← always written
  ```
  Eight `docs/*.md` files take the bare `write()` path — `draft.md`, `architecture.md`, `interfaces.md`, `review.md`, `codex_tasks.md`, `validation_matrix.md`, `risk_register.md`, `goal_status.md`. The user-facing message printed on a non-empty workspace at line 265 says:
  > `Pass --force to refresh scaffold-managed files. Ledgers and human-edited docs are preserved unless explicit reset flags are used. Planned writes:`

  …but the promise only holds for `goal.md` and `plan.md`. The other six (or seven, counting `goal_status.md`) are silently overwritten on every `--force` run regardless of `--overwrite-human-docs`.

- Reproducer (verified empirically):
  ```bash
  render_task_bundle.py --contract slime-weight-sync.yaml --output WS
  for f in architecture.md interfaces.md review.md codex_tasks.md validation_matrix.md risk_register.md; do
      echo "# Substantive $f\nReal content" > WS/docs/$f
  done
  render_task_bundle.py --contract slime-weight-sync.yaml --output WS --force
  cat WS/docs/architecture.md
  # → "# Architecture\n\nPending RLCR iteration.\n"   (substantive content gone)
  cat WS/docs/validation_matrix.md
  # → "# Validation Matrix\n\n| requirement | ... | pending |\n"   (replaced with template)
  ```
- Why it blocks: Reference §"Blocking Review Checks" lists three triggers that all apply:
  - "Silently changes objective, acceptance criteria, non-goals, or review gate behavior" — `validation_matrix.md` and `risk_register.md` are exactly the artifacts that hold acceptance criteria evidence; reverting them silently changes the workspace's gate state.
  - "Lets a candidate promote without required validation evidence" — once `validation_matrix.md` is reset to the template (every row `pending`), the workspace looks like a fresh scaffold to a reviewer.
  - "Causes `render_task_bundle.py` … to produce incomplete RLCR workspaces" — the workspace contract in §"Task Workspace Contract" lists all six docs as first-class deliverables.

  Worse, `render_rlcr_context.py:69-75` excerpts both `validation_matrix.md` and `risk_register.md` directly into the review packet. After `--force` resets them to the template, Codex reviews against placeholders instead of the real evidence and risks. AGENTS.md "Done means" requires "Validation evidence is recorded with command, expected result, evidence path, and status" — that record lives in `validation_matrix.md`.

  This is the same class of bug the round-2 P0 #3 fix addressed for `goal.md`/`plan.md`/`goal_versions.jsonl`; the `--overwrite-human-docs` split was scoped too narrowly and the gap was never re-examined in rounds 3-7. `test_render_task_bundle_force_flag_guards` only asserts `goal.md` survival, so the regression is invisible to CI.

- Suggested fix: route the affected docs through `doc_writer` so they participate in the `--overwrite-human-docs` interlock:
  ```python
  doc_writer(output / "docs" / "draft.md", ...)
  for name, title in [("architecture.md", ...), ("interfaces.md", ...), ("review.md", ...), ("codex_tasks.md", ...)]:
      doc_writer(output / "docs" / name, f"# {title}\n\nPending RLCR iteration.\n")
  doc_writer(output / "docs" / "validation_matrix.md", ...)
  doc_writer(output / "docs" / "risk_register.md", ...)
  doc_writer(output / "docs" / "goal_status.md", ...)
  ```
  Add a regression test that writes substantive content into all eight files, runs `--force`, and asserts content is preserved; runs `--force --overwrite-human-docs` and asserts content is replaced. Update the help text to truthfully list the files governed by `--overwrite-human-docs` (or rename the flag to make the scope obvious — e.g., `--overwrite-scaffolded-docs`).

  If the team intentionally treats `architecture.md` / `interfaces.md` / `review.md` / `codex_tasks.md` as scaffold-only (Builder fills them in by editing `.humanize/...` instead), say so explicitly: change the line-265 message to "human-edited `goal.md` and `plan.md` are preserved" and document the convention in CLAUDE.md. The current implicit "preserved" claim does not match the code.

## Open Questions

- Which of the eight docs are "human-edited" (Builder/architect content) vs "scaffold-only" (always regenerated from contract)? `validation_matrix.md` and `risk_register.md` are clearly human-edited because their content is task-specific evidence. `goal_status.md` is scaffold-only (status flag + timestamp). The other five are ambiguous and the codebase doesn't say. The fix should pick one of: (a) protect all of them under `--overwrite-human-docs`, (b) split the flag (`--overwrite-scaffolded-docs` covers all eight by default; `--overwrite-evidence-docs` covers `validation_matrix.md`/`risk_register.md`), or (c) keep two-flag interlock and just expand the protected set to include `validation_matrix.md`/`risk_register.md` (the minimum needed to close the gate-bypass).
- After this fix, are there *any* P1 paths remaining? My retrospective scan checked schemas (all 12 source manifests, 33 wiki pages, 5 contracts validate cleanly under their schemas), render-stability across re-runs (byte-stable), round-2 packet generation (resolved issues correctly suppressed), and parse→append→gate schema enforcement (consistent). I did not find any other material gap. The repository may be ready to close the review series after this finding.
- The full set of "rare scripts" (`refresh_sources.py`, `ingest_github_repo.py`, `ingest_docs.py`, `grep_wiki.py`, `check_provenance.py`, `validate_goal.py`, `render_claim_report.py`, `summarize_rlcr.py`, `build_candidate_ledger.py`, `render_goal.py`) was scanned without finding workflow-affecting bugs — but they are also not exercised by CI, so latent issues are possible. Worth a separate "tools sweep" if the team wants total confidence.

## Summary

The round-7 triage closed the lock-parser body-override bug cleanly (33 tests pass, was 32). One residual P1 surfaced from the retrospective scan:

- **P1 (unfixed)** `render_task_bundle.py --force` silently overwrites human-edited `validation_matrix.md` and `risk_register.md` (plus four other docs), even though the printed help message promises "human-edited docs are preserved." The `--overwrite-human-docs` interlock (added in round 3 as the round-2 P0 fix) only covers `goal.md` and `plan.md`. After `--force`, `render_rlcr_context.py` excerpts the freshly-reset templates into the review packet, so Codex sees placeholder evidence; `validate_review_gate.py` does not detect this because nothing hashes the validation matrix. Verified empirically by writing substantive content into all six docs, running `--force`, and observing them revert to the scaffold template.

This is the same severity class as the round-2 P0 #3 (`--force` silently overwrites human-edited docs) — the original fix solved it for the two highest-profile docs and missed the rest. Recommend closing the gap with a one-line-per-doc change to `doc_writer`, plus a regression test covering all eight docs.

After this fix, the retrospective scan found no other material gap across the seven rounds of accumulated changes.
