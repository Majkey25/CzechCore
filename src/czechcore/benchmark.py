from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Iterable, Sequence
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from time import perf_counter
from typing import Protocol, cast, runtime_checkable

from czechcore.cli import configure_utf8_stdout
from czechcore.core import CorrectionResult
from czechcore.engine import CzechCore


@dataclass(frozen=True, slots=True)
class BenchmarkCase:
    source: str
    reference: str
    category: str

    def __post_init__(self) -> None:
        if not self.source or not self.reference or not self.category:
            raise ValueError("benchmark fields must be non-empty strings")


@dataclass(frozen=True, slots=True)
class BenchmarkMetrics:
    total: int
    exact_matches: int
    source_correct: int
    changed_correct_sentences: int
    corrected_incorrect_sentences: int
    unchanged_incorrect_sentences: int
    wrong_incorrect_predictions: int
    elapsed_seconds: float = 0.0
    mean_latency_ms: float = 0.0


@dataclass(frozen=True, slots=True)
class BenchmarkFailure:
    line: int
    category: str
    source: str
    reference: str
    prediction: str
    kind: str


class Engine(Protocol):
    def correct(
        self,
        text: str,
        *,
        autocorrect: bool = False,
        min_confidence: float = 0.995,
    ) -> CorrectionResult: ...


@runtime_checkable
class BatchEngine(Engine, Protocol):
    def correct_many(
        self,
        texts: Sequence[str],
        *,
        autocorrect: bool = False,
        min_confidence: float = 0.995,
    ) -> tuple[CorrectionResult, ...]: ...


def evaluate_pairs(pairs: Iterable[tuple[str, str, str]]) -> BenchmarkMetrics:
    total = exact = source_correct = changed_correct = corrected = unchanged = wrong = 0
    for source, reference, prediction in pairs:
        total += 1
        exact += prediction == reference
        if source == reference:
            source_correct += 1
            changed_correct += prediction != source
        elif prediction == reference:
            corrected += 1
        elif prediction == source:
            unchanged += 1
        else:
            wrong += 1
    return BenchmarkMetrics(
        total,
        exact,
        source_correct,
        changed_correct,
        corrected,
        unchanged,
        wrong,
    )


def load_cases(path: Path) -> tuple[BenchmarkCase, ...]:
    cases: list[BenchmarkCase] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            loaded = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid benchmark JSON on line {line_number}") from error
        if not isinstance(loaded, dict):
            raise ValueError(f"invalid benchmark object on line {line_number}")
        raw = cast(dict[str, str | None], loaded)
        source, reference, category = (
            raw.get("source"),
            raw.get("reference"),
            raw.get("category"),
        )
        if not isinstance(source, str) or not source:
            raise ValueError(f"invalid benchmark fields on line {line_number}")
        if not isinstance(reference, str) or not reference:
            raise ValueError(f"invalid benchmark fields on line {line_number}")
        if not isinstance(category, str) or not category:
            raise ValueError(f"invalid benchmark fields on line {line_number}")
        cases.append(BenchmarkCase(source, reference, category))
    if not cases:
        raise ValueError("benchmark file contains no cases")
    return tuple(cases)


def run_benchmark(cases: Sequence[BenchmarkCase], engine: Engine) -> BenchmarkMetrics:
    metrics, _ = run_benchmark_details(cases, engine)
    return metrics


def run_benchmark_details(
    cases: Sequence[BenchmarkCase],
    engine: Engine,
    *,
    batch_size: int = 16,
) -> tuple[BenchmarkMetrics, tuple[BenchmarkFailure, ...]]:
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    started = perf_counter()
    sources = [case.source for case in cases]
    results = (
        tuple(
            result
            for offset in range(0, len(sources), batch_size)
            for result in engine.correct_many(sources[offset : offset + batch_size])
        )
        if isinstance(engine, BatchEngine)
        else tuple(engine.correct(source) for source in sources)
    )
    pairs = [
        (case.source, case.reference, result.suggested_text)
        for case, result in zip(cases, results, strict=True)
    ]
    elapsed = perf_counter() - started
    metrics = replace(
        evaluate_pairs(pairs),
        elapsed_seconds=elapsed,
        mean_latency_ms=elapsed * 1000 / len(cases),
    )
    failures = tuple(
        BenchmarkFailure(
            line,
            case.category,
            source,
            reference,
            prediction,
            (
                "false_change"
                if source == reference
                else "unchanged_error"
                if prediction == source
                else "wrong_rewrite"
            ),
        )
        for line, (case, (source, reference, prediction)) in enumerate(
            zip(cases, pairs, strict=True),
            start=1,
        )
        if prediction != reference
    )
    return metrics, failures


def main(
    argv: Sequence[str] | None = None,
    *,
    engine_factory: Callable[[], Engine] | None = None,
) -> int:
    configure_utf8_stdout()
    parser = argparse.ArgumentParser(prog="czechcore-benchmark")
    parser.add_argument("path", type=Path)
    parser.add_argument("--details", action="store_true")
    parser.add_argument("--suggestion-min-confidence", type=float, default=0.25)
    parser.add_argument("--max-changed-ratio", type=float, default=0.35)
    parser.add_argument("--batch-size", type=int, default=16)
    arguments = parser.parse_args(argv)
    cases = load_cases(cast(Path, arguments.path))
    engine = (
        engine_factory()
        if engine_factory is not None
        else CzechCore(
            suggestion_min_confidence=cast(float, arguments.suggestion_min_confidence),
            max_changed_ratio=cast(float, arguments.max_changed_ratio),
        )
    )
    metrics, failures = run_benchmark_details(
        cases,
        engine,
        batch_size=cast(int, arguments.batch_size),
    )
    report: object = (
        {"metrics": asdict(metrics), "failures": [asdict(item) for item in failures]}
        if arguments.details
        else asdict(metrics)
    )
    print(json.dumps(report, ensure_ascii=False))
    return 0
