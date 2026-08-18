from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast

from czechcore.core import candidate_is_safe
from tools.research.evaluate_corpus import SentenceMetrics

DEFAULT_THRESHOLDS = (
    0.25,
    0.3,
    0.35,
    0.4,
    0.45,
    0.5,
    0.6,
    0.7,
    0.8,
    0.9,
    0.95,
    0.99,
    0.995,
)


@dataclass(frozen=True, slots=True)
class Diagnostic:
    source: str
    prediction: str
    confidence: float | None


@dataclass(frozen=True, slots=True)
class CalibrationPoint:
    threshold: float
    total: int
    changed: int
    changed_reference_match: int
    changed_precision: float
    coverage: float
    exact: int
    corrected_errors: int
    unchanged_errors: int
    wrong_rewrites: int
    source_correct: int
    false_changes: int
    false_change_rate: float


def _diagnostics(path: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        loaded: object = json.loads(line)
        if not isinstance(loaded, dict):
            raise ValueError(f"diagnostic line {line_number} must be an object")
        record = cast(dict[str, object], loaded)
        source, prediction, raw_confidences = (
            record.get("source"),
            record.get("prediction"),
            record.get("edit_confidences"),
        )
        if not isinstance(source, str) or not isinstance(prediction, str):
            raise ValueError(f"diagnostic line {line_number} has invalid text")
        if not isinstance(raw_confidences, list) or not all(
            isinstance(value, int | float) for value in cast(list[object], raw_confidences)
        ):
            raise ValueError(f"diagnostic line {line_number} has invalid confidences")
        confidences = [float(value) for value in cast(list[int | float], raw_confidences)]
        diagnostics.append(
            Diagnostic(source, prediction, min(confidences) if confidences else None)
        )
    if not diagnostics:
        raise ValueError("diagnostics are empty")
    return diagnostics


def calibrate(
    diagnostics_path: Path,
    gold_path: Path,
    thresholds: Sequence[float],
    prediction_dir: Path | None = None,
    max_changed_ratio: float = 0.35,
) -> tuple[CalibrationPoint, ...]:
    if not thresholds or any(not 0.25 <= threshold <= 1.0 for threshold in thresholds):
        raise ValueError("thresholds must be between the recorded 0.25 floor and 1")
    diagnostics = _diagnostics(diagnostics_path)
    gold = gold_path.read_text(encoding="utf-8").splitlines()
    if len(gold) != len(diagnostics):
        raise ValueError("gold and diagnostics must have the same line count")
    references = [tuple(dict.fromkeys(line.split("\t"))) for line in gold]

    points: list[CalibrationPoint] = []
    if prediction_dir is not None:
        prediction_dir.mkdir(parents=True, exist_ok=True)
    for threshold in thresholds:
        predictions: list[str] = []
        for item in diagnostics:
            candidate = (
                item.prediction
                if item.confidence is not None and item.confidence >= threshold
                else item.source
            )
            predictions.append(
                candidate
                if candidate_is_safe(item.source, candidate, max_changed_ratio)
                else item.source
            )
        metrics = SentenceMetrics()
        changed_reference_match = 0
        for item, refs, prediction in zip(diagnostics, references, predictions, strict=True):
            metrics.add(item.source, refs, prediction)
            changed_reference_match += prediction != item.source and prediction in refs
        changed = sum(
            prediction != item.source
            for item, prediction in zip(diagnostics, predictions, strict=True)
        )
        points.append(
            CalibrationPoint(
                threshold,
                metrics.total,
                changed,
                changed_reference_match,
                changed_reference_match / changed if changed else 1.0,
                changed / metrics.total,
                metrics.exact,
                metrics.corrected_errors,
                metrics.unchanged_errors,
                metrics.wrong_rewrites,
                metrics.source_correct,
                metrics.false_changes,
                metrics.false_changes / metrics.source_correct if metrics.source_correct else 0.0,
            )
        )
        if prediction_dir is not None:
            filename = f"threshold-{threshold:.3f}".replace(".", "_") + ".txt"
            (prediction_dir / filename).write_text(
                "\n".join(predictions) + "\n",
                encoding="utf-8",
            )
    return tuple(points)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build confidence precision/coverage curves")
    parser.add_argument("diagnostics", type=Path)
    parser.add_argument("gold", type=Path)
    parser.add_argument("--thresholds", nargs="+", type=float, default=DEFAULT_THRESHOLDS)
    parser.add_argument("--prediction-dir", type=Path)
    parser.add_argument("--max-changed-ratio", type=float, default=0.35)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args(argv)
    points = calibrate(
        cast(Path, arguments.diagnostics),
        cast(Path, arguments.gold),
        cast(list[float], arguments.thresholds),
        cast(Path | None, arguments.prediction_dir),
        cast(float, arguments.max_changed_ratio),
    )
    rendered = json.dumps([asdict(point) for point in points], ensure_ascii=False, indent=2) + "\n"
    output = cast(Path | None, arguments.output)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
