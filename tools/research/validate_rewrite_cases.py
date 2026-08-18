from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import cast


def _strings(value: object, field: str, line: int) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"line {line}: {field} must be a string list")
    strings: list[str] = []
    for item in cast(list[object], value):
        if not isinstance(item, str) or not item:
            raise ValueError(f"line {line}: {field} must contain non-empty strings")
        strings.append(item)
    return strings


def validate_cases(path: Path) -> dict[str, int]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise ValueError("rewrite benchmark is empty")
    categories: set[str] = set()
    risk_tags: set[str] = set()
    for line_number, line in enumerate(lines, start=1):
        loaded: object = json.loads(line)
        if not isinstance(loaded, dict):
            raise ValueError(f"line {line_number}: case must be an object")
        case = cast(dict[str, object], loaded)
        source = case.get("source")
        category = case.get("category")
        if not isinstance(source, str) or not source:
            raise ValueError(f"line {line_number}: source must be non-empty")
        if not isinstance(category, str) or not category:
            raise ValueError(f"line {line_number}: category must be non-empty")
        references = _strings(case.get("references"), "references", line_number)
        protected = _strings(case.get("protected_literals"), "protected_literals", line_number)
        tags = _strings(case.get("risk_tags"), "risk_tags", line_number)
        if not references or not tags:
            raise ValueError(f"line {line_number}: references and risk_tags must be non-empty")
        for literal in protected:
            if literal not in source or any(literal not in reference for reference in references):
                raise ValueError(
                    f"line {line_number}: protected literal must occur in source and references"
                )
        categories.add(category)
        risk_tags.update(tags)
    return {"cases": len(lines), "categories": len(categories), "risk_tags": len(risk_tags)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate semantic rewrite benchmark")
    parser.add_argument(
        "path", type=Path, nargs="?", default=Path("benchmarks/rewrite_cases.jsonl")
    )
    arguments = parser.parse_args(argv)
    print(json.dumps(validate_cases(cast(Path, arguments.path)), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
