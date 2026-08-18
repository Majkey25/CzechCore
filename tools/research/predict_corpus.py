from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from contextlib import ExitStack
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import cast

from czechcore.benchmark import BatchEngine, Engine
from czechcore.engine import CzechCore


@dataclass(frozen=True, slots=True)
class PredictionSummary:
    sentences: int
    changed: int
    warnings: int
    elapsed_seconds: float
    mean_latency_ms: float


def predict_file(
    source_path: Path,
    output_path: Path,
    engine: Engine,
    *,
    limit: int | None = None,
    source_copy: Path | None = None,
    batch_size: int = 16,
    diagnostics_path: Path | None = None,
) -> PredictionSummary:
    if limit is not None and limit <= 0:
        raise ValueError("limit must be positive")
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    sources = source_path.read_text(encoding="utf-8").splitlines()
    if limit is not None:
        sources = sources[:limit]
    if not sources or any(not source for source in sources):
        raise ValueError("source corpus must contain non-empty lines")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if source_copy is not None:
        source_copy.parent.mkdir(parents=True, exist_ok=True)
        source_copy.write_text("\n".join(sources) + "\n", encoding="utf-8")
    if diagnostics_path is not None:
        diagnostics_path.parent.mkdir(parents=True, exist_ok=True)

    started = perf_counter()
    changed = warnings = 0
    with ExitStack() as stack:
        output = stack.enter_context(output_path.open("w", encoding="utf-8", newline="\n"))
        diagnostics = (
            stack.enter_context(diagnostics_path.open("w", encoding="utf-8", newline="\n"))
            if diagnostics_path is not None
            else None
        )
        for offset in range(0, len(sources), batch_size):
            batch = sources[offset : offset + batch_size]
            if isinstance(engine, BatchEngine):
                results = engine.correct_many(batch)
            else:
                results = tuple(engine.correct(source) for source in batch)
            for index, (source, result) in enumerate(
                zip(batch, results, strict=True),
                start=offset + 1,
            ):
                output.write(result.suggested_text + "\n")
                changed += result.suggested_text != source
                warnings += len(result.warnings)
                if diagnostics is not None:
                    diagnostics.write(
                        json.dumps(
                            {
                                "line": index,
                                "source": source,
                                "prediction": result.suggested_text,
                                "warnings": result.warnings,
                                "edit_confidences": [edit.confidence for edit in result.edits],
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
            output.flush()
            if diagnostics is not None:
                diagnostics.flush()
    elapsed = perf_counter() - started
    return PredictionSummary(
        len(sources),
        changed,
        warnings,
        elapsed,
        elapsed * 1000 / len(sources),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate one CzechCore prediction per input line")
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--source-copy", type=Path)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--diagnostics", type=Path)
    parser.add_argument("--suggestion-min-confidence", type=float, default=0.25)
    parser.add_argument("--max-changed-ratio", type=float, default=0.35)
    arguments = parser.parse_args(argv)
    summary = predict_file(
        cast(Path, arguments.source),
        cast(Path, arguments.output),
        CzechCore(
            suggestion_min_confidence=cast(float, arguments.suggestion_min_confidence),
            max_changed_ratio=cast(float, arguments.max_changed_ratio),
        ),
        limit=cast(int | None, arguments.limit),
        source_copy=cast(Path | None, arguments.source_copy),
        batch_size=cast(int, arguments.batch_size),
        diagnostics_path=cast(Path | None, arguments.diagnostics),
    )
    print(json.dumps(asdict(summary), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
