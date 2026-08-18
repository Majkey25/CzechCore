from __future__ import annotations

from collections import Counter
from pathlib import Path

from tools.research.validate_sources import load_manifest, validate_manifest

ROOT = Path(__file__).parents[1]


def test_research_source_manifest_is_complete_and_valid() -> None:
    sources = validate_manifest(load_manifest(ROOT / "research" / "sources.json"))

    assert len(sources) >= 30
    assert len({source["id"] for source in sources}) == len(sources)


def test_research_source_manifest_covers_required_evidence_kinds() -> None:
    sources = validate_manifest(load_manifest(ROOT / "research" / "sources.json"))
    kinds = Counter(source["kind"] for source in sources)

    assert kinds["pdf"] >= 12
    assert kinds["git"] >= 5
    assert kinds["dataset"] >= 4
    assert kinds["model_card"] >= 5
    assert kinds["collection"] >= 1
