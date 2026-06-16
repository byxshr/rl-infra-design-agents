#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CONTEXT_FILES = {
    "markdown": "context/context_bundle.md",
    "json": "context/context_bundle.json",
    "sources": "context/context_sources.yaml",
}
BRIDGE_SCHEMA_VERSION = 1
BRIDGE_METADATA_RELPATH = Path(".humanize") / "rlinfra_bridge.json"
MAX_COMMAND_OUTPUT_CHARS = 4096
STRICT_PREREQ_EXIT_CODE = 2


class BridgeError(Exception):
    pass


@dataclass
class CommandFailure(Exception):
    record: dict[str, Any]

    def __str__(self) -> str:
        command = " ".join(str(part) for part in self.record["argv"])
        return f"{self.record['name']} failed with exit {self.record['returncode']}: {command}"


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


def normalize_stream(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def truncate_stream(text: str) -> tuple[str, bool]:
    if len(text) <= MAX_COMMAND_OUTPUT_CHARS:
        return text, False
    marker = f"\n... truncated to {MAX_COMMAND_OUTPUT_CHARS} characters by prepare_humanize_task.py ...\n"
    return text[:MAX_COMMAND_OUTPUT_CHARS] + marker, True


def run_command(
    name: str,
    argv: list[str],
    *,
    cwd: Path,
    commands_run: list[dict[str, Any]],
    timeout: int,
) -> None:
    timed_out = False
    try:
        result = subprocess.run(argv, cwd=cwd, text=True, capture_output=True, timeout=timeout)
        returncode = result.returncode
        stdout = result.stdout
        stderr = result.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        returncode = 124
        stdout = normalize_stream(exc.stdout)
        stderr = normalize_stream(exc.stderr)
        stderr += f"\nCommand timed out after {timeout} seconds.\n"
    stored_stdout, stdout_truncated = truncate_stream(stdout)
    stored_stderr, stderr_truncated = truncate_stream(stderr)
    record = {
        "name": name,
        "argv": [str(part) for part in argv],
        "cwd": str(cwd),
        "returncode": returncode,
        "stdout": stored_stdout,
        "stderr": stored_stderr,
        "stdout_truncated": stdout_truncated,
        "stderr_truncated": stderr_truncated,
        "timeout_seconds": timeout,
        "timed_out": timed_out,
    }
    commands_run.append(record)
    if stdout:
        print(stdout, end="")
    if stderr:
        print(stderr, end="", file=sys.stderr)
    if returncode != 0:
        raise CommandFailure(record)


def find_humanize_roots(repo: Path, env: dict[str, str]) -> tuple[list[Path], list[str]]:
    roots: list[Path] = []
    warnings: list[str] = []

    sibling = (repo.parent / "humanize").resolve()
    if sibling.exists():
        roots.append(sibling)

    env_root = env.get("HUMANIZE_ROOT")
    if env_root:
        resolved = Path(env_root).expanduser()
        if not resolved.is_absolute():
            resolved = (Path.cwd() / resolved).resolve()
        else:
            resolved = resolved.resolve()
        if resolved.exists():
            if resolved not in roots:
                roots.append(resolved)
        else:
            warnings.append(f"HUMANIZE_ROOT is set but does not exist: {resolved}")

    if not roots:
        warnings.append("Humanize root not found; checked sibling ../humanize and HUMANIZE_ROOT.")
    return roots, warnings


def find_instruction_files(repo: Path, humanize_roots: list[Path]) -> tuple[list[Path], list[Path], list[str]]:
    humanize_candidates: list[Path] = []
    for root in humanize_roots:
        humanize_candidates.extend(
            [
                root / ".claude" / "CLAUDE.md",
                root / "CLAUDE.md",
                root / "docs" / "install-for-claude.md",
                root / "skills" / "humanize-rlcr" / "SKILL.md",
                root / "skills" / "humanize" / "SKILL.md",
            ]
        )
    repo_candidates = [
        repo / "integrations" / "humanize" / "README.md",
        repo / "docs" / "humanize-compatible-rlcr.md",
        repo / "CLAUDE.md",
    ]
    humanize_found = [path.resolve() for path in humanize_candidates if path.exists()]
    repo_found = [path.resolve() for path in repo_candidates if path.exists()]
    warnings = []
    if not humanize_found:
        warnings.append("Humanize-side Claude Code/Humanize instruction files were not found.")
    return humanize_found, repo_found, warnings


def detect_prerequisites(
    repo: Path,
    *,
    env: dict[str, str] | None = None,
    path: str | None = None,
) -> dict[str, Any]:
    env = dict(os.environ if env is None else env)
    humanize_roots, warnings = find_humanize_roots(repo, env)
    humanize_instruction_files, repo_instruction_files, instruction_warnings = find_instruction_files(repo, humanize_roots)
    warnings.extend(instruction_warnings)

    codex_path = shutil.which("codex", path=path if path is not None else env.get("PATH"))
    if codex_path is None:
        warnings.append("codex CLI not found on PATH; Codex review automation may be unavailable.")

    return {
        "humanize_roots": [str(path) for path in humanize_roots],
        "codex_cli": codex_path,
        "humanize_instruction_files": [str(path) for path in humanize_instruction_files],
        "repository_instruction_files": [str(path) for path in repo_instruction_files],
        "instruction_files": [str(path) for path in [*humanize_instruction_files, *repo_instruction_files]],
        "warnings": warnings,
    }


def run_git(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, timeout=30)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def git_rev_parse(path: Path, ref: str = "HEAD") -> str | None:
    result = run_git(["rev-parse", ref], cwd=path)
    if result is None or result.returncode != 0:
        return None
    return result.stdout.strip() or None


def gitlink_commit(repo: Path, rel_path: str) -> str | None:
    result = run_git(["ls-tree", "HEAD", rel_path], cwd=repo)
    if result is None or result.returncode != 0:
        return None
    parts = result.stdout.strip().split()
    if len(parts) >= 3 and parts[1] == "commit":
        return parts[2]
    return None


def target_repo_status(target_repo: Path | None, diff_base: str) -> tuple[dict[str, Any], list[str]]:
    if target_repo is None:
        return {"provided": False}, []

    warnings: list[str] = []
    status: dict[str, Any] = {
        "provided": True,
        "path": str(target_repo),
        "exists": target_repo.exists(),
        "is_git_repo": False,
        "diff_base": diff_base,
        "diff_base_resolves": False,
    }
    if not target_repo.exists():
        warnings.append(f"target repo does not exist: {target_repo}")
        return status, warnings
    if not target_repo.is_dir():
        warnings.append(f"target repo is not a directory: {target_repo}")
        return status, warnings

    git_dir = run_git(["rev-parse", "--git-dir"], cwd=target_repo)
    if git_dir is None:
        warnings.append(f"target repo could not be validated because git is unavailable: {target_repo}")
        return status, warnings
    if git_dir.returncode != 0:
        warnings.append(f"target repo is not a git repository: {target_repo}")
        return status, warnings

    status["is_git_repo"] = True
    status["git_dir"] = git_dir.stdout.strip()
    head = git_rev_parse(target_repo)
    if head:
        status["head_commit"] = head

    diff_ref = run_git(["rev-parse", "--verify", f"{diff_base}^{{commit}}"], cwd=target_repo)
    if diff_ref is None:
        warnings.append(f"target repo diff base could not be validated because git is unavailable: {diff_base}")
    elif diff_ref.returncode == 0:
        status["diff_base_resolves"] = True
        status["diff_base_commit"] = diff_ref.stdout.strip()
    else:
        warnings.append(f"target repo diff base does not resolve: {diff_base}")
    return status, warnings


def require_existing_files(workspace: Path) -> dict[str, str]:
    paths = {key: workspace / rel for key, rel in CONTEXT_FILES.items()}
    missing = [path for path in paths.values() if not path.exists()]
    if missing:
        joined = "\n".join(f"- {path}" for path in missing)
        raise BridgeError(f"missing required context artifact(s):\n{joined}")
    return {key: str(path.resolve()) for key, path in paths.items()}


def render_humanize_start(
    *,
    prepared_at: str,
    workspace: Path,
    contract: Path,
    target_repo: Path | None,
    diff_base: str,
    context_paths: dict[str, str],
    plan_lock: Path,
    metadata_path: Path,
    repo_commit: str | None,
    rlinfrawiki_commit: str | None,
) -> str:
    target_text = str(target_repo) if target_repo is not None else "not provided"
    repo_commit_text = repo_commit or "unknown"
    rlinfrawiki_commit_text = rlinfrawiki_commit or "unknown"
    return f"""<!-- generated by scripts/prepare_humanize_task.py at {prepared_at}; metadata: {metadata_path} -->

# Humanize RLCR Start

This workspace is prepared for Humanize-compatible RLCR. It does not auto-launch Claude Code.

## Prepared Inputs

- Workspace path: `{workspace}`
- Contract path: `{contract}`
- Target repo: `{target_text}`
- Diff base: `{diff_base}`
- Plan: `docs/plan.md`
- Plan lock: `{plan_lock}`
- Context bundle: `{context_paths["markdown"]}`
- Context JSON: `{context_paths["json"]}`
- Context sources: `{context_paths["sources"]}`
- Main repo commit: `{repo_commit_text}`
- Pinned RLInfraWiki commit: `{rlinfrawiki_commit_text}`
- Bridge metadata: `{metadata_path}`

## Start Command

First open Claude Code and enter the prepared workspace:

```bash
cd {workspace}
```

Then run this exact slash command inside Claude Code:

```text
/humanize:start-rlcr-loop docs/plan.md
```

## RLInfraWiki Provenance Rules

- Keep `context/context_bundle.md`, `context/context_bundle.json`, and `context/context_sources.yaml` together.
- Preserve RLInfraWiki page IDs and source IDs in `docs/plan.md`, review packets, validation notes, and evidence.
- Treat upstream behavior as `source-reported` unless local target-repo evidence proves it.
- Do not claim GPU, NCCL, multi-node, throughput, latency, production, or quality verification without local commands, logs, hardware/context, and artifact paths.

## Validation And Risk Rules

- Run the commands listed in `docs/validation_matrix.md` before requesting Codex review.
- Keep `docs/risk_register.md` current when Humanize changes the implementation plan.
- Record validation output under `evidence/` or another explicit artifact path.
- Keep review-gate semantics intact: unresolved P0/P1 issues block promotion, P2 requires an approved waiver, and missing provenance remains a blocker.

IMP-014 is still the boundary for importing Humanize `.humanize/rlcr/...` rounds back into this repository's review ledger.
"""


def write_metadata(path: Path, metadata: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def prepare(args: argparse.Namespace) -> int:
    root = repo_root()
    cwd = Path.cwd()
    contract = resolve_cli_path(args.contract, base=cwd)
    workspace = resolve_cli_path(args.workspace, base=cwd)
    target_repo = maybe_resolve_cli_path(args.target_repo, base=cwd)
    wiki_scripts = root / ".agents" / "skills" / "RLInfraWiki" / "scripts"
    render_script = wiki_scripts / "render_task_bundle.py"
    validate_context_script = wiki_scripts / "validate_context_bundle.py"
    lock_plan_script = wiki_scripts / "lock_plan.py"
    review_gate_script = wiki_scripts / "validate_review_gate.py"
    commands_run: list[dict[str, Any]] = []
    prepared_at = now_iso()
    git_cli_available = shutil.which("git") is not None
    repo_commit = git_rev_parse(root)
    rlinfrawiki_root = (root / ".agents" / "skills" / "RLInfraWiki").resolve()
    rlinfrawiki_commit = gitlink_commit(root, ".agents/skills/RLInfraWiki") or git_rev_parse(rlinfrawiki_root)

    if args.overwrite_human_docs and not args.force:
        raise BridgeError("--overwrite-human-docs requires --force")
    if not contract.exists():
        raise BridgeError(f"missing contract: {contract}")
    for script in [render_script, validate_context_script, lock_plan_script, review_gate_script]:
        if not script.exists():
            raise BridgeError(f"missing pinned RLInfraWiki script: {script}")

    render_argv = [
        sys.executable,
        str(render_script),
        "--contract",
        str(contract),
        "--output",
        str(workspace),
    ]
    if args.force:
        render_argv.append("--force")
    if args.overwrite_human_docs:
        render_argv.append("--overwrite-human-docs")
    run_command("render_task_bundle", render_argv, cwd=root, commands_run=commands_run, timeout=args.command_timeout)

    context_paths = require_existing_files(workspace)
    run_command(
        "validate_context_bundle",
        [sys.executable, str(validate_context_script), context_paths["markdown"]],
        cwd=root,
        commands_run=commands_run,
        timeout=args.command_timeout,
    )
    run_command(
        "lock_plan",
        [sys.executable, str(lock_plan_script), "--workspace", str(workspace)],
        cwd=root,
        commands_run=commands_run,
        timeout=args.command_timeout,
    )
    plan_lock = (workspace / ".humanize" / "plan.lock.md").resolve()
    if not plan_lock.exists():
        raise BridgeError(f"missing plan lock after lock_plan.py: {plan_lock}")
    run_command(
        "validate_review_gate",
        [sys.executable, str(review_gate_script), "--workspace", str(workspace)],
        cwd=root,
        commands_run=commands_run,
        timeout=args.command_timeout,
    )

    prereqs = detect_prerequisites(root)
    if not git_cli_available:
        prereqs["warnings"].append("git CLI not found on PATH; bridge cannot record commit identity.")
    else:
        if repo_commit is None:
            prereqs["warnings"].append("main repository commit identity could not be recorded.")
        if rlinfrawiki_commit is None:
            prereqs["warnings"].append("pinned RLInfraWiki commit identity could not be recorded.")
    target_status, target_warnings = target_repo_status(target_repo, args.diff_base)
    prereqs["warnings"].extend(target_warnings)
    for warning in prereqs["warnings"]:
        print(f"WARN: {warning}")

    metadata_path = (workspace / BRIDGE_METADATA_RELPATH).resolve()
    humanize_start_path = (workspace / "humanize_start.md").resolve()
    humanize_start = render_humanize_start(
        prepared_at=prepared_at,
        workspace=workspace,
        contract=contract,
        target_repo=target_repo,
        diff_base=args.diff_base,
        context_paths=context_paths,
        plan_lock=plan_lock,
        metadata_path=metadata_path,
        repo_commit=repo_commit,
        rlinfrawiki_commit=rlinfrawiki_commit,
    )
    humanize_start_path.write_text(humanize_start, encoding="utf-8")

    metadata = {
        "schema_version": BRIDGE_SCHEMA_VERSION,
        "prepared_at": prepared_at,
        "repo_root": str(root),
        "repo_commit": repo_commit,
        "rlinfrawiki_root": str(rlinfrawiki_root),
        "rlinfrawiki_commit": rlinfrawiki_commit,
        "contract": str(contract),
        "workspace": str(workspace),
        "target_repo": str(target_repo) if target_repo is not None else None,
        "target_repo_status": target_status,
        "diff_base": args.diff_base,
        "context_paths": context_paths,
        "plan_lock": str(plan_lock),
        "humanize_start": str(humanize_start_path),
        "prerequisites": prereqs,
        "prereq_warnings": prereqs["warnings"],
        "commands_run": commands_run,
        "next_command": "/humanize:start-rlcr-loop docs/plan.md",
    }
    write_metadata(metadata_path, metadata)

    print(f"Humanize-ready workspace prepared: {workspace}")
    print(f"Start guide: {humanize_start_path}")
    print(f"Metadata: {metadata_path}")
    print("Next in Claude Code:")
    print(f"  cd {workspace}")
    print("  /humanize:start-rlcr-loop docs/plan.md")

    if args.strict_prereqs and prereqs["warnings"]:
        print("ERROR: --strict-prereqs requested and prerequisite warnings were found:", file=sys.stderr)
        for warning in prereqs["warnings"]:
            print(f"ERROR: {warning}", file=sys.stderr)
        return STRICT_PREREQ_EXIT_CODE
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare an RL infra task workspace for Humanize RLCR. Exit code 0 means prepared, "
            "1 means render/validation/bridge failure, and 2 means the workspace was prepared but "
            "--strict-prereqs found missing prerequisites."
        )
    )
    parser.add_argument("--contract", required=True, help="Task contract YAML path.")
    parser.add_argument("--workspace", required=True, help="Workspace path to render and prepare.")
    parser.add_argument("--target-repo", default=None, help="Optional target repository path for the Humanize task.")
    parser.add_argument("--diff-base", default="main", help="Diff base branch for target-repo review context.")
    parser.add_argument("--force", action="store_true", help="Allow rendering into an existing workspace.")
    parser.add_argument(
        "--overwrite-human-docs",
        action="store_true",
        help="With --force, regenerate scaffolded docs under docs/.",
    )
    parser.add_argument(
        "--strict-prereqs",
        action="store_true",
        help="Fail when Humanize/Codex prerequisites are missing instead of recording warnings.",
    )
    parser.add_argument(
        "--command-timeout",
        type=int,
        default=300,
        help="Seconds to allow each pinned RLInfraWiki subprocess before failing.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return prepare(args)
    except CommandFailure as exc:
        record = exc.record
        command = " ".join(str(part) for part in record["argv"])
        print(f"ERROR: command failed: {command}", file=sys.stderr)
        print(f"ERROR: exit code: {record['returncode']}", file=sys.stderr)
        return int(record["returncode"] or 1)
    except BridgeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
