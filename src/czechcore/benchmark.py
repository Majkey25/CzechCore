from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Iterable, Sequence
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from time import perf_counter
from typing import Protocol, cast

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


class Engine(Protocol):
    def correct(
        self,
        text: str,
        *,
        autocorrect: bool = False,
        min_confidence: float = 0.995,
    ) -> CorrectionResult: ...


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
    started = perf_counter()
    pairs = [
        (case.source, case.reference, engine.correct(case.source).suggested_text) for case in cases
    ]
    elapsed = perf_counter() - started
    return replace(
        evaluate_pairs(pairs),
        elapsed_seconds=elapsed,
        mean_latency_ms=elapsed * 1000 / len(cases),
    )


def main(
    argv: Sequence[str] | None = None,
    *,
    engine_factory: Callable[[], Engine] = CzechCore,
) -> int:
    parser = argparse.ArgumentParser(prog="czechcore-benchmark")
    parser.add_argument("path", type=Path)
    arguments = parser.parse_args(argv)
    cases = load_cases(cast(Path, arguments.path))
    metrics = run_benchmark(cases, engine_factory())
    print(json.dumps(asdict(metrics), ensure_ascii=False))
    return 0
