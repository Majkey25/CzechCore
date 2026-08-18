from __future__ import annotations

from pathlib import Path

from tools.research.evaluate_corpus import evaluate


def test_corpus_evaluation_handles_references_and_domains(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    gold = tmp_path / "gold.txt"
    predictions = tmp_path / "predictions.txt"
    meta = tmp_path / "meta.tsv"
    pointers = tmp_path / "pointers.txt"
    source.write_text("Dobře.\nMuži přišly.\nŽeny šli.\nSprávně.\n", encoding="utf-8")
    gold.write_text(
        "Dobře.\tV pořádku.\nMuži přišli.\nŽeny šly.\n\n",
        encoding="utf-8",
    )
    predictions.write_text(
        "V pořádku.\nMuži přišli.\nŽeny šli.\nŠpatně.\n",
        encoding="utf-8",
    )
    meta.write_text(
        "Filename\tDomain\nfirst\tFormal\nsecond\tInformal\n",
        encoding="utf-8",
    )
    pointers.write_text("first\nfirst\nsecond\nsecond\n", encoding="utf-8")

    report = evaluate(source, gold, predictions, meta, pointers)

    assert report["overall"] == {
        "total": 4,
        "exact": 2,
        "source_correct": 1,
        "false_changes": 1,
        "corrected_errors": 1,
        "unchanged_errors": 1,
        "wrong_rewrites": 1,
    }
