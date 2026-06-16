#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from prepare_humanize_task import BRIDGE_METADATA_RELPATH, BRIDGE_SCHEMA_VERSION as PREPARE_BRIDGE_SCHEMA_VERSION


OPERATOR_SCHEMA_VERSION = 1
SUPPORTED_PREPARE_BRIDGE_SCHEMA_VERSIONS = frozenset({PREPARE_BRIDGE_SCHEMA_VERSION})
SLASH_COMMAND = "/humanize:start-rlcr-loop docs/plan.md"


class StartError(Exception):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_cli_path(value: str, *, base: Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base / path
    return path.resolve()


def maybe_resolve_cli_path(value: str | None, *, base: Path) -> Path | None:
    if value is None or not value.strip():
        return None
    return resolve_cli_path(value, base=base)


def shell_join(parts: list[str]) -> str:
    return shlex.join([str(part) for part in parts])


def make_var(name: str, value: str | int) -> str:
    return f"{name}={shlex.quote(str(value))}"


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be >= 1")
    return parsed


def non_empty_string(value: str) -> str:
    if not value.strip():
        raise argparse.ArgumentTypeError("must not be empty")
    return value


def normalize_stream(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise StartError(f"missing prepare metadata: {path}") from exc
    except json.JSONDecodeError as exc:
        raise StartError(f"prepare metadata is not valid JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise StartError(f"prepare metadata must be a JSON object: {path}")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def prepare_argv(args: argparse.Namespace, *, root: Path, contract: Path, workspace: Path, target_repo: Path | None) -> list[str]:
    argv = [
        sys.executable,
        str(root / "scripts" / "prepare_humanize_task.py"),
        "--contract",
        str(contract),
        "--workspace",
        str(workspace),
        "--diff-base",
        args.diff_base,
    ]
    if target_repo is not None:
        argv.extend(["--target-repo", str(target_repo)])
    if args.force:
        argv.append("--force")
    if args.overwrite_human_docs:
        argv.append("--overwrite-human-docs")
    if args.strict_prereqs:
        argv.append("--strict-prereqs")
    return argv


def run_prepare(argv: list[str], *, root: Path, print_json: bool, timeout: int) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(argv, cwd=root, text=True, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        result = subprocess.CompletedProcess(
            argv,
            124,
            stdout=normalize_stream(exc.stdout),
            stderr=normalize_stream(exc.stderr) + f"\nCommand timed out after {timeout} seconds.\n",
        )
    stdout_stream = sys.stderr if print_json else sys.stdout
    if result.stdout:
        print(result.stdout, end="", file=stdout_stream)
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result


def build_commands(*, root: Path, workspace: Path, round_number: int, python_executable: str) -> dict[str, Any]:
    import_command = " ".join(
        [
            "make",
            "import-humanize-round",
            make_var("HUMANIZE_WORKSPACE", str(workspace)),
            make_var("ROUND", round_number),
            make_var("PYTHON", python_executable),
        ]
    )
    import_with_loop_dir = " ".join(
        [
            "make",
            "import-humanize-round",
            make_var("HUMANIZE_WORKSPACE", str(workspace)),
            make_var("ROUND", round_number),
            make_var("HUMANIZE_LOOP_DIR", str(workspace / ".humanize" / "rlcr" / "{{TIMESTAMP}}")),
            make_var("PYTHON", python_executable),
        ]
    )
    gate_argv = [
        python_executable,
        str(root / ".agents" / "skills" / "RLInfraWiki" / "scripts" / "validate_review_gate.py"),
        "--workspace",
        str(workspace),
        "--require-review",
    ]
    return {
        "enter_workspace": f"cd {shlex.quote(str(workspace))}",
        "humanize_start": SLASH_COMMAND,
        "import_round": import_command,
        "import_round_with_loop_dir": import_with_loop_dir,
        "review_gate": shell_join(gate_argv),
        "python": python_executable,
    }


def render_operator_doc(
    *,
    created_at: str,
    contract: Path,
    workspace: Path,
    target_repo: Path | None,
    diff_base: str,
    round_number: int,
    bridge_metadata_path: Path,
    operator_metadata_path: Path,
    commands: dict[str, Any],
) -> str:
    target_text = str(target_repo) if target_repo is not None else "not provided"
    return f"""<!-- generated by scripts/start_humanize_task.py at {created_at}; metadata: {operator_metadata_path} -->

# Humanize Task Operator Guide

This workspace was prepared by the IMP-015 start wrapper. It does not start Claude Code and does not run the Humanize plugin.

## Prepared Inputs

- Contract: `{contract}`
- Workspace: `{workspace}`
- Target repo: `{target_text}`
- Diff base: `{diff_base}`
- Round to import: `{round_number}`
- Bridge metadata: `{bridge_metadata_path}`
- Operator metadata: `{operator_metadata_path}`
- Plan: `docs/plan.md`

## 1. Start Humanize In Claude Code

Open Claude Code in the prepared workspace:

```bash
{commands["enter_workspace"]}
```

Run this exact slash command inside Claude Code:

```text
{commands["humanize_start"]}
```

## 2. Import The Humanize Round

After Humanize writes `.humanize/rlcr/<timestamp>/round-{round_number}-summary.md` and `round-{round_number}-review-result.md`, return to the main `rl-infra-design-agents` repository and run:

```bash
{commands["import_round"]}
```

If more than one Humanize loop directory exists and auto-discovery is ambiguous, pass the loop directory explicitly:

```bash
{commands["import_round_with_loop_dir"]}
```

IMP-014 owns this import boundary: it copies Humanize round files into `review_rounds/`, writes `humanize_round_metadata.json`, updates `review_issues.jsonl`, and preserves raw Humanize review output for audit.

## 3. Run The Review Gate

Require an imported review artifact before promotion:

```bash
{commands["review_gate"]}
```

## Provenance And Non-Claims

- Keep `context/context_bundle.md`, `context/context_bundle.json`, and `context/context_sources.yaml` together.
- Preserve RLInfraWiki page IDs and source IDs in plans, validation notes, review packets, and evidence.
- Treat upstream framework behavior as `source-reported` unless local target-repo evidence proves it.
- Do not claim GPU, NCCL, multi-node, throughput, latency, production, or quality verification without local commands, logs, hardware/context, and artifact paths.
- Keep `docs/validation_matrix.md` and `docs/risk_register.md` current as Humanize changes the plan.
"""


def validate_prepare_bridge_schema(bridge_metadata: dict[str, Any], accepted_bridge_schemas: list[int]) -> int:
    if "schema_version" not in bridge_metadata:
        raise StartError(
            "missing prepare bridge schema_version; "
            f"supported: {sorted(SUPPORTED_PREPARE_BRIDGE_SCHEMA_VERSIONS | set(accepted_bridge_schemas))}"
        )
    prepare_bridge_schema_version = bridge_metadata["schema_version"]
    supported_versions = SUPPORTED_PREPARE_BRIDGE_SCHEMA_VERSIONS | set(accepted_bridge_schemas)
    if prepare_bridge_schema_version not in supported_versions:
        raise StartError(
            f"unsupported prepare bridge schema_version: {prepare_bridge_schema_version}; "
            f"supported: {sorted(supported_versions)}"
        )
    return int(prepare_bridge_schema_version)


def build_operator_metadata(
    *,
    created_at: str,
    contract: Path,
    workspace: Path,
    target_repo: Path | None,
    diff_base: str,
    round_number: int,
    bridge_metadata_path: Path,
    operator_doc_path: Path,
    operator_metadata_path: Path,
    bridge_metadata: dict[str, Any],
    prepare_command: list[str],
    commands: dict[str, Any],
    prepare_bridge_schema_version: int,
) -> dict[str, Any]:
    prereq_warnings = bridge_metadata.get("prereq_warnings", [])
    if not isinstance(prereq_warnings, list):
        prereq_warnings = []
    return {
        "schema_version": OPERATOR_SCHEMA_VERSION,
        "created_at": created_at,
        "contract": str(contract),
        "workspace": str(workspace),
        "target_repo": str(target_repo) if target_repo is not None else None,
        "diff_base": diff_base,
        "round": round_number,
        "prepare_metadata_path": str(bridge_metadata_path),
        "bridge_metadata_path": str(bridge_metadata_path),
        "operator_doc": str(operator_doc_path),
        "operator_metadata": str(operator_metadata_path),
        "prepare_bridge_schema_version": prepare_bridge_schema_version,
        "repo_commit": bridge_metadata.get("repo_commit"),
        "rlinfrawiki_commit": bridge_metadata.get("rlinfrawiki_commit"),
        "context_paths": bridge_metadata.get("context_paths", {}),
        "plan_lock": bridge_metadata.get("plan_lock"),
        "prereq_warnings": prereq_warnings,
        "commands": {
            "prepare": shell_join(prepare_command),
            **commands,
        },
    }


def emit_operator_steps(metadata: dict[str, Any], *, stream: Any) -> None:
    commands = metadata["commands"]
    print("Humanize task workspace is ready.", file=stream)
    print(f"Workspace: {metadata['workspace']}", file=stream)
    print(f"Operator guide: {metadata['operator_doc']}", file=stream)
    print(f"Operator metadata: {metadata['operator_metadata']}", file=stream)
    print("", file=stream)
    print("1. In Claude Code:", file=stream)
    print(f"   {commands['enter_workspace']}", file=stream)
    print(f"   {commands['humanize_start']}", file=stream)
    print("", file=stream)
    print("2. After Humanize writes a round, return to this repo and run:", file=stream)
    print(f"   {commands['import_round']}", file=stream)
    print("   If auto-discovery is ambiguous, use:", file=stream)
    print(f"   {commands['import_round_with_loop_dir']}", file=stream)
    print("", file=stream)
    print("3. Run the review gate:", file=stream)
    print(f"   {commands['review_gate']}", file=stream)


def start(args: argparse.Namespace) -> int:
    root = repo_root()
    cwd = Path.cwd()
    contract = resolve_cli_path(args.contract, base=cwd)
    workspace = resolve_cli_path(args.workspace, base=cwd)
    target_repo = maybe_resolve_cli_path(args.target_repo, base=cwd)
    prepare_command = prepare_argv(args, root=root, contract=contract, workspace=workspace, target_repo=target_repo)

    prepare_result = run_prepare(prepare_command, root=root, print_json=args.print_json, timeout=args.prepare_timeout)
    if prepare_result.returncode != 0:
        print("ERROR: stage prepare_humanize_task failed", file=sys.stderr)
        print(f"ERROR: command: {shell_join(prepare_command)}", file=sys.stderr)
        print(f"ERROR: exit code: {prepare_result.returncode}", file=sys.stderr)
        return prepare_result.returncode

    bridge_metadata_path = (workspace / BRIDGE_METADATA_RELPATH).resolve()
    operator_doc_path = (workspace / "humanize_operator.md").resolve()
    operator_metadata_path = (workspace / ".humanize" / "rlinfra_operator.json").resolve()
    try:
        bridge_metadata = load_json(bridge_metadata_path)
        prepare_bridge_schema_version = validate_prepare_bridge_schema(bridge_metadata, args.accept_bridge_schema)
    except StartError as exc:
        print("ERROR: stage operator_metadata failed", file=sys.stderr)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    created_at = now_iso()
    commands = build_commands(root=root, workspace=workspace, round_number=args.round, python_executable=sys.executable)
    operator_doc = render_operator_doc(
        created_at=created_at,
        contract=contract,
        workspace=workspace,
        target_repo=target_repo,
        diff_base=args.diff_base,
        round_number=args.round,
        bridge_metadata_path=bridge_metadata_path,
        operator_metadata_path=operator_metadata_path,
        commands=commands,
    )
    operator_doc_path.write_text(operator_doc, encoding="utf-8")
    metadata = build_operator_metadata(
        created_at=created_at,
        contract=contract,
        workspace=workspace,
        target_repo=target_repo,
        diff_base=args.diff_base,
        round_number=args.round,
        bridge_metadata_path=bridge_metadata_path,
        operator_doc_path=operator_doc_path,
        operator_metadata_path=operator_metadata_path,
        bridge_metadata=bridge_metadata,
        prepare_command=prepare_command,
        commands=commands,
        prepare_bridge_schema_version=prepare_bridge_schema_version,
    )
    write_json(operator_metadata_path, metadata)

    if args.print_json:
        print(json.dumps(metadata, indent=2, sort_keys=True))
        emit_operator_steps(metadata, stream=sys.stderr)
    else:
        emit_operator_steps(metadata, stream=sys.stdout)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare a Humanize-ready RL infra workspace and print the Claude Code/import/gate operator steps."
    )
    parser.add_argument("--contract", required=True, help="Task contract YAML path.")
    parser.add_argument("--workspace", required=True, help="Workspace path to render and prepare.")
    parser.add_argument("--target-repo", default=None, help="Optional target repository path for the Humanize task.")
    parser.add_argument("--diff-base", type=non_empty_string, default="main", help="Diff base branch for target-repo review context.")
    parser.add_argument("--round", type=positive_int, default=1, help="Humanize round number expected for import.")
    parser.add_argument("--force", action="store_true", help="Allow rendering into an existing workspace.")
    parser.add_argument(
        "--overwrite-human-docs",
        action="store_true",
        help="With --force, regenerate scaffolded docs under docs/.",
    )
    parser.add_argument(
        "--strict-prereqs",
        action="store_true",
        help="Pass through to prepare_humanize_task.py and preserve its strict prerequisite failure code.",
    )
    parser.add_argument(
        "--prepare-timeout",
        type=positive_int,
        default=300,
        help="Seconds to wait for prepare_humanize_task.py before failing.",
    )
    parser.add_argument(
        "--accept-bridge-schema",
        type=positive_int,
        action="append",
        default=[],
        help="Explicitly accept an additional prepare bridge schema version.",
    )
    parser.add_argument("--print-json", action="store_true", help="Print operator metadata JSON to stdout.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return start(args)
    except StartError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
