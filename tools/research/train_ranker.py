from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from math import exp, log, sqrt
from pathlib import Path
from typing import cast
from unicodedata import category, normalize

from czechcore.core import candidate_is_safe

_WORD = re.compile(r"(?u)[^\W\d_]+")
FEATURE_NAMES = (
    "beam_confidence",
    "source_length",
    "length_ratio",
    "changed_ratio",
    "opcode_count",
    "inserted_ratio",
    "deleted_ratio",
    "source_word_count",
    "word_count_delta",
    "diacritics_only",
    "case_only",
    "punctuation_delta",
    "digit_delta",
    "source_known_ratio",
    "candidate_known_ratio",
    "same_lemma_ratio",
    "different_lemma_ratio",
    "unknown_to_known_ratio",
    "same_pos_ratio",
)


@dataclass(frozen=True, slots=True)
class Candidate:
    pointer: str
    source: str
    prediction: str
    confidence: float
    label: float
    features: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class SelectionMetrics:
    threshold: float
    eligible: int
    accepted: int
    correct: int
    precision: float
    coverage: float
    recall: float


@dataclass(frozen=True, slots=True)
class LogisticRanker:
    weights: tuple[float, ...]
    bias: float
    mean: tuple[float, ...]
    std: tuple[float, ...]

    def score(self, features: Sequence[float]) -> float:
        normalized = [
            (value - mean) / std
            for value, mean, std in zip(features, self.mean, self.std, strict=True)
        ]
        value = self.bias + sum(
            weight * feature for weight, feature in zip(self.weights, normalized, strict=True)
        )
        return _sigmoid(value)


class Morphology:
    def __init__(self, path: Path) -> None:
        from ufal.morphodita import Morpho, TaggedLemmas

        model = Morpho.load(str(path))
        if model is None:
            raise RuntimeError(f"cannot load MorphoDiTa dictionary: {path}")
        self._model = model
        self._lemmas_factory = TaggedLemmas
        self._cache: dict[str, tuple[tuple[str, str], ...]] = {}

    def analyze(self, word: str) -> tuple[tuple[str, str], ...]:
        if word in self._cache:
            return self._cache[word]
        lemmas = self._lemmas_factory()
        status = self._model.analyze(word, self._model.NO_GUESSER, lemmas)
        result = (
            ()
            if status < 0
            else tuple((self._model.rawLemma(item.lemma), item.tag) for item in lemmas)
        )
        if len(self._cache) >= 50_000:
            self._cache.clear()
        self._cache[word] = result
        return result


def _without_diacritics(text: str) -> str:
    return "".join(char for char in normalize("NFD", text) if category(char) != "Mn")


def _word_features(
    source: str,
    candidate: str,
    morphology: Morphology,
) -> tuple[float, ...]:
    source_words = _WORD.findall(source)
    candidate_words = _WORD.findall(candidate)
    pairs: list[tuple[str, str]] = []
    for operation, i1, i2, j1, j2 in SequenceMatcher(
        None,
        [word.casefold() for word in source_words],
        [word.casefold() for word in candidate_words],
        autojunk=False,
    ).get_opcodes():
        if operation == "replace" and i2 - i1 == j2 - j1:
            pairs.extend(zip(source_words[i1:i2], candidate_words[j1:j2], strict=True))
    if not pairs:
        return (0.0,) * 6

    source_known = candidate_known = same_lemma = different_lemma = unknown_to_known = same_pos = 0
    for source_word, candidate_word in pairs:
        source_analyses = morphology.analyze(source_word)
        candidate_analyses = morphology.analyze(candidate_word)
        source_known += bool(source_analyses)
        candidate_known += bool(candidate_analyses)
        if not source_analyses and candidate_analyses:
            unknown_to_known += 1
        source_lemmas = {lemma for lemma, _ in source_analyses}
        candidate_lemmas = {lemma for lemma, _ in candidate_analyses}
        if source_lemmas and candidate_lemmas:
            if source_lemmas & candidate_lemmas:
                same_lemma += 1
            else:
                different_lemma += 1
            source_pos = {tag[:1] for _, tag in source_analyses}
            candidate_pos = {tag[:1] for _, tag in candidate_analyses}
            same_pos += bool(source_pos & candidate_pos)
    count = len(pairs)
    return tuple(
        value / count
        for value in (
            source_known,
            candidate_known,
            same_lemma,
            different_lemma,
            unknown_to_known,
            same_pos,
        )
    )


