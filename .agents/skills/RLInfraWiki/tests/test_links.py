import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from _rlinfra import iter_wiki_pages, load_source_manifests


def test_all_wiki_sources_exist():
    sources = load_source_manifests()
    for page in iter_wiki_pages():
        for sid in page.get("sources", []):
            assert sid in sources, f"{page.get('id')} cites unknown {sid}"
