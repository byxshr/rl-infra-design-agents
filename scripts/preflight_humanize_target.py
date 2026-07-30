#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


PREFLIGHT_SCHEMA_VERSION = 1
HYGIENE_FAILURE_EXIT_CODE = 3
SAFE_PLAN_PATH_RE = re.compile(r"^[A-Za-z0-9._/-]+$")
PLAN_LOCK_HASH_RE = re.compile(r"^- plan_sha256: ([0-9a-f]{64})$", re.MULTILINE)
MAX_DIRTY_ERROR_ENTRIES = 20


class PreflightFailure(Exception):
    def __init__(self, message: str, *, code: str = "preflight_error"):
        super().__init__(message)
        self.code = code


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_cli_path(value: str, *, base: Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base / path
    return path.resolve()


def run_git(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, timeout=30)
    except FileNotFoundError as exc:
        raise PreflightFailure("git CLI is not available", code="git_unavailable") from exc
    except subprocess.TimeoutExpired as exc:
        raise PreflightFailure(f"git command timed out: git {' '.join(args)}", code="git_timeout") from exc


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_target_plan_path(value: str) -> PurePosixPath:
    if not value or not value.strip():
        raise PreflightFailure("--target-plan must not be empty", code="unsafe_target_plan")
    if any(char.isspace() for char in value):
        raise PreflightFailure("--target-plan must not contain whitespace", code="unsafe_target_plan")
    if not SAFE_PLAN_PATH_RE.fullmatch(value):
        raise PreflightFailure("--target-plan contains unsupported characters", code="unsafe_target_plan")
    plan = PurePosixPath(value)
    if plan.is_absolute():
        raise PreflightFailure("--target-plan must be relative to the target repository", code="unsafe_target_plan")
    if ".." in plan.parts:
        raise PreflightFailure("--target-plan must not contain parent traversal", code="unsafe_target_plan")
    if not plan.parts or plan.parts[0] == ".humanize":
        raise PreflightFailure("--target-plan must live outside .humanize/", code="unsafe_target_plan")
    if plan.name in {"", ".", ".."}:
        raise PreflightFailure("--target-plan must name a file", code="unsafe_target_plan")
    return plan


def load_bridge_metadata(workspace: Path) -> dict[str, Any]:
    path = workspace / ".humanize" / "rlinfra_bridge.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PreflightFailure(
            f"missing bridge metadata: {path}; prepare the workspace first",
            code="bridge_metadata",
        ) from exc
    except json.JSONDecodeError as exc:
        raise PreflightFailure(f"bridge metadata is invalid JSON: {path}: {exc}", code="bridge_metadata") from exc
    if not isinstance(data, dict):
        raise PreflightFailure(f"bridge metadata must be a JSON object: {path}", code="bridge_metadata")
    return data


def append_local_exclude(target_repo: Path) -> dict[str, Any]:
    probe = ".humanize/rlcr/.probe"
    ignored = run_git(["check-ignore", "-v", "--no-index", "--", probe], cwd=target_repo)
    if ignored.returncode == 0:
        return {
            "ignored": True,
            "updated": False,
            "pattern": ignored.stdout.strip(),
            "source": "existing-ignore-rule",
        }
    if ignored.returncode not in {1}:
        raise PreflightFailure(
            f"could not inspect .humanize ignore status: {ignored.stderr.strip()}",
            code="local_ignore",
        )

    git_path = run_git(["rev-parse", "--git-path", "info/exclude"], cwd=target_repo)
    if git_path.returncode != 0 or not git_path.stdout.strip():
        raise PreflightFailure(
            f"could not resolve .git/info/exclude: {git_path.stderr.strip()}",
            code="local_ignore",
        )
    exclude_path = Path(git_path.stdout.strip())
    if not exclude_path.is_absolute():
        exclude_path = target_repo / exclude_path
    exclude_path = exclude_path.resolve()
    exclude_path.parent.mkdir(parents=True, exist_ok=True)
    existing = exclude_path.read_text(encoding="utf-8") if exclude_path.exists() else ""
    prefix = "" if not existing or existing.endswith("\n") else "\n"
    exclude_path.write_text(existing + prefix + "/.humanize/\n", encoding="utf-8")

    verified = run_git(["check-ignore", "-v", "--no-index", "--", probe], cwd=target_repo)
    if verified.returncode != 0:
        raise PreflightFailure("failed to activate the local .humanize/ exclude rule", code="local_ignore")
    return {
        "ignored": True,
        "updated": True,
        "pattern": verified.stdout.strip(),
        "source": str(exclude_path),
    }