def extract_features(
    source: str,
    candidate: str,
    confidence: float,
    morphology: Morphology,
) -> tuple[float, ...]:
    opcodes = SequenceMatcher(None, source, candidate, autojunk=False).get_opcodes()
    changed = inserted = deleted = 0
    for operation, i1, i2, j1, j2 in opcodes:
        if operation == "equal":
            continue
        changed += max(i2 - i1, j2 - j1)
        inserted += max(0, (j2 - j1) - (i2 - i1))
        deleted += max(0, (i2 - i1) - (j2 - j1))
    source_words = _WORD.findall(source)
    candidate_words = _WORD.findall(candidate)
    source_length = max(len(source), 1)
    morph = _word_features(source, candidate, morphology)
    return (
        confidence,
        min(len(source) / 512, 1.0),
        len(candidate) / source_length,
        changed / source_length,
        min((len(opcodes) - 1) / 20, 1.0),
        inserted / source_length,
        deleted / source_length,
        min(len(source_words) / 100, 1.0),
        min(abs(len(candidate_words) - len(source_words)) / 20, 1.0),
        float(_without_diacritics(source) == _without_diacritics(candidate)),
        float(source.casefold() == candidate.casefold()),
        min(
            abs(
                sum(category(char).startswith("P") for char in candidate)
                - sum(category(char).startswith("P") for char in source)
            )
            / 20,
            1.0,
        ),
        min(
            abs(sum(char.isdigit() for char in candidate) - sum(char.isdigit() for char in source))
            / 10,
            1.0,
        ),
        *morph,
    )


def _load_candidates(
    diagnostics_path: Path,
    gold_path: Path,
    pointers_path: Path,
    morphology: Morphology,
) -> list[Candidate]:
    diagnostics = diagnostics_path.read_text(encoding="utf-8").splitlines()
    gold = gold_path.read_text(encoding="utf-8").splitlines()
    pointers = pointers_path.read_text(encoding="utf-8").splitlines()
    if len({len(diagnostics), len(gold), len(pointers)}) != 1:
        raise ValueError("diagnostics, gold, and pointers must have the same line count")
    candidates: list[Candidate] = []
    for line_number, (raw, raw_gold, pointer) in enumerate(
        zip(diagnostics, gold, pointers, strict=True),
        start=1,
    ):
        loaded: object = json.loads(raw)
        if not isinstance(loaded, dict):
            raise ValueError(f"diagnostic line {line_number} must be an object")
        record = cast(dict[str, object], loaded)
        source, prediction, raw_confidences = (
            record.get("source"),
            record.get("prediction"),
            record.get("edit_confidences"),
        )
        if (
            not isinstance(source, str)
            or not isinstance(prediction, str)
            or not isinstance(raw_confidences, list)
        ):
            raise ValueError(f"diagnostic line {line_number} has invalid fields")
        confidences: list[float] = []
        for value in cast(list[object], raw_confidences):
            if isinstance(value, bool) or not isinstance(value, int | float):
                raise ValueError(f"diagnostic line {line_number} has invalid confidence")
            confidences.append(float(value))
        if (
            not confidences
            or prediction == source
            or not candidate_is_safe(source, prediction, 0.35)
        ):
            continue
        references = raw_gold.split("\t")
        confidence = min(confidences)
        features = extract_features(source, prediction, confidence, morphology)
        candidates.append(
            Candidate(
                pointer,
                source,
                prediction,
                confidence,
                float(prediction in references),
                features,
            )
        )
    if not candidates:
        raise ValueError("no changed candidates available")
    return candidates


