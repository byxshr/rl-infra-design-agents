from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import jsonschema
import yaml

SKILL_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[4]
WIKI_DIR = SKILL_ROOT / "wiki"
SOURCES_DIR = SKILL_ROOT / "sources"
DATA_DIR = SKILL_ROOT / "data"
QUERIES_DIR = SKILL_ROOT / "queries"

FRONTMATTER_RE = re.compile(r"^---\s*\r?\n(.*?)\r?\n---\s*\r?\n(.*)", re.DOTALL)
CONFIDENCE_LEVELS = {"verified", "source-reported", "inferred", "experimental"}
VALID_SEVERITIES = {"P0", "P1", "P2", "P3"}
TERMINAL_STATUSES = {"resolved", "fixed", "closed"}
DEFERRED_STATUSES = {"waived", "backlog"}
CLOSED_STATUSES = TERMINAL_STATUSES | DEFERRED_STATUSES
VALID_ISSUE_STATUSES = {"open", "in_progress"} | CLOSED_STATUSES


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_yaml(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return default if data is None else data


def dump_yaml(data: Any) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=False)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(json.loads(line))
    return out


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=False) + "\n")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def split_frontmatter(path: Path) -> tuple[dict[str, Any] | None, str]:
    content = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(content)
    if not match:
        return None, content
    fm = yaml.safe_load(match.group(1))
    if not isinstance(fm, dict):
        return None, match.group(2)
    return fm, match.group(2)


def iter_wiki_pages() -> list[dict[str, Any]]:
    pages = []
    if not WIKI_DIR.exists():
        return pages
    for path in sorted(WIKI_DIR.rglob("*.md")):
        if path.name == "README.md":
            continue
        fm, body = split_frontmatter(path)
        if not fm:
            continue
        fm = dict(fm)
        fm["_path"] = path.relative_to(SKILL_ROOT).as_posix()
        fm["_abs_path"] = path
        fm["_body"] = body
        pages.append(fm)
    return pages


def page_id_map() -> dict[str, Path]:
    out = {}
    for page in iter_wiki_pages():
        out[str(page.get("id"))] = page["_abs_path"]
    return out


def load_aliases() -> dict[str, set[str]]:
    raw = load_yaml(DATA_DIR / "aliases.yaml", {}) or {}
    aliases: dict[str, set[str]] = {}
    for canonical, values in raw.items():
        vals = {str(canonical).lower()}
        for value in values or []:
            vals.add(str(value).lower())
        for value in vals:
            aliases.setdefault(value, set()).update(vals)
    return aliases


def expand_terms(terms: list[str]) -> list[str]:
    aliases = load_aliases()
    out: list[str] = []
    for term in terms:
        low = term.lower()
        out.append(low)
        out.extend(sorted(aliases.get(low, set())))
    return list(dict.fromkeys(out))


def tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_.+-]+", text.lower())


def load_source_manifests() -> dict[str, dict[str, Any]]:
    manifests: dict[str, dict[str, Any]] = {}
    for base in [SOURCES_DIR / "repos", SOURCES_DIR / "docs", SOURCES_DIR / "papers", SOURCES_DIR / "blogs"]:
        if not base.exists():
            continue
        for path in sorted(base.glob("*.yaml")):
            data = load_yaml(path, {}) or {}
            sid = data.get("id")
            if sid:
                data["_path"] = path.relative_to(SKILL_ROOT).as_posix()
                manifests[str(sid)] = data
    return manifests


def load_version_claims() -> dict[str, dict[str, Any]]:
    raw = load_yaml(DATA_DIR / "version_claims.yaml", {}) or {}
    claims = raw.get("version_claims", raw)
    if isinstance(claims, list):
        return {str(c.get("id")): c for c in claims if isinstance(c, dict) and c.get("id")}
    return claims or {}