def remediation_for(
    code: str,
    *,
    target_repo: Path,
    workspace: Path,
    target_plan: str,
    details: dict[str, Any] | None = None,
) -> list[str]:
    if code == "unsafe_target_plan":
        return [
            "Choose a whitespace-free relative plan path outside .humanize/, such as docs/superpowers/rlcr/task-plan.md, then rerun the preflight."
        ]
    if code == "symlink_target_plan":
        return [
            "Replace the target-plan symlink with a normal tracked file inside the target repository, then rerun preflight."
        ]
    if code in {"missing_target_plan", "untracked_target_plan"}:
        safe_plan = validate_target_plan_path(target_plan)
        target_path = target_repo.joinpath(*safe_plan.parts)
        return [
            shlex.join(["mkdir", "-p", str(target_path.parent)]),
            shlex.join(["cp", str(workspace / "docs" / "plan.md"), str(target_path)]),
            shlex.join(["git", "-C", str(target_repo), "add", "--", target_plan]),
            shlex.join(["git", "-C", str(target_repo), "commit", "-m", "Add RLCR plan"]),
        ]
    if code == "plan_hash_mismatch":
        hash_script = (
            "import hashlib, pathlib, sys; "
            "print(*[f'{hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()}  {p}' for p in sys.argv[1:]], sep='\\n')"
        )
        return [
            shlex.join(
                [
                    sys.executable,
                    "-c",
                    hash_script,
                    str(workspace / "docs" / "plan.md"),
                    str(target_repo / Path(target_plan)),
                ]
            ),
            "Decide which committed plan is authoritative. If the workspace plan is correct, copy it to the target and commit it. If the target plan is correct, copy it back to workspace docs/plan.md and rerun start without --overwrite-human-docs.",
        ]
    if code == "dirty_target_plan":
        return [
            shlex.join(["git", "-C", str(target_repo), "status", "--short", "--", target_plan]),
            "Commit the intended target-plan edit or restore it before rerunning preflight.",
        ]
    if code == "tracked_humanize":
        return [
            shlex.join(["git", "-C", str(target_repo), "rm", "--cached", "-r", ".humanize"]),
            "Keep .humanize/ on disk and rerun the preflight; do not use git add -f.",
        ]
    if code == "working_tree_dirty":
        details = details or {}
        tracked_count = len(details.get("tracked_entries", []))
        untracked_count = len(details.get("untracked_entries", []))
        return [
            shlex.join(["git", "-C", str(target_repo), "status", "--short"]),
            (
                f"Preflight found {tracked_count} tracked/staged entries and {untracked_count} untracked entries. "
                "Resolve tracked or staged edits deliberately. For local generated or untracked paths, add narrow "
                "patterns to .git/info/exclude; do not commit or stash build artifacts merely to satisfy preflight."
            ),
        ]
    if code == "bridge_metadata":
        return [
            "Rerun the target-aware prepare/start flow for this workspace, target repository, and diff base; do not hand-edit stale bridge metadata."
        ]
    if code == "plan_lock":
        return [
            "Inspect workspace docs/plan.md and .humanize/plan.lock.md, restore the intended plan content, then refresh the lock.",
            shlex.join(
                [
                    sys.executable,
                    str(repo_root() / ".agents" / "skills" / "RLInfraWiki" / "scripts" / "lock_plan.py"),
                    "--workspace",
                    str(workspace),
                ]
            ),
        ]
    if code == "workspace_plan":
        return [
            "Rerun prepare without --overwrite-human-docs to restore missing generated workspace inputs, then review docs/plan.md before starting."
        ]
    if code == "diff_base":
        return [
            shlex.join(["git", "-C", str(target_repo), "branch", "--list"]),
            "Choose an existing local diff-base branch and rerun the target-aware prepare/start flow with the same value.",
        ]
    if code == "local_ignore":
        return [
            shlex.join(["git", "-C", str(target_repo), "rev-parse", "--git-path", "info/exclude"]),
            "Repair access to the repository-local exclude file, then rerun preflight.",
        ]
    if code in {"git_unavailable", "git_timeout", "git_inspection"}:
        return ["Restore a working git CLI/repository operation, then rerun preflight; do not change target content to mask a tooling failure."]
    if code == "filesystem_error":
        return [
            f"Inspect filesystem access and free space for both workspace {workspace} and target {target_repo}, then rerun preflight."
        ]
    if code == "target_repo":
        return ["Pass the exact target git root as --target-repo and rerun the target-aware prepare/start flow."]
    return ["Correct the reported preflight condition and rerun the same command."]


