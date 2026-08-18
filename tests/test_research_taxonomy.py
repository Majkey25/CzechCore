from __future__ import annotations

from pathlib import Path
from typing import cast

from tools.research.validate_taxonomy import load_json, validate_taxonomy

ROOT = Path(__file__).parents[1]


def test_research_taxonomy_covers_all_authoritative_sections_and_corpus_types() -> None:
    summary = validate_taxonomy(
        taxonomy=load_json(ROOT / "research" / "taxonomy.json"),
        ijc_outline=load_json(ROOT / "research" / "ijc-outline.json"),
        geccc=load_json(ROOT / "research" / "geccc-error-types.json"),
    )

    assert summary["families"] >= 12
    assert summary["phenomena"] >= 60
    assert summary["ijc_sections"] == 22
    assert summary["ijc_rules"] == 202
    assert summary["geccc_error_types"] == 65


def test_correction_taxonomy_requires_positive_negative_and_ambiguity_evidence() -> None:
    taxonomy = load_json(ROOT / "research" / "taxonomy.json")
    families = taxonomy["families"]
    assert isinstance(families, list)

    for raw_family in cast(list[object], families):
        assert isinstance(raw_family, dict)
        family = cast(dict[str, object], raw_family)
        if family["scope"] == "correction":
            evidence = family["required_evidence"]
            assert isinstance(evidence, list)
            assert set(cast(list[str], evidence)) == {"positive", "negative", "ambiguity"}
