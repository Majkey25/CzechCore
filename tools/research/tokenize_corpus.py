from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, cast

from czechcore.tokenizer import CzechTokenizer, SentenceSpan


class Tokenizer(Protocol):
    def sentences(self, text: str) -> tuple[SentenceSpan, ...]: ...


def tokenize_file(source: Path, output: Path, tokenizer: Tokenizer) -> int:
    lines = source.read_text(encoding="utf-8").splitlines()
    if not lines or any(not line for line in lines):
        raise ValueError("source corpus must contain non-empty lines")
    tokenized = [" ".join(span.tokenized for span in tokenizer.sentences(line)) for line in lines]
    if any(not line for line in tokenized):
        raise ValueError("tokenizer produced an empty line")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(tokenized) + "\n", encoding="utf-8")
    return len(tokenized)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="UDPipe-tokenize a sentence-per-line corpus")
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args(argv)
    print(
        tokenize_file(
            cast(Path, arguments.source),
            cast(Path, arguments.output),
            CzechTokenizer(),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