def split_name(pointer: str) -> str:
    bucket = hashlib.sha256(pointer.encode()).digest()[0]
    if bucket < 180:
        return "train"
    if bucket < 230:
        return "calibration"
    return "validation"


def choose_threshold(
    scores: Sequence[float],
    labels: Sequence[float],
    target_precision: float,
    min_accepted: int,
) -> float:
    best = 1.0
    best_count = 0
    for threshold in sorted(set(scores), reverse=True):
        selected = [
            label for score, label in zip(scores, labels, strict=True) if score >= threshold
        ]
        if len(selected) < min_accepted:
            continue
        precision = sum(selected) / len(selected)
        if precision >= target_precision and len(selected) > best_count:
            best = threshold
            best_count = len(selected)
    return best


def selection_metrics(
    scores: Sequence[float],
    labels: Sequence[float],
    threshold: float,
) -> SelectionMetrics:
    selected = [label for score, label in zip(scores, labels, strict=True) if score >= threshold]
    positives = sum(labels)
    correct = int(sum(selected))
    return SelectionMetrics(
        threshold,
        len(labels),
        len(selected),
        correct,
        correct / len(selected) if selected else 1.0,
        len(selected) / len(labels) if labels else 0.0,
        correct / positives if positives else 0.0,
    )


def best_precision_metrics(
    scores: Sequence[float],
    labels: Sequence[float],
    min_accepted: int,
) -> SelectionMetrics:
    best: SelectionMetrics | None = None
    for threshold in sorted(set(scores), reverse=True):
        metrics = selection_metrics(scores, labels, threshold)
        if metrics.accepted < min_accepted:
            continue
        if (
            best is None
            or metrics.precision > best.precision
            or (metrics.precision == best.precision and metrics.accepted > best.accepted)
        ):
            best = metrics
    return best or selection_metrics(scores, labels, 1.0)


def _sigmoid(value: float) -> float:
    if value >= 0:
        return 1 / (1 + exp(-value))
    exponential = exp(value)
    return exponential / (1 + exponential)


def _mean_std(items: Sequence[Candidate]) -> tuple[tuple[float, ...], tuple[float, ...]]:
    count = len(items)
    mean = tuple(
        sum(item.features[index] for item in items) / count for index in range(len(FEATURE_NAMES))
    )
    std = tuple(
        max(
            sqrt(sum((item.features[index] - mean[index]) ** 2 for item in items) / count),
            1e-6,
        )
        for index in range(len(FEATURE_NAMES))
    )
    return mean, std


def _train_logistic(
    items: Sequence[Candidate],
    epochs: int,
    learning_rate: float,
) -> LogisticRanker:
    mean, std = _mean_std(items)
    normalized = [
        tuple((feature - mean[index]) / std[index] for index, feature in enumerate(item.features))
        for item in items
    ]
    weights = [0.0] * len(FEATURE_NAMES)
    positives = sum(item.label for item in items)
    prevalence = min(max(positives / len(items), 1e-6), 1 - 1e-6)
    bias = log(prevalence / (1 - prevalence))
    for _ in range(epochs):
        weight_gradient = [0.0] * len(weights)
        bias_gradient = 0.0
        for item, features in zip(items, normalized, strict=True):
            probability = _sigmoid(
                bias
                + sum(weight * feature for weight, feature in zip(weights, features, strict=True))
            )
            error = probability - item.label
            bias_gradient += error
            for index, feature in enumerate(features):
                weight_gradient[index] += error * feature
        scale = learning_rate / len(items)
        bias -= scale * bias_gradient
        for index, gradient in enumerate(weight_gradient):
            weights[index] -= scale * gradient + learning_rate * 0.001 * weights[index]
    return LogisticRanker(tuple(weights), bias, mean, std)


