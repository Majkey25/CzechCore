from __future__ import annotations

import pytest

from czechcore.core import (
    CorrectionKind,
    TextEdit,
    apply_edits,
    candidate_is_safe,
    extract_edits,
    protected_literals,
    remove_adjacent_repeated_words,
)


def test_extracts_diacritics_and_punctuation_with_original_offsets() -> None:
    source = "Rekl ze prijde."

    edits = extract_edits(source, "Řekl, že přijde.", confidence=0.99, applied=False)

    assert apply_edits(source, edits) == "Řekl, že přijde."
    assert [edit.kind for edit in edits] == [
        CorrectionKind.DIACRITICS,
        CorrectionKind.PUNCTUATION,
        CorrectionKind.DIACRITICS,
        CorrectionKind.DIACRITICS,
    ]
    assert [(edit.start, edit.end, edit.source) for edit in edits] == [
        (0, 1, "R"),
        (4, 4, ""),
        (5, 6, "z"),
        (9, 10, "r"),
    ]


@pytest.mark.parametrize(
    ("source", "replacement", "kind"),
    [
        ("ahoj", "Ahoj", CorrectionKind.CAPITALIZATION),
        ("ahoj  světe", "ahoj světe", CorrectionKind.WHITESPACE),
        ("přišly", "přišli", CorrectionKind.GRAMMAR),
    ],
)
def test_classifies_mechanical_edits(
    source: str,
    replacement: str,
    kind: CorrectionKind,
) -> None:
    edits = extract_edits(source, replacement, confidence=0.8, applied=True)

    assert len(edits) == 1
    assert edits[0].kind is kind
    assert edits[0].applied


def test_apply_edits_rejects_source_mismatch() -> None:
    edit = TextEdit(0, 1, "x", "y", CorrectionKind.GRAMMAR, 0.9, False)

    with pytest.raises(ValueError, match="source text"):
        apply_edits("a", (edit,))


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_edit_rejects_invalid_confidence(confidence: float) -> None:
    with pytest.raises(ValueError, match="confidence"):
        TextEdit(0, 0, "", ",", CorrectionKind.PUNCTUATION, confidence, False)


def test_extract_edits_returns_empty_for_unchanged_text() -> None:
    assert extract_edits("Byli doma.", "Byli doma.", confidence=1.0, applied=False) == ()


@pytest.mark.parametrize(
    ("source", "candidate"),
    [
        ("Piš na majkey25@example.cz.", "Piš na majkey25 @ example.cz."),
        ("Použij C++20.", "Použij C + + 20."),
        ("Verze je v1.2.3.", "Verze je v 1.2.3."),
        ("Otevři C:\\Data\\text.txt.", "Otevři C: Data text.txt."),
    ],
)
def test_rejects_candidate_that_changes_protected_literal(source: str, candidate: str) -> None:
    assert not candidate_is_safe(source, candidate, max_changed_ratio=0.35)


def test_detects_protected_literals_in_source_order() -> None:
    text = "CzechCore 1.2.3: https://example.cz piš na majkey25@example.cz a použij C++20."

    assert protected_literals(text) == (
        "CzechCore",
        "1.2.3",
        "https://example.cz",
        "majkey25@example.cz",
        "C++20",
    )


def test_accepts_small_correction_that_preserves_protected_literals() -> None:
    source = "Projekt CzechCore použival verzi v1.2.3."
    candidate = "Projekt CzechCore používal verzi v1.2.3."

    assert candidate_is_safe(source, candidate, max_changed_ratio=0.35)


def test_rejects_large_rewrite_and_empty_candidate() -> None:
    assert not candidate_is_safe("Toto je věta.", "Úplně jiný dlouhý text.", 0.35)
    assert not candidate_is_safe("Toto je věta.", "", 0.35)


def test_removes_exact_adjacent_repeated_word() -> None:
    assert remove_adjacent_repeated_words("To je je vážný problém.") == "To je vážný problém."


def test_keeps_rhetorical_repetition_separated_by_punctuation() -> None:
    assert remove_adjacent_repeated_words("Velmi, velmi dobře.") == "Velmi, velmi dobře."
