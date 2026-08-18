from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from czechcore.core import candidate_is_safe


def apply_safety(source_path: Path, candidate_path: Path, output_path: Path, ratio: float) -> int:
    sources = source_path.read_text(encoding="utf-8").splitlines()
    candidates = candidate_path.read_text(encoding="utf-8").splitlines()
    if not sources or len(sources) != len(candidates):
        raise ValueError("source and candidate files must have the same non-zero line count")
    accepted = [
        candidate if candidate_is_safe(source, candidate, ratio) else source
        for source, candidate in zip(sources, candidates, strict=True)
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(accepted) + "\n", encoding="utf-8")
    return sum(candidate != result for candidate, result in zip(candidates, accepted, strict=True))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply current CzechCore safety to candidates")
    parser.add_argument("source", type=Path)
    parser.add_argument("candidates", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--max-changed-ratio", type=float, default=0.35)
    arguments = parser.parse_args(argv)
    rejected = apply_safety(
        cast(Path, arguments.source),
        cast(Path, arguments.candidates),
        cast(Path, arguments.output),
        cast(float, arguments.max_changed_ratio),
    )
    print(json.dumps({"rejected": rejected}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