def train_and_evaluate(
    candidates: Sequence[Candidate],
    target_precision: float,
    epochs: int,
    learning_rate: float,
) -> tuple[LogisticRanker, dict[str, object]]:
    splits = {
        name: [candidate for candidate in candidates if split_name(candidate.pointer) == name]
        for name in ("train", "calibration", "validation")
    }
    if any(not items for items in splits.values()):
        raise ValueError("all ranker splits must be non-empty")
    model = _train_logistic(splits["train"], epochs, learning_rate)
    calibration_scores = [model.score(item.features) for item in splits["calibration"]]
    validation_scores = [model.score(item.features) for item in splits["validation"]]
    calibration_labels = [item.label for item in splits["calibration"]]
    validation_labels = [item.label for item in splits["validation"]]
    ranker_threshold = choose_threshold(
        calibration_scores,
        calibration_labels,
        target_precision,
        min_accepted=20,
    )

    confidence_calibration = [item.confidence for item in splits["calibration"]]
    confidence_validation = [item.confidence for item in splits["validation"]]
    confidence_threshold = choose_threshold(
        confidence_calibration,
        calibration_labels,
        target_precision,
        min_accepted=20,
    )
    report: dict[str, object] = {
        "schema_version": 1,
        "feature_names": FEATURE_NAMES,
        "target_precision": target_precision,
        "epochs": epochs,
        "splits": {
            name: {
                "candidates": len(items),
                "exact": int(sum(item.label for item in items)),
            }
            for name, items in splits.items()
        },
        "ranker": {
            "calibration": asdict(
                selection_metrics(calibration_scores, calibration_labels, ranker_threshold)
            ),
            "validation": asdict(
                selection_metrics(validation_scores, validation_labels, ranker_threshold)
            ),
        },
        "confidence_baseline": {
            "calibration": asdict(
                selection_metrics(
                    confidence_calibration,
                    calibration_labels,
                    confidence_threshold,
                )
            ),
            "validation": asdict(
                selection_metrics(
                    confidence_validation,
                    validation_labels,
                    confidence_threshold,
                )
            ),
        },
        "oracle_precision_frontier": {
            "note": "diagnostic only; thresholds use labels from the named split",
            "ranker_calibration": {
                str(count): asdict(
                    best_precision_metrics(calibration_scores, calibration_labels, count)
                )
                for count in (5, 10, 20, 50, 100)
            },
            "ranker_validation": {
                str(count): asdict(
                    best_precision_metrics(validation_scores, validation_labels, count)
                )
                for count in (5, 10, 20, 50, 100)
            },
            "confidence_calibration": {
                str(count): asdict(
                    best_precision_metrics(confidence_calibration, calibration_labels, count)
                )
                for count in (5, 10, 20, 50, 100)
            },
        },
        "model": asdict(model),
    }
    return model, report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train a research-only Czech candidate ranker")
    parser.add_argument("diagnostics", type=Path)
    parser.add_argument("gold", type=Path)
    parser.add_argument("pointers", type=Path)
    parser.add_argument("morphology", type=Path)
    parser.add_argument("--target-precision", type=float, default=0.9)
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--learning-rate", type=float, default=0.1)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    arguments = parser.parse_args(argv)
    target_precision = cast(float, arguments.target_precision)
    epochs = cast(int, arguments.epochs)
    learning_rate = cast(float, arguments.learning_rate)
    if not 0 < target_precision <= 1 or epochs <= 0 or learning_rate <= 0:
        raise ValueError("target_precision, epochs, and learning_rate must be positive")
    candidates = _load_candidates(
        cast(Path, arguments.diagnostics),
        cast(Path, arguments.gold),
        cast(Path, arguments.pointers),
        Morphology(cast(Path, arguments.morphology)),
    )
    model, report = train_and_evaluate(candidates, target_precision, epochs, learning_rate)
    artifact = cast(Path, arguments.artifact)
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "feature_names": FEATURE_NAMES,
                "ranker": asdict(model),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    report["artifact_sha256"] = hashlib.sha256(artifact.read_bytes()).hexdigest()
    output = cast(Path, arguments.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"candidates": len(candidates), **cast(dict[str, object], report["ranker"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
