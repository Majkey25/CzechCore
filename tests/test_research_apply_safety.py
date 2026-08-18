from __future__ import annotations

from pathlib import Path

from tools.research.apply_safety import apply_safety


def test_apply_safety_reverts_only_unsafe_candidates(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    candidates = tmp_path / "candidates.txt"
    output = tmp_path / "output.txt"
    source.write_text("Zavolej na 777 123 456.\nDúm stojí.\n", encoding="utf-8")
    candidates.write_text("Zavolej na 777, 123, 456.\nDům stojí.\n", encoding="utf-8")

    rejected = apply_safety(source, candidates, output, 0.35)

    assert rejected == 1
    assert output.read_text(encoding="utf-8").splitlines() == [
        "Zavolej na 777 123 456.",
        "Dům stojí.",
    ]
