from pathlib import Path
import json
import jsonschema

ROOT = Path(__file__).resolve().parents[4]


def test_json_schemas_are_valid():
    for path in (ROOT / "schemas").glob("*.json"):
        jsonschema.Draft202012Validator.check_schema(json.loads(path.read_text()))


def test_verified_wiki_schema_requires_context_and_artifact_evidence():
    schema = json.loads((ROOT / "schemas" / "wiki_page.schema.json").read_text())
    validator = jsonschema.Draft202012Validator(schema)
    instance = {
        "id": "test-page",
        "title": "Test Page",
        "type": "pattern",
        "confidence": "verified",
        "reproducibility": "local",
        "sources": ["source-test"],
        "summary": "Test summary",
        "updated_at": "2026-06-12",
        "local_evidence": {
            "command": "pytest",
            "commit": "abc123",
            "result": "passed",
            "log": "evidence/test.log",
        },
    }
    assert list(validator.iter_errors(instance))
    instance["local_evidence"]["context"] = "local CPU run"
    assert not list(validator.iter_errors(instance))
