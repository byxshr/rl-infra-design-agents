#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import jsonschema

from _rlinfra import PROJECT_ROOT, append_jsonl, ensure_workspace_dirs, load_jsonl, now_iso, read_task_contract, sha256_file
from render_goal import render_goal

PLANNED_FILES = [
    "task_contract.yaml",
    "docs/goal.md",
    "docs/draft.md",
    "docs/plan.md",
    "docs/architecture.md",
    "docs/interfaces.md",
    "docs/validation_matrix.md",
    "docs/risk_register.md",
    "docs/review.md",
    "docs/goal_status.md",
    "docs/codex_tasks.md",
    ".humanize/rlcr_config.yaml",
    ".humanize/loop_state.json",
    ".humanize/codex_invocations.jsonl",
    ".humanize/claude_iterations.jsonl",
    "review_issues.jsonl",
    "review_waivers.jsonl",
    "candidates.jsonl",
    "goal_versions.jsonl",
    "progress_log.md",
    "metrics.csv",
    "review_rounds/README.md",
    "evidence/README.md",
    "runs/README.md",
    "profile/README.md",
]

LEDGER_FILES = [
    ".humanize/codex_invocations.jsonl",
    ".humanize/claude_iterations.jsonl",
    "review_issues.jsonl",
    "review_waivers.jsonl",
    "candidates.jsonl",
]

METRICS_HEADER = "timestamp,metric,value,unit,notes\n"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_if_missing(path: Path, text: str) -> None:
    if path.exists():
        return
    write(path, text)


def append_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(text)


def last_contract_hash(path: Path) -> str | None:
    for row in reversed(load_jsonl(path)):
        value = row.get("contract_hash")
        if value:
            return str(value)
    return None


def validate_metrics_header(path: Path) -> None:
    if not path.exists():
        return
    first_line = path.read_text(encoding="utf-8").splitlines()
    current = first_line[0] + "\n" if first_line else ""
    if current and current != METRICS_HEADER:
        raise SystemExit(
            f"metrics.csv header mismatch: {path}\n"
            f"expected: {METRICS_HEADER.strip()}\n"
            f"found: {current.strip()}"
        )


def validate_contract_schema(contract: dict, contract_path: Path) -> None:
    schema_path = PROJECT_ROOT / "schemas" / "task_contract.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(contract), key=lambda err: list(err.path))
    if errors:
        details = "\n".join(f"- {'/'.join(str(p) for p in err.path) or '<root>'}: {err.message}" for err in errors)
        raise SystemExit(f"task contract failed schema validation: {contract_path}\n{details}")


