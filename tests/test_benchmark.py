from __future__ import annotations

import json
from pathlib import Path

import pytest

from czechcore.benchmark import evaluate_pairs, load_cases


def test_metrics_count_false_changes_to_correct_sentences() -> None:
    metrics = evaluate_pairs((("Správně.", "Správně.", "Špatně."),))

    assert metrics.total == 1
    assert metrics.source_correct == 1
    assert metrics.changed_correct_sentences == 1
    assert metrics.exact_matches == 0


def test_metrics_separate_corrected_and_unchanged_errors() -> None:
    metrics = evaluate_pairs(
        (
            ("Muži přišly.", "Muži přišli.", "Muži přišli."),
            ("Ženy šli.", "Ženy šly.", "Ženy šli."),
        )
    )

    assert metrics.corrected_incorrect_sentences == 1
    assert metrics.unchanged_incorrect_sentences == 1
    assert metrics.exact_matches == 1


def test_load_cases_validates_jsonl_boundary(tmp_path: Path) -> None:
    path = tmp_path / "cases.jsonl"
    path.write_text(
        json.dumps(
            {"source": "Muži přišly.", "reference": "Muži přišli.", "category": "agreement"}
        ),
        encoding="utf-8",
    )

    cases = load_cases(path)

    assert len(cases) == 1
    assert cases[0].category == "agreement"


def test_load_cases_rejects_missing_string_field(tmp_path: Path) -> None:
    path = tmp_path / "cases.jsonl"
    path.write_text('{"source": "text", "reference": null}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="line 1"):
        load_cases(path)
