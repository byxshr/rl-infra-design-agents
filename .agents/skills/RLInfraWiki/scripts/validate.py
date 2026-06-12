#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import jsonschema
from _rlinfra import CONFIDENCE_LEVELS, DATA_DIR, PROJECT_ROOT, SKILL_ROOT, load_source_manifests, load_version_claims, load_yaml, split_frontmatter

REQUIRED_PAGE_FIELDS = ["id", "title", "type", "confidence", "reproducibility", "sources", "summary", "updated_at"]
REQUIRED_SOURCE_FIELDS = ["id", "name", "source_category", "status", "trust_level", "captured_at"]


def validate_schemas(errors):
    schemas = {}
    for path in sorted((PROJECT_ROOT / "schemas").glob("*.json")):
        try:
            schema = json.loads(path.read_text(encoding="utf-8"))
            jsonschema.Draft202012Validator.check_schema(schema)
            schemas[path.name] = schema
        except Exception as exc:
            errors.append(f"{path.relative_to(PROJECT_ROOT)}: invalid JSON schema: {exc}")
    return schemas


def schema_path(error):
    return "/".join(str(part) for part in error.path) or "<root>"


def add_schema_errors(errors, rel, validator, instance):
    for error in sorted(validator.iter_errors(instance), key=lambda err: list(err.path)):
        errors.append(f"{rel}: schema {schema_path(error)}: {error.message}")


def validate_local_evidence(rel, fm, errors):
    if fm.get("confidence") != "verified":
        return
    evidence = fm.get("local_evidence")
    if not isinstance(evidence, dict):
        errors.append(f"{rel}: verified claim requires local_evidence object")
        return
    for field in ["command", "commit", "result"]:
        if not evidence.get(field):
            errors.append(f"{rel}: verified local_evidence missing {field}")
    if not (evidence.get("hardware") or evidence.get("context")):
        errors.append(f"{rel}: verified local_evidence requires hardware or context")
    if not (evidence.get("log") or evidence.get("artifact_path")):
        errors.append(f"{rel}: verified local_evidence requires log or artifact_path")


def validate_sources(errors, schemas):
    validator = jsonschema.Draft202012Validator(schemas.get("source.schema.json", {}))
    seen = set()
    for sid, source in load_source_manifests().items():
        if sid in seen:
            errors.append(f"duplicate source id: {sid}")
        seen.add(sid)
        add_schema_errors(errors, source.get("_path", sid), validator, source)
        for field in REQUIRED_SOURCE_FIELDS:
            if field not in source or source[field] in (None, ""):
                errors.append(f"{source.get('_path', sid)}: missing source field {field}")
    if not seen:
        errors.append("no source manifests found")


def validate_wiki(errors, schemas):
    validator = jsonschema.Draft202012Validator(schemas.get("wiki_page.schema.json", {}))
    sources = load_source_manifests()
    version_claims = load_version_claims()
    seen_ids = set()
    for path in sorted((SKILL_ROOT / "wiki").rglob("*.md")):
        if path.name == "README.md":
            continue
        fm, body = split_frontmatter(path)
        rel = path.relative_to(SKILL_ROOT)
        if not fm:
            errors.append(f"{rel}: missing or invalid YAML frontmatter")
            continue
        add_schema_errors(errors, rel, validator, fm)
        pid = fm.get("id")
        if pid in seen_ids:
            errors.append(f"{rel}: duplicate page id {pid}")
        seen_ids.add(pid)
        for field in REQUIRED_PAGE_FIELDS:
            if field not in fm or fm[field] in (None, ""):
                errors.append(f"{rel}: missing required field {field}")
        if fm.get("confidence") not in CONFIDENCE_LEVELS:
            errors.append(f"{rel}: invalid confidence {fm.get('confidence')}")
        validate_local_evidence(rel, fm, errors)
        if not isinstance(fm.get("sources", []), list) or not fm.get("sources"):
            errors.append(f"{rel}: sources must be a non-empty list")
        for sid in fm.get("sources", []) or []:
            if sid not in sources:
                errors.append(f"{rel}: unknown source id {sid}")
        for vid in fm.get("version_sensitive", []) or []:
            if vid not in version_claims:
                errors.append(f"{rel}: unknown version claim id {vid}")
        for list_field in ["frameworks", "backends", "components", "algorithms", "deployment_modes", "tags", "risks"]:
            if list_field in fm and not isinstance(fm[list_field], list):
                errors.append(f"{rel}: {list_field} must be a list")
        if not body.strip():
            errors.append(f"{rel}: empty body")


def validate_data(errors):
    tags = load_yaml(DATA_DIR / "tags.yaml", {}) or {}
    for key in ["frameworks", "backends", "components", "algorithms", "deployment_modes", "confidence", "risks"]:
        if key not in tags:
            errors.append(f"data/tags.yaml: missing {key}")
    version_claims = load_version_claims()
    sources = load_source_manifests()
    for vid, claim in version_claims.items():
        for sid in claim.get("source_ids", []) or []:
            if sid not in sources:
                errors.append(f"data/version_claims.yaml:{vid}: unknown source id {sid}")


def validate_contracts(errors, schemas):
    validator = jsonschema.Draft202012Validator(schemas.get("task_contract.schema.json", {}))
    required = ["task_name", "objective", "deliverables", "required_wiki_queries", "promotion_criteria"]
    for path in sorted((PROJECT_ROOT / "examples" / "task_contracts").glob("*.yaml")):
        data = load_yaml(path, {}) or {}
        add_schema_errors(errors, path.relative_to(PROJECT_ROOT), validator, data)
        for field in required:
            if field not in data:
                errors.append(f"{path.relative_to(PROJECT_ROOT)}: missing {field}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate RLInfraWiki files")
    parser.parse_args()
    errors = []
    schemas = validate_schemas(errors)
    validate_sources(errors, schemas)
    validate_data(errors)
    validate_wiki(errors, schemas)
    validate_contracts(errors, schemas)
    if errors:
        print(f"ERROR: {len(errors)} validation issue(s)")
        for err in errors:
            print(f"  - {err}")
        return 1
    print("RLInfraWiki validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