def parse_porcelain_z(output: str) -> list[dict[str, str | None]]:
    parts = output.split("\0")
    records: list[dict[str, str | None]] = []
    index = 0
    while index < len(parts):
        record = parts[index]
        index += 1
        if not record:
            continue
        if len(record) < 4 or record[2] != " ":
            raise PreflightFailure(
                f"unexpected git status --porcelain -z record: {record!r}",
                code="git_inspection",
            )
        status = record[:2]
        path = record[3:]
        original_path = None
        if "R" in status or "C" in status:
            if index >= len(parts) or not parts[index]:
                raise PreflightFailure(
                    f"missing original path for git status record: {record!r}",
                    code="git_inspection",
                )
            original_path = parts[index]
            index += 1
        records.append({"status": status, "path": path, "original_path": original_path})
    return records


def display_status_record(record: dict[str, str | None]) -> str:
    text = f"{record['status']} {record['path']}"
    if record["original_path"] is not None:
        text += f" <- {record['original_path']}"
    return text


def classify_working_tree(records: list[dict[str, str | None]], *, passed: bool = False) -> dict[str, Any]:
    entries = [display_status_record(record) for record in records]
    untracked = [record["path"] for record in records if record["status"] == "??"]
    tracked_records = [record for record in records if record["status"] != "??"]
    tracked = [display_status_record(record) for record in tracked_records]
    staged = [
        display_status_record(record)
        for record in tracked_records
        if record["status"] is not None and record["status"][0] != " "
    ]
    unstaged = [
        display_status_record(record)
        for record in tracked_records
        if record["status"] is not None and record["status"][1] != " "
    ]
    return {
        "passed": passed,
        "entry_count": len(entries),
        "entries": entries,
        "tracked_entries": tracked,
        "untracked_entries": untracked,
        "staged_entries": staged,
        "unstaged_entries": unstaged,
    }


def dirty_tree_message(entries: list[str]) -> str:
    preview = entries[:MAX_DIRTY_ERROR_ENTRIES]
    message = f"target working tree is not clean: {len(entries)} entries; first {len(preview)}: " + " | ".join(preview)
    omitted = len(entries) - len(preview)
    if omitted:
        message += f" | ... {omitted} additional entries omitted from the error message"
    return message