def render_bundle(contract_path: Path, output: Path, preserve_ledgers: bool = False, preserve_human_docs: bool = False) -> None:
    contract = read_task_contract(contract_path)
    validate_contract_schema(contract, contract_path)
    ensure_workspace_dirs(output)
    if preserve_ledgers:
        validate_metrics_header(output / "metrics.csv")
    shutil.copyfile(contract_path, output / "task_contract.yaml")
    doc_writer = write_if_missing if preserve_human_docs else write
    doc_writer(output / "docs" / "goal.md", render_goal(contract))
    queries = contract.get("required_wiki_queries", [])
    doc_writer(output / "docs" / "draft.md", "# Draft\n\n## Task contract summary\n\n" + contract.get("objective", "") + "\n\n## RLInfraWiki queries run\n\n| query | top pages | source IDs | notes |\n|---|---|---|---|\n" + "".join(f"| {q} | pending | pending | run query.py |\n" for q in queries) + "\n## Candidate directions\n\n### Candidate A\n\nPrimary path.\n\n### Candidate B\n\nFallback path.\n")
    doc_writer(output / "docs" / "plan.md", f"""# Executable Plan

## Objective

{contract.get('objective', '')}

## Non-goals

- Do not implement a new RL framework.
- Do not make unverified performance claims.

## Chosen architecture

Pending after RLInfraWiki query and human refinement.

## Alternatives considered

- Primary framework path.
- Reference framework fallback.

## Dataflow

prompt source -> rollout request -> inference backend -> tool/env interaction -> reward/verifier -> trajectory object -> data buffer -> trainer batch -> gradient update -> weight sync -> rollout version update -> metrics/traces

## APIs and interfaces

Document trainer, rollout, reward, environment, and evidence interfaces.

## State and storage

Track task config, policy version, weight version, evidence path, and review issue state.

## Failure modes

Version mismatch, partial weight update, delayed reward, nondeterminism, and rollback gap.

## Observability

Metrics, traces, logs, and validation evidence are required before review.

## Implementation steps

### Step 1

- Files: docs/*
- Changes: finalize design and validation matrix
- Tests: run validation commands
- Acceptance: criteria mapped to evidence

## Validation commands

""" + "".join(f"- `{cmd}`\n" for cmd in contract.get("validation_commands", [])) + """
## Rollback plan

Revert candidate changes, restore prior plan lock, and mark unresolved review issues open.

## Promotion criteria

""" + "".join(f"- {item}\n" for item in contract.get("promotion_criteria", [])) + """
## Review checklist

- Goal alignment
- Source provenance
- Validation evidence
- Failure modes and rollback
- Open review issues and waivers
""")
    for name, title in [("architecture.md", "Architecture"), ("interfaces.md", "Interfaces"), ("review.md", "Review"), ("codex_tasks.md", "Codex Tasks")]:
        doc_writer(output / "docs" / name, f"# {title}\n\nPending RLCR iteration.\n")
    doc_writer(output / "docs" / "validation_matrix.md", "# Validation Matrix\n\n| requirement | validation command | expected result | evidence path | status |\n|---|---|---|---|---|\n" + "".join(f"| contract validation | `{cmd}` | exits 0 | evidence/{i:02d}-validation.log | pending |\n" for i, cmd in enumerate(contract.get("validation_commands", []), 1)))
    doc_writer(output / "docs" / "risk_register.md", "# Risk Register\n\n| risk | severity | mitigation | status |\n|---|---|---|---|\n| version mismatch | P1 | add weight_version_id validation | open |\n| provenance gap | P1 | cite RLInfraWiki source IDs | open |\n")
    doc_writer(output / "docs" / "goal_status.md", f"# Goal Status\n\n- status: active\n- updated_at: {now_iso()}\n")
    write(output / ".humanize" / "rlcr_config.yaml", f"""mode: {contract.get('review_mode', 'humanize-compatible-rlcr')}
builder: {contract.get('builder', 'claude')}
reviewer: {contract.get('reviewer', 'codex')}
human_architect_required_for:
  - goal_amendment
  - P1_waiver
  - promotion_with_unresolved_P2
plan_lock:
  enabled: true
  file: .humanize/plan.lock.md
review:
  blocker_severities: [P0, P1]
  waiver_allowed_for: [P2]
  backlog_allowed_for: [P3]
validation:
  require_before_review: true
  require_after_fix: true
""")
    if not preserve_ledgers:
        write(output / ".humanize" / "loop_state.json", json.dumps({"status": "initialized", "round": 0, "updated_at": now_iso()}, indent=2) + "\n")
    else:
        write_if_missing(output / ".humanize" / "loop_state.json", json.dumps({"status": "initialized", "round": 0, "updated_at": now_iso()}, indent=2) + "\n")
    for rel in LEDGER_FILES:
        target = output / rel
        if preserve_ledgers:
            write_if_missing(target, "")
        else:
            write(target, "")
    rendered_at = now_iso()
    contract_hash = sha256_file(contract_path)
    goal_version = {"goal_id": contract.get("task_name"), "status": "active", "contract_hash": contract_hash, "created_at": rendered_at}
    goal_versions_path = output / "goal_versions.jsonl"
    prior_contract_hash = last_contract_hash(goal_versions_path) if goal_versions_path.exists() else None
    contract_changed = prior_contract_hash is not None and prior_contract_hash != contract_hash
    if preserve_human_docs and contract_changed:
        print(
            "WARN: contract changed; scaffolded docs under docs/ were preserved and may be stale. "
            "Re-run with --overwrite-human-docs to regenerate them, or hand-edit validation_matrix.md "
            "and plan.md to reflect the new contract.",
            file=sys.stderr,
        )
    goal_history_exists = goal_versions_path.exists() and bool(load_jsonl(goal_versions_path))
    if preserve_ledgers and contract_changed:
        append_jsonl(goal_versions_path, [goal_version])
    elif preserve_ledgers and goal_history_exists and prior_contract_hash is None:
        append_jsonl(goal_versions_path, [goal_version])
    elif not preserve_ledgers or not goal_versions_path.exists() or prior_contract_hash is None:
        write(goal_versions_path, json.dumps(goal_version) + "\n")
    progress_path = output / "progress_log.md"
    progress_entry = f"- {rendered_at}: workspace rendered from `{contract_path.name}`.\n"
    amended_progress_entry = f"- {rendered_at}: contract amended -> workspace re-rendered from `{contract_path.name}`.\n"
    if preserve_ledgers and progress_path.exists() and contract_changed:
        append_text(progress_path, amended_progress_entry)
    elif preserve_ledgers and progress_path.exists() and prior_contract_hash is None:
        append_text(progress_path, progress_entry)
    elif preserve_ledgers and progress_path.exists():
        pass
    elif preserve_ledgers and not progress_path.exists():
        write(progress_path, f"# Progress Log\n\n{progress_entry}")
    else:
        write(progress_path, f"# Progress Log\n\n{progress_entry}")
    metrics_path = output / "metrics.csv"
    if preserve_ledgers:
        if not metrics_path.exists() or not metrics_path.read_text(encoding="utf-8"):
            write(metrics_path, METRICS_HEADER)
    else:
        write(metrics_path, METRICS_HEADER)
    write(output / "review_rounds" / "README.md", "# Review Rounds\n\nEach round stores review_packet.md, codex_review.md, parsed_issues.jsonl, claude_response.md, and validation_after_fix.md.\n")
    write(output / "evidence" / "README.md", "# Evidence\n\nStore validation logs, command output, screenshots, traces, and local reproduction evidence here.\n")
    write(output / "runs" / "README.md", "# Runs\n\nTask-specific runs live here when the external workspace permits it.\n")
    write(output / "profile" / "README.md", "# Profile\n\nProfiling notes and summaries live here; large logs should stay outside this repository.\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a complete RL infra task workspace")
    parser.add_argument("--contract", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--force", action="store_true", help="Allow refreshing scaffold files in an existing non-empty workspace")
    parser.add_argument("--reset-ledgers", action="store_true", help="With --force, also reset review ledgers, loop state, metrics, and progress logs")
    parser.add_argument("--overwrite-human-docs", action="store_true", help="With --force, also overwrite scaffolded docs under docs/")
    args = parser.parse_args()
    output = Path(args.output)
    existing_nonempty = output.exists() and any(output.iterdir())
    if args.reset_ledgers and not args.force:
        print("ERROR: --reset-ledgers requires --force")
        return 1
    if args.overwrite_human_docs and not args.force:
        print("ERROR: --overwrite-human-docs requires --force")
        return 1
    if existing_nonempty and not args.force:
        print(f"ERROR: refusing to render into non-empty workspace: {output}")
        print("Pass --force to refresh scaffold-managed files. Ledgers and human-edited docs are preserved unless explicit reset flags are used. Planned writes:")
        for rel in PLANNED_FILES:
            print(f"  - {rel}")
        return 1
    output.mkdir(parents=True, exist_ok=True)
    render_bundle(
        Path(args.contract),
        output,
        preserve_ledgers=existing_nonempty and not args.reset_ledgers,
        preserve_human_docs=existing_nonempty and not args.overwrite_human_docs,
    )
    print(f"rendered task workspace at {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
