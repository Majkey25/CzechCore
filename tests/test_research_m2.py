from __future__ import annotations

from pathlib import Path

from tools.research.subset_m2 import write_subset


def test_m2_subset_preserves_complete_records(tmp_path: Path) -> None:
    source = tmp_path / "source.m2"
    output = tmp_path / "output.m2"
    source.write_text(
        "S První .\nA -1 -1|||noop|||-NONE-|||REQUIRED|||-NONE-|||0\n\n"
        "S Druhá .\nA 0 1|||R:OTHER|||Jiná|||REQUIRED|||-NONE-|||0\n\n",
        encoding="utf-8",
    )

    count = write_subset(source, output, 1)

    assert count == 1
    assert output.read_text(encoding="utf-8").startswith("S První .\n")
    assert "Druhá" not in output.read_text(encoding="utf-8")