def find_page(lookup: str) -> Path | None:
    candidate = SKILL_ROOT / lookup
    if ("/" in lookup or lookup.endswith(".md")) and candidate.exists():
        return candidate
    return page_id_map().get(lookup)


def ensure_workspace_dirs(workspace: Path) -> None:
    for rel in ["docs", ".humanize", "review_rounds", "evidence", "runs", "profile"]:
        (workspace / rel).mkdir(parents=True, exist_ok=True)


def read_task_contract(path: Path) -> dict[str, Any]:
    data = load_yaml(path, {}) or {}
    if not isinstance(data, dict):
        raise SystemExit(f"task contract must be a YAML mapping: {path}")
    return data


@lru_cache(maxsize=None)
def load_project_schema(name: str) -> dict[str, Any]:
    return json.loads((PROJECT_ROOT / "schemas" / name).read_text(encoding="utf-8"))


def schema_error_path(error: jsonschema.ValidationError) -> str:
    return "/".join(str(part) for part in error.path) or "<root>"


def schema_validation_errors(instance: Any, schema_name: str, label: str) -> list[str]:
    validator = jsonschema.Draft202012Validator(load_project_schema(schema_name))
    return [
        f"{label}: schema {schema_error_path(error)}: {error.message}"
        for error in sorted(validator.iter_errors(instance), key=lambda err: list(err.path))
    ]


def normalize_review_issue(issue: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(issue)
    if "severity" in normalized and normalized["severity"] is not None:
        normalized["severity"] = str(normalized["severity"]).upper()
    if "status" in normalized and normalized["status"] is not None:
        normalized["status"] = str(normalized["status"]).lower()
    return normalized


def normalize_review_waiver(waiver: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(waiver)
    if "severity" in normalized and normalized["severity"] is not None:
        normalized["severity"] = str(normalized["severity"]).upper()
    if "status" in normalized and normalized["status"] is not None:
        normalized["status"] = str(normalized["status"]).lower()
    return normalized


def load_review_waivers(workspace: Path) -> tuple[list[dict[str, Any]], set[str], list[str]]:
    waivers = []
    approved = set()
    errors = []
    for idx, waiver in enumerate(load_jsonl(workspace / "review_waivers.jsonl"), 1):
        normalized = normalize_review_waiver(waiver)
        waivers.append(normalized)
        row_errors = schema_validation_errors(
            normalized,
            "review_waiver.schema.json",
            f"review_waivers.jsonl:{idx}",
        )
        errors.extend(row_errors)
        if not row_errors and normalized.get("status") == "approved":
            approved.add(str(normalized.get("issue_id")))
    return waivers, approved, errors


def issue_needs_review_attention(issue: dict[str, Any], approved_waivers: set[str] | None = None) -> bool:
    issue_id = str(issue.get("id", ""))
    severity = str(issue.get("severity", "")).upper()
    status = str(issue.get("status", "open")).lower()
    approved_waivers = approved_waivers or set()
    if status in TERMINAL_STATUSES:
        return False
    if severity == "P2" and status == "waived" and issue_id in approved_waivers:
        return False
    if severity == "P3" and status in DEFERRED_STATUSES:
        return False
    return True


def issue_blocks_promotion(issue: dict[str, Any], approved_waivers: set[str] | None = None) -> bool:
    issue_id = str(issue.get("id", ""))
    severity = str(issue.get("severity", "")).upper()
    status = str(issue.get("status", "open")).lower()
    approved_waivers = approved_waivers or set()
    if severity not in VALID_SEVERITIES or status not in VALID_ISSUE_STATUSES:
        return True
    if status in TERMINAL_STATUSES:
        return False
    if severity in {"P0", "P1"}:
        return True
    if severity == "P2":
        return not (status == "waived" and issue_id in approved_waivers)
    return False


def markdown_list(items: list[str]) -> str:
    if not items:
        return "- None specified\n"
    return "".join(f"- {item}\n" for item in items)
