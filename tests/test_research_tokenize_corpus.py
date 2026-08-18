from __future__ import annotations

from pathlib import Path

from czechcore.tokenizer import SentenceSpan
from tools.research.tokenize_corpus import tokenize_file


class SpaceTokenizer:
    def sentences(self, text: str) -> tuple[SentenceSpan, ...]:
        return (SentenceSpan(0, len(text), text.replace(".", " .")),)


def test_tokenize_file_preserves_line_alignment(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    output = tmp_path / "output.txt"
    source.write_text("První.\nDruhá.\n", encoding="utf-8")

    count = tokenize_file(source, output, SpaceTokenizer())

    assert count == 2
    assert output.read_text(encoding="utf-8").splitlines() == ["První .", "Druhá ."]
