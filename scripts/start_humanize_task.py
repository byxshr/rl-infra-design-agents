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
from validate_humanize_review_contract import CONTRACT_ID, validate_runtime_root


OPERATOR_SCHEMA_VERSION = 3
SUPPORTED_PREPARE_BRIDGE_SCHEMA_VERSIONS = frozenset({PREPARE_BRIDGE_SCHEMA_VERSION})
SLASH_COMMAND = "/humanize:start-rlcr-loop docs/plan.md"
TARGET_PREFLIGHT_RELPATH = Path(".humanize") / "rlinfra_target_preflight.json"
TARGET_HYGIENE_EXIT_CODE = 3
PREREQUISITE_EXIT_CODE = 2
PERSONAL_HUMANIZE_REPOSITORY = "byxshr/humanize"


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


def run_target_preflight(
    *,
    root: Path,
    workspace: Path,
    target_repo: Path,
    target_plan: str,
    diff_base: str,
    timeout: int,
) -> tuple[subprocess.CompletedProcess[str], dict[str, Any] | None, list[str]]:
    report_path = (workspace / TARGET_PREFLIGHT_RELPATH).resolve()
    argv = [
        sys.executable,
        str(root / "scripts" / "preflight_humanize_target.py"),
        "--target-repo",
        str(target_repo),
        "--workspace",
        str(workspace),
        "--target-plan",
        target_plan,
        "--diff-base",
        diff_base,
        "--report",
        str(report_path),
        "--print-json",
    ]
    try:
        result = subprocess.run(argv, cwd=root, text=True, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        result = subprocess.CompletedProcess(
            argv,
            124,
            stdout=normalize_stream(exc.stdout),
            stderr=normalize_stream(exc.stderr) + f"\nTarget preflight timed out after {timeout} seconds.\n",
        )
    report = None
    if result.stdout.strip():
        try:
            parsed = json.loads(result.stdout)
            if isinstance(parsed, dict):
                report = parsed
        except json.JSONDecodeError:
            pass
    return result, report, argv


def discover_installed_humanize_runtime(*, timeout: int) -> dict[str, Any]:
    command = ["claude", "plugin", "list", "--json"]
    try:
        result = subprocess.run(command, text=True, capture_output=True, timeout=timeout)
    except FileNotFoundError:
        return {
            "runtime_type": "installed_plugin",
            "status": "missing",
            "root": None,
            "plugin_id": "humanize@PolyArch",
            "plugin_version": None,
            "contract_fingerprint": None,
            "checker": "claude plugin list --json",
            "errors": ["claude executable was not found while discovering humanize@PolyArch"],
        }
    except subprocess.TimeoutExpired:
        return {
            "runtime_type": "installed_plugin",
            "status": "missing",
            "root": None,
            "plugin_id": "humanize@PolyArch",
            "plugin_version": None,
            "contract_fingerprint": None,
            "checker": "claude plugin list --json",
            "errors": [f"claude plugin discovery timed out after {timeout} seconds"],
        }
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip() or f"exit code {result.returncode}"
        return {
            "runtime_type": "installed_plugin",
            "status": "missing",
            "root": None,
            "plugin_id": "humanize@PolyArch",
            "plugin_version": None,
            "contract_fingerprint": None,
            "checker": "claude plugin list --json",
            "errors": [f"claude plugin discovery failed: {detail}"],
        }
    try:
        plugins = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return {
            "runtime_type": "installed_plugin",
            "status": "missing",
            "root": None,
            "plugin_id": "humanize@PolyArch",
            "plugin_version": None,
            "contract_fingerprint": None,
            "checker": "claude plugin list --json",
            "errors": [f"claude plugin list returned invalid JSON: {exc}"],
        }
    if not isinstance(plugins, list):
        return {
            "runtime_type": "installed_plugin",
            "status": "missing",
            "root": None,
            "plugin_id": "humanize@PolyArch",
            "plugin_version": None,
            "contract_fingerprint": None,
            "checker": "claude plugin list --json",
            "errors": ["claude plugin list JSON must be an array"],
        }
    matches = [
        plugin
        for plugin in plugins
        if isinstance(plugin, dict) and plugin.get("id") == "humanize@PolyArch" and plugin.get("enabled") is True
    ]
    if len(matches) != 1:
        return {
            "runtime_type": "installed_plugin",
            "status": "missing",
            "root": None,
            "plugin_id": "humanize@PolyArch",
            "plugin_version": None,
            "contract_fingerprint": None,
            "checker": "claude plugin list --json",
            "errors": [f"expected one enabled humanize@PolyArch plugin, found {len(matches)}"],
        }
    plugin = matches[0]
    install_path = plugin.get("installPath")
    if not isinstance(install_path, str) or not install_path.strip():
        return {
            "runtime_type": "installed_plugin",
            "status": "missing",
            "root": None,
            "plugin_id": "humanize@PolyArch",
            "plugin_version": plugin.get("version"),
            "contract_fingerprint": None,
            "checker": "claude plugin list --json",
            "errors": ["enabled humanize@PolyArch plugin has no installPath"],
        }
    validation = validate_runtime_root(Path(install_path))
    return {
        "runtime_type": "installed_plugin",
        "status": validation["status"],
        "root": validation["root"],
        "plugin_id": plugin.get("id"),
        "plugin_version": plugin.get("version") or validation.get("plugin_version"),
        "contract_fingerprint": validation.get("contract_fingerprint"),
        "validation_kind": validation.get("validation_kind"),
        "checker": "claude plugin list --json + scripts/validate_humanize_review_contract.py",
        "errors": validation["errors"],
    }


def is_personal_humanize_remote(url: str) -> bool:
    normalized = url.strip().lower().rstrip("/")
    if normalized.endswith(".git"):
        normalized = normalized[:-4]
    return normalized in {
        "git@github.com:byxshr/humanize",
        "ssh://git@github.com/byxshr/humanize",
        "https://github.com/byxshr/humanize",
    }


def inspect_personal_humanize_fork(root: Path, *, timeout: int) -> dict[str, Any]:
    resolved_root = root.resolve()

    def git(*args: str) -> subprocess.CompletedProcess[str]:
        command = ["git", "-C", str(resolved_root), *args]
        try:
            return subprocess.run(
                command,
                text=True,
                capture_output=True,
                timeout=timeout,
            )
        except FileNotFoundError:
            return subprocess.CompletedProcess(command, 127, stdout="", stderr="git executable was not found")
        except subprocess.TimeoutExpired:
            return subprocess.CompletedProcess(
                command,
                124,
                stdout="",
                stderr=f"git command timed out after {timeout} seconds",
            )

    errors: list[str] = []
    top_level = git("rev-parse", "--show-toplevel")
    if top_level.returncode != 0:
        detail = (top_level.stderr or top_level.stdout).strip() or f"exit code {top_level.returncode}"
        errors.append(f"Humanize plugin root is not a Git checkout: {detail}")
        git_root = None
    else:
        git_root = str(Path(top_level.stdout.strip()).resolve())
        if Path(git_root) != resolved_root:
            errors.append(f"Humanize plugin root must be the Git checkout root: {git_root}")

    remote_result = git("remote", "-v")
    remote_urls: list[str] = []
    if remote_result.returncode == 0:
        for line in remote_result.stdout.splitlines():
            fields = line.split()
            if len(fields) >= 2 and fields[1] not in remote_urls:
                remote_urls.append(fields[1])
    fork_remotes = [url for url in remote_urls if is_personal_humanize_remote(url)]
    if not fork_remotes:
        errors.append(
            "Humanize checkout has no remote for github.com/byxshr/humanize; "
            "real target tasks must use the project-maintained fork"
        )

    head_result = git("rev-parse", "HEAD")
    git_head = head_result.stdout.strip() if head_result.returncode == 0 else None
    if not git_head:
        detail = (head_result.stderr or head_result.stdout).strip() or f"exit code {head_result.returncode}"
        errors.append(f"could not resolve Humanize checkout HEAD: {detail}")

    status_result = git("status", "--porcelain", "--untracked-files=normal")
    git_clean = status_result.returncode == 0 and not status_result.stdout.strip()
    if status_result.returncode != 0:
        detail = (status_result.stderr or status_result.stdout).strip() or f"exit code {status_result.returncode}"
        errors.append(f"could not inspect Humanize checkout status: {detail}")
    elif not git_clean:
        errors.append("Humanize checkout must be clean before launching a real target task")

    return {
        "status": "compatible" if not errors else "incompatible",
        "git_root": git_root,
        "git_head": git_head,
        "fork_remotes": fork_remotes,
        "git_clean": git_clean,
        "errors": errors,
    }


def resolve_humanize_runtime(
    explicit_root: Path | None,
    *,
    timeout: int,
    require_personal_fork: bool = False,
) -> dict[str, Any]:
    if explicit_root is None and require_personal_fork:
        runtime = {
            "runtime_type": "personal_fork",
            "status": "missing",
            "root": None,
            "plugin_id": "humanize",
            "plugin_version": None,
            "contract_fingerprint": None,
            "validation_kind": None,
            "checker": "explicit local byxshr/humanize fork required",
            "git_root": None,
            "git_head": None,
            "fork_remotes": [],
            "git_clean": False,
            "errors": [
                "real target tasks require --humanize-plugin-root pointing to a clean local "
                "github.com/byxshr/humanize checkout"
            ],
        }
    elif explicit_root is None:
        runtime = discover_installed_humanize_runtime(timeout=timeout)
    else:
        validation = validate_runtime_root(explicit_root)
        fork_validation = (
            inspect_personal_humanize_fork(explicit_root, timeout=timeout)
            if require_personal_fork and validation["status"] == "compatible"
            else None
        )
        errors = list(validation["errors"])
        if fork_validation is not None:
            errors.extend(fork_validation["errors"])
        runtime = {
            "runtime_type": "personal_fork" if require_personal_fork else "explicit_local",
            "status": "compatible" if validation["status"] == "compatible" and not errors else "incompatible",
            "root": validation["root"],
            "plugin_id": "humanize",
            "plugin_version": validation.get("plugin_version"),
            "contract_fingerprint": validation.get("contract_fingerprint"),
            "validation_kind": validation.get("validation_kind"),
            "checker": (
                "scripts/validate_humanize_review_contract.py --humanize-root + "
                "local byxshr/humanize Git provenance"
                if require_personal_fork
                else "scripts/validate_humanize_review_contract.py --humanize-root"
            ),
            "git_root": fork_validation.get("git_root") if fork_validation else None,
            "git_head": fork_validation.get("git_head") if fork_validation else None,
            "fork_remotes": fork_validation.get("fork_remotes", []) if fork_validation else [],
            "git_clean": fork_validation.get("git_clean") if fork_validation else None,
            "errors": errors,
        }
    return {
        "contract_id": CONTRACT_ID,
        "required": True,
        **runtime,
    }


def build_commands(
    *,
    root: Path,
    workspace: Path,
    round_number: int,
    python_executable: str,
    target_repo: Path | None,
    target_plan: str | None,
    diff_base: str,
    launcher_path: Path | None,
) -> dict[str, Any]:
    import_command = " ".join(
        [
            "make",
            "import-humanize-round",
            make_var("HUMANIZE_WORKSPACE", str(workspace)),
            make_var("ROUND", round_number),
            make_var("PYTHON", python_executable),
        ]
    )
    loop_root = (target_repo or workspace) / ".humanize" / "rlcr" / "{{TIMESTAMP}}"
    import_with_loop_dir = " ".join(
        [
            "make",
            "import-humanize-round",
            make_var("HUMANIZE_WORKSPACE", str(workspace)),
            make_var("ROUND", round_number),
            make_var("HUMANIZE_LOOP_DIR", str(loop_root)),
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
    humanize_start = SLASH_COMMAND
    if target_repo is not None and target_plan is not None:
        humanize_start = (
            f"/humanize:start-rlcr-loop {target_plan} --track-plan-file --base-branch {diff_base}"
        )
    return {
        "enter_workspace": f"cd {shlex.quote(str(workspace))}",
        "launch_claude": shell_join([str(launcher_path)]) if launcher_path is not None else None,
        "humanize_start": humanize_start,
        "import_round": import_command,
        "import_round_with_loop_dir": import_with_loop_dir,
        "review_gate": shell_join(gate_argv),
        "python": python_executable,
    }


def render_launcher(
    *,
    root: Path,
    workspace: Path,
    target_repo: Path,
    target_plan: str,
    diff_base: str,
    report_path: Path,
    plugin_root: Path | None,
) -> str:
    preflight = shell_join(
        [
            sys.executable,
            str(root / "scripts" / "preflight_humanize_target.py"),
            "--target-repo",
            str(target_repo),
            "--workspace",
            str(workspace),
            "--target-plan",
            target_plan,
            "--diff-base",
            diff_base,
            "--report",
            str(report_path),
        ]
    )
    claude_args = ""
    if plugin_root is not None:
        claude_args = f" --plugin-dir {shlex.quote(str(plugin_root))}"
    return f"""#!/usr/bin/env bash
set -euo pipefail

{preflight}
cd {shlex.quote(str(target_repo))}
exec "${{RLINFRA_CLAUDE_BIN:-claude}}"{claude_args} "$@"
"""


def render_operator_doc(
    *,
    created_at: str,
    contract: Path,
    workspace: Path,
    target_repo: Path | None,
    target_plan: str | None,
    diff_base: str,
    round_number: int,
    bridge_metadata_path: Path,
    operator_metadata_path: Path,
    launcher_path: Path | None,
    preflight_report_path: Path | None,
    review_contract: dict[str, Any],
    commands: dict[str, Any],
) -> str:
    target_text = str(target_repo) if target_repo is not None else "not provided"
    target_plan_text = target_plan or "not provided"
    if target_repo is not None:
        plugin_prerequisites = f"""The start wrapper requires a clean local checkout of the project-maintained
`{PERSONAL_HUMANIZE_REPOSITORY}` fork, validates it against `{CONTRACT_ID}`, records its Git HEAD and
remote provenance, and passes it to Claude Code with `--plugin-dir`. It does not fall back to a
marketplace-installed Humanize runtime for real target tasks.
"""
        start_instructions = f"""## 1. Launch Claude Code From The Target Repository

The target plan passed strict hygiene checks and matches the prepared `docs/plan.md` byte-for-byte.

Run the generated launcher from a terminal:

```bash
{commands["launch_claude"]}
```

The launcher reruns target preflight, changes directory to `{target_repo}`, and starts Claude Code there. Do not start Claude Code from the staging workspace and switch repositories later.

The launcher is an initial-launch guard and forwards any Claude CLI arguments. Once a loop has intentionally changed the target working tree, resume inside the existing Claude session or start Claude directly from the target root; the strict launcher will reject the in-flight dirty tree.

Then run this exact slash command inside Claude Code:

```text
{commands["humanize_start"]}
```

The tracked plan lives outside `.humanize/`. Keep `.humanize/rlcr/` local-only and never run `git add -f .humanize`.
"""
    else:
        plugin_prerequisites = f"""Workspace-only mode may validate an explicitly supplied local runtime or
discover an enabled `humanize@PolyArch` plugin. This compatibility path is for design-only work and
does not satisfy the local-fork requirement for a real target task.

If `/humanize:start-rlcr-loop` is unavailable in workspace-only mode, install Humanize in Claude Code:

```text
/plugin marketplace add PolyArch/humanize
/plugin install humanize@PolyArch
```
"""
        start_instructions = f"""## 1. Start Humanize In Claude Code

Open Claude Code in the prepared workspace:

```bash
{commands["enter_workspace"]}
```

Run this exact slash command inside Claude Code:

```text
{commands["humanize_start"]}
```

Workspace-only mode does not provide target-repository session-root guarantees. Use target mode for real code-changing tasks.
"""
    return f"""<!-- generated by scripts/start_humanize_task.py at {created_at}; metadata: {operator_metadata_path} -->

# Humanize Task Operator Guide

This workspace was prepared by the IMP-015 start wrapper. It does not start Claude Code and does not run the Humanize plugin.

## Prepared Inputs

- Contract: `{contract}`
- Workspace: `{workspace}`
- Target repo: `{target_text}`
- Target plan: `{target_plan_text}`
- Diff base: `{diff_base}`
- Round to import: `{round_number}`
- Bridge metadata: `{bridge_metadata_path}`
- Operator metadata: `{operator_metadata_path}`
- Target preflight report: `{preflight_report_path or 'not applicable'}`
- Claude launcher: `{launcher_path or 'not applicable'}`
- Review contract: `{review_contract["contract_id"]}` ({review_contract["status"]})
- Humanize runtime: `{review_contract.get("runtime_type")}` at `{review_contract.get("root") or 'not found'}`
- Contract fingerprint: `{review_contract.get("contract_fingerprint") or 'unavailable'}`
- Runtime validation kind: `{review_contract.get("validation_kind") or 'unavailable'}`
- Plan: `docs/plan.md`

## Humanize Plugin Prerequisites

{plugin_prerequisites}

{start_instructions}

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
    target_plan: str | None,
    diff_base: str,
    round_number: int,
    bridge_metadata_path: Path,
    operator_doc_path: Path,
    operator_metadata_path: Path,
    launcher_path: Path | None,
    preflight_report_path: Path | None,
    preflight_report: dict[str, Any] | None,
    bridge_metadata: dict[str, Any],
    prepare_command: list[str],
    commands: dict[str, Any],
    prepare_bridge_schema_version: int,
    review_contract: dict[str, Any],
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
        "target_plan": target_plan,
        "execution_mode": "target_repo" if target_repo is not None else "workspace",
        "diff_base": diff_base,
        "round": round_number,
        "prepare_metadata_path": str(bridge_metadata_path),
        "bridge_metadata_path": str(bridge_metadata_path),
        "operator_doc": str(operator_doc_path),
        "operator_metadata": str(operator_metadata_path),
        "launcher": str(launcher_path) if launcher_path is not None else None,
        "target_preflight_report": str(preflight_report_path) if preflight_report_path is not None else None,
        "target_preflight": preflight_report,
        "plan_sha256": preflight_report.get("plan_sha256") if preflight_report is not None else None,
        "prepare_bridge_schema_version": prepare_bridge_schema_version,
        "repo_commit": bridge_metadata.get("repo_commit"),
        "rlinfrawiki_commit": bridge_metadata.get("rlinfrawiki_commit"),
        "context_paths": bridge_metadata.get("context_paths", {}),
        "plan_lock": bridge_metadata.get("plan_lock"),
        "prereq_warnings": prereq_warnings,
        "review_contract": review_contract,
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
    if metadata["execution_mode"] == "target_repo":
        print(f"   Launch with: {commands['launch_claude']}", file=stream)
    else:
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
    humanize_plugin_root = maybe_resolve_cli_path(getattr(args, "humanize_plugin_root", None), base=cwd)
    target_plan_arg = getattr(args, "target_plan", None)
    target_plan = target_plan_arg.strip() if target_plan_arg is not None else None
    if target_repo is not None and not target_plan:
        raise StartError("--target-plan is required when --target-repo is provided")
    if target_repo is None and target_plan:
        raise StartError("--target-plan requires --target-repo")

    operator_doc_path = (workspace / "humanize_operator.md").resolve()
    operator_metadata_path = (workspace / ".humanize" / "rlinfra_operator.json").resolve()
    launcher_path = (workspace / "launch_humanize.sh").resolve() if target_repo is not None else None
    preflight_report_path = (workspace / TARGET_PREFLIGHT_RELPATH).resolve() if target_repo is not None else None
    for artifact in [operator_doc_path, operator_metadata_path, launcher_path]:
        if artifact is not None and artifact.is_dir() and not artifact.is_symlink():
            raise StartError(f"generated artifact path is a directory; remove it before retrying: {artifact}")

    prepare_command = prepare_argv(args, root=root, contract=contract, workspace=workspace, target_repo=target_repo)

    prepare_result = run_prepare(prepare_command, root=root, print_json=args.print_json, timeout=args.prepare_timeout)
    if prepare_result.returncode != 0:
        print("ERROR: stage prepare_humanize_task failed", file=sys.stderr)
        print(f"ERROR: command: {shell_join(prepare_command)}", file=sys.stderr)
        print(f"ERROR: exit code: {prepare_result.returncode}", file=sys.stderr)
        return prepare_result.returncode

    bridge_metadata_path = (workspace / BRIDGE_METADATA_RELPATH).resolve()
    try:
        bridge_metadata = load_json(bridge_metadata_path)
        prepare_bridge_schema_version = validate_prepare_bridge_schema(bridge_metadata, args.accept_bridge_schema)
    except StartError as exc:
        print("ERROR: stage operator_metadata failed", file=sys.stderr)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    review_contract = resolve_humanize_runtime(
        humanize_plugin_root,
        timeout=min(args.prepare_timeout, 30),
        require_personal_fork=target_repo is not None,
    )
    if review_contract["status"] != "compatible":
        detail = "; ".join(review_contract["errors"]) or "unknown compatibility failure"
        message = f"Humanize runtime is not compatible with {CONTRACT_ID}: {detail}"
        if target_repo is not None or args.strict_prereqs:
            print("ERROR: stage humanize_review_contract failed", file=sys.stderr)
            print(f"ERROR: {message}", file=sys.stderr)
            if target_repo is not None:
                print(
                    "FIX: pass --humanize-plugin-root /path/to/a/clean/byxshr/humanize checkout",
                    file=sys.stderr,
                )
            else:
                print(
                    "FIX: pass --humanize-plugin-root /path/to/compatible/humanize or update the installed plugin",
                    file=sys.stderr,
                )
            return PREREQUISITE_EXIT_CODE
        print(f"WARN: {message}", file=sys.stderr)

    for stale in [operator_doc_path, operator_metadata_path, launcher_path]:
        if stale is not None and (stale.exists() or stale.is_symlink()):
            if stale.is_dir() and not stale.is_symlink():
                raise StartError(f"generated artifact path is a directory; remove it before retrying: {stale}")
            stale.unlink()

    preflight_report: dict[str, Any] | None = None
    if target_repo is not None and target_plan is not None:
        preflight_result, preflight_report, preflight_command = run_target_preflight(
            root=root,
            workspace=workspace,
            target_repo=target_repo,
            target_plan=target_plan,
            diff_base=args.diff_base,
            timeout=args.prepare_timeout,
        )
        if preflight_result.stderr:
            print(preflight_result.stderr, end="", file=sys.stderr)
        if preflight_result.returncode != 0:
            print("ERROR: stage target_hygiene_preflight failed", file=sys.stderr)
            print(f"ERROR: command: {shell_join(preflight_command)}", file=sys.stderr)
            if preflight_report is not None:
                for error in preflight_report.get("errors", []):
                    print(f"ERROR: {error}", file=sys.stderr)
                for command in preflight_report.get("remediation", []):
                    print(f"FIX: {command}", file=sys.stderr)
                print(f"REPORT: {preflight_report.get('report_path', preflight_report_path)}", file=sys.stderr)
            return TARGET_HYGIENE_EXIT_CODE if preflight_result.returncode == TARGET_HYGIENE_EXIT_CODE else 1
        if preflight_report is None or preflight_report.get("status") != "passed":
            print("ERROR: target preflight returned no parseable passed report", file=sys.stderr)
            return 1

        assert launcher_path is not None
        assert preflight_report_path is not None
        launcher_path.write_text(
            render_launcher(
                root=root,
                workspace=workspace,
                target_repo=target_repo,
                target_plan=target_plan,
                diff_base=args.diff_base,
                report_path=preflight_report_path,
                plugin_root=humanize_plugin_root,
            ),
            encoding="utf-8",
        )
        launcher_path.chmod(0o755)

    created_at = now_iso()
    commands = build_commands(
        root=root,
        workspace=workspace,
        round_number=args.round,
        python_executable=sys.executable,
        target_repo=target_repo,
        target_plan=target_plan,
        diff_base=args.diff_base,
        launcher_path=launcher_path,
    )
    operator_doc = render_operator_doc(
        created_at=created_at,
        contract=contract,
        workspace=workspace,
        target_repo=target_repo,
        target_plan=target_plan,
        diff_base=args.diff_base,
        round_number=args.round,
        bridge_metadata_path=bridge_metadata_path,
        operator_metadata_path=operator_metadata_path,
        launcher_path=launcher_path,
        preflight_report_path=preflight_report_path,
        review_contract=review_contract,
        commands=commands,
    )
    operator_doc_path.write_text(operator_doc, encoding="utf-8")
    metadata = build_operator_metadata(
        created_at=created_at,
        contract=contract,
        workspace=workspace,
        target_repo=target_repo,
        target_plan=target_plan,
        diff_base=args.diff_base,
        round_number=args.round,
        bridge_metadata_path=bridge_metadata_path,
        operator_doc_path=operator_doc_path,
        operator_metadata_path=operator_metadata_path,
        launcher_path=launcher_path,
        preflight_report_path=preflight_report_path,
        preflight_report=preflight_report,
        bridge_metadata=bridge_metadata,
        prepare_command=prepare_command,
        commands=commands,
        prepare_bridge_schema_version=prepare_bridge_schema_version,
        review_contract=review_contract,
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
    parser.add_argument(
        "--humanize-plugin-root",
        default=None,
        help=(
            "Explicit Humanize plugin root. Real target tasks require a clean local "
            "github.com/byxshr/humanize checkout and pass it to claude --plugin-dir."
        ),
    )
    parser.add_argument(
        "--target-plan",
        default=None,
        help="Tracked, clean target-repository plan path; required with --target-repo.",
    )
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
