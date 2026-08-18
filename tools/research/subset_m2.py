from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
from typing import cast


def write_subset(source: Path, output: Path, limit: int) -> int:
    if limit <= 0:
        raise ValueError("limit must be positive")
    records = source.read_text(encoding="utf-8").strip().split("\n\n")
    if not records or any(not record.startswith("S ") for record in records):
        raise ValueError("invalid M2 corpus")
    selected = records[:limit]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n\n".join(selected) + "\n\n", encoding="utf-8")
    return len(selected)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Copy the first N records from an M2 corpus")
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("limit", type=int)
    arguments = parser.parse_args(argv)
    count = write_subset(
        cast(Path, arguments.source),
        cast(Path, arguments.output),
        cast(int, arguments.limit),
    )
    print(count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