def run_preflight(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    cwd = Path.cwd()
    target_repo = resolve_cli_path(args.target_repo, base=cwd)
    workspace = resolve_cli_path(args.workspace, base=cwd)
    report_path = resolve_cli_path(
        args.report or str(workspace / ".humanize" / "rlinfra_target_preflight.json"),
        base=cwd,
    )
    report: dict[str, Any] = {
        "schema_version": PREFLIGHT_SCHEMA_VERSION,
        "checked_at": now_iso(),
        "status": "failed",
        "target_repo": str(target_repo),
        "workspace": str(workspace),
        "target_plan": args.target_plan,
        "diff_base": args.diff_base,
        "checks": {},
        "errors": [],
        "error_code": None,
        "remediation": [],
    }

    try:
        target_plan = validate_target_plan_path(args.target_plan)
        if not target_repo.exists() or not target_repo.is_dir():
            raise PreflightFailure(
                f"target repository does not exist or is not a directory: {target_repo}",
                code="target_repo",
            )

        top_level = run_git(["rev-parse", "--show-toplevel"], cwd=target_repo)
        if top_level.returncode != 0:
            raise PreflightFailure(f"target repository is not a git repository: {target_repo}", code="target_repo")
        actual_root = Path(top_level.stdout.strip()).resolve()
        if actual_root != target_repo:
            raise PreflightFailure(
                f"target repository must be the git root: requested={target_repo} actual={actual_root}",
                code="target_repo",
            )
        report["checks"]["git_root"] = {"passed": True, "path": str(actual_root)}

        bridge = load_bridge_metadata(workspace)
        if bridge.get("schema_version") != 2 or bridge.get("execution_mode") != "target_repo":
            raise PreflightFailure(
                "bridge metadata must use schema v2 target_repo execution mode; rerun the target-aware prepare step",
                code="bridge_metadata",
            )
        bridge_workspace = bridge.get("workspace")
        if not isinstance(bridge_workspace, str) or Path(bridge_workspace).expanduser().resolve() != workspace:
            raise PreflightFailure(
                f"bridge workspace does not match preflight workspace: bridge={bridge_workspace!r} workspace={workspace}",
                code="bridge_metadata",
            )
        bridge_target = bridge.get("target_repo")
        if not isinstance(bridge_target, str) or Path(bridge_target).expanduser().resolve() != target_repo:
            raise PreflightFailure(
                f"bridge target_repo does not match preflight target: bridge={bridge_target!r} target={target_repo}",
                code="bridge_metadata",
            )
        if bridge.get("diff_base") != args.diff_base:
            raise PreflightFailure(
                f"bridge diff_base does not match preflight diff base: bridge={bridge.get('diff_base')!r} target={args.diff_base!r}",
                code="bridge_metadata",
            )
        report["checks"]["bridge_metadata"] = {
            "passed": True,
            "schema_version": bridge.get("schema_version"),
        }

        base_ref = f"refs/heads/{args.diff_base}^{{commit}}"
        base = run_git(["rev-parse", "--verify", base_ref], cwd=target_repo)
        if base.returncode != 0:
            raise PreflightFailure(f"diff base is not a local branch: {args.diff_base}", code="diff_base")
        report["checks"]["diff_base"] = {"passed": True, "commit": base.stdout.strip()}

        tracked_humanize = run_git(["ls-files", "--", ".humanize"], cwd=target_repo)
        if tracked_humanize.returncode != 0:
            raise PreflightFailure(
                f"could not inspect tracked Humanize state: {tracked_humanize.stderr.strip()}",
                code="git_inspection",
            )
        tracked_paths = [line for line in tracked_humanize.stdout.splitlines() if line.strip()]
        if tracked_paths:
            raise PreflightFailure(
                f"tracked Humanize state is forbidden: {', '.join(tracked_paths)}",
                code="tracked_humanize",
            )
        report["checks"]["tracked_humanize"] = {"passed": True, "paths": []}

        ignore = append_local_exclude(target_repo)
        report["checks"]["local_ignore"] = {"passed": True, **ignore}

        target_plan_path = target_repo.joinpath(*target_plan.parts)
        if target_plan_path.is_symlink():
            raise PreflightFailure(
                f"target plan must not be a symlink: {target_plan}",
                code="symlink_target_plan",
            )
        if not target_plan_path.exists() or not target_plan_path.is_file():
            raise PreflightFailure(
                f"target plan does not exist or is not a regular file: {target_plan}",
                code="missing_target_plan",
            )
        try:
            target_plan_path.resolve().relative_to(target_repo)
        except ValueError as exc:
            raise PreflightFailure(
                f"target plan resolves outside the target repository: {target_plan}",
                code="unsafe_target_plan",
            ) from exc
        tracked_plan = run_git(["ls-files", "--error-unmatch", "--", target_plan.as_posix()], cwd=target_repo)
        if tracked_plan.returncode != 0:
            raise PreflightFailure(f"target plan is not tracked in git: {target_plan}", code="untracked_target_plan")
        plan_status = run_git(["status", "--porcelain", "--", target_plan.as_posix()], cwd=target_repo)
        if plan_status.returncode != 0:
            raise PreflightFailure(
                f"could not inspect target plan status: {plan_status.stderr.strip()}",
                code="git_inspection",
            )
        if plan_status.stdout.strip():
            raise PreflightFailure(
                f"target plan has uncommitted modifications: {target_plan}",
                code="dirty_target_plan",
            )

        prepared_plan = workspace / "docs" / "plan.md"
        if not prepared_plan.exists() or not prepared_plan.is_file():
            raise PreflightFailure(f"prepared workspace plan is missing: {prepared_plan}", code="workspace_plan")
        prepared_hash = sha256_file(prepared_plan)
        plan_lock = workspace / ".humanize" / "plan.lock.md"
        try:
            lock_text = plan_lock.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise PreflightFailure(f"prepared plan lock is missing: {plan_lock}", code="plan_lock") from exc
        lock_match = PLAN_LOCK_HASH_RE.search(lock_text)
        if lock_match is None:
            raise PreflightFailure(f"prepared plan lock has no valid plan_sha256: {plan_lock}", code="plan_lock")
        lock_hash = lock_match.group(1)
        if lock_hash != prepared_hash:
            raise PreflightFailure(
                f"prepared plan lock does not match docs/plan.md: lock={lock_hash} prepared={prepared_hash}",
                code="plan_lock",
            )
        target_hash = sha256_file(target_plan_path)
        if prepared_hash != target_hash:
            raise PreflightFailure(
                f"target plan hash does not match the prepared plan: target={target_hash} prepared={prepared_hash}",
                code="plan_hash_mismatch",
            )
        report["checks"]["target_plan"] = {
            "passed": True,
            "path": target_plan.as_posix(),
            "absolute_path": str(target_plan_path),
            "tracked": True,
            "clean": True,
            "sha256": target_hash,
            "prepared_sha256": prepared_hash,
            "plan_lock_sha256": lock_hash,
        }

        tree = run_git(["status", "--porcelain=v1", "-z", "--untracked-files=all"], cwd=target_repo)
        if tree.returncode != 0:
            raise PreflightFailure(
                f"could not inspect target working tree: {tree.stderr.strip()}",
                code="git_inspection",
            )
        records = parse_porcelain_z(tree.stdout)
        if records:
            report["checks"]["working_tree"] = classify_working_tree(records)
            raise PreflightFailure(
                dirty_tree_message(report["checks"]["working_tree"]["entries"]),
                code="working_tree_dirty",
            )
        report["checks"]["working_tree"] = classify_working_tree([], passed=True)
        report["status"] = "passed"
        report["plan_sha256"] = target_hash
        exit_code = 0
    except (PreflightFailure, OSError) as exc:
        message = str(exc) if isinstance(exc, PreflightFailure) else f"filesystem error during target preflight: {exc}"
        error_code = exc.code if isinstance(exc, PreflightFailure) else "filesystem_error"
        report["errors"].append(message)
        report["error_code"] = error_code
        try:
            report["remediation"] = remediation_for(
                error_code,
                target_repo=target_repo,
                workspace=workspace,
                target_plan=args.target_plan,
                details=report["checks"].get("working_tree"),
            )
        except Exception as remediation_exc:
            detail = str(remediation_exc).strip()
            if len(detail) > 240:
                detail = detail[:237] + "..."
            suffix = f": {detail}" if detail else ""
            report["remediation"] = [
                f"Remediation generation failed safely: {type(remediation_exc).__name__}{suffix}. "
                "Correct the reported condition and rerun preflight."
            ]
        exit_code = HYGIENE_FAILURE_EXIT_CODE

    report["report_path"] = str(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return exit_code, report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate target-repository hygiene before a Humanize RLCR launch.")
    parser.add_argument("--target-repo", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--target-plan", required=True)
    parser.add_argument("--diff-base", required=True)
    parser.add_argument("--report", default=None)
    parser.add_argument("--print-json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    code, report = run_preflight(args)
    if args.print_json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif code == 0:
        print(f"Humanize target preflight passed: {report['target_repo']}")
        print(f"Report: {report['report_path']}")
    else:
        for error in report["errors"]:
            print(f"ERROR: {error}", file=sys.stderr)
        for command in report["remediation"]:
            print(f"FIX: {command}", file=sys.stderr)
        print(f"Report: {report['report_path']}", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
