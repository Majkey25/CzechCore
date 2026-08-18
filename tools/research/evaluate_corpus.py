from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast


@dataclass(slots=True)
class SentenceMetrics:
    total: int = 0
    exact: int = 0
    source_correct: int = 0
    false_changes: int = 0
    corrected_errors: int = 0
    unchanged_errors: int = 0
    wrong_rewrites: int = 0

    def add(self, source: str, references: tuple[str, ...], prediction: str) -> None:
        self.total += 1
        exact = prediction in references
        source_correct = source in references
        self.exact += exact
        self.source_correct += source_correct
        if source_correct:
            self.false_changes += prediction != source
        elif exact:
            self.corrected_errors += 1
        elif prediction == source:
            self.unchanged_errors += 1
        else:
            self.wrong_rewrites += 1


def _lines(path: Path, *, allow_empty: bool = False) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or (not allow_empty and any(not line for line in lines)):
        raise ValueError(f"expected non-empty lines: {path}")
    return lines


def _domains(meta_path: Path, pointers_path: Path) -> list[str]:
    with meta_path.open(encoding="utf-8", newline="") as source:
        records = csv.DictReader(source, delimiter="\t")
        domains = {
            record["Filename"]: record["Domain"]
            for record in records
            if record.get("Filename") and record.get("Domain")
        }
    pointers = _lines(pointers_path)
    try:
        return [domains[pointer] for pointer in pointers]
    except KeyError as error:
        raise ValueError(f"missing GECCC metadata for {error.args[0]}") from error


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def evaluate(
    source_path: Path,
    gold_path: Path,
    predictions_path: Path,
    meta_path: Path,
    pointers_path: Path,
) -> dict[str, object]:
    sources = _lines(source_path)
    gold = _lines(gold_path, allow_empty=True)
    predictions = _lines(predictions_path)
    domains = _domains(meta_path, pointers_path)
    lengths = {len(sources), len(gold), len(predictions), len(domains)}
    if len(lengths) != 1:
        raise ValueError(
            "source, gold, predictions, and metadata must contain the same number of lines"
        )

    overall = SentenceMetrics()
    by_domain: dict[str, SentenceMetrics] = {}
    for source, raw_references, prediction, domain in zip(
        sources,
        gold,
        predictions,
        domains,
        strict=True,
    ):
        references = tuple(dict.fromkeys(raw_references.split("\t")))
        overall.add(source, references, prediction)
        by_domain.setdefault(domain, SentenceMetrics()).add(source, references, prediction)

    return {
        "schema_version": 1,
        "inputs": {
            "source_sha256": _sha256(source_path),
            "gold_sha256": _sha256(gold_path),
            "predictions_sha256": _sha256(predictions_path),
            "meta_sha256": _sha256(meta_path),
            "pointers_sha256": _sha256(pointers_path),
        },
        "overall": asdict(overall),
        "domains": {name: asdict(metrics) for name, metrics in sorted(by_domain.items())},
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate aligned GECCC predictions")
    parser.add_argument("source", type=Path)
    parser.add_argument("gold", type=Path)
    parser.add_argument("predictions", type=Path)
    parser.add_argument("meta", type=Path)
    parser.add_argument("pointers", type=Path)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args(argv)
    report = evaluate(
        cast(Path, arguments.source),
        cast(Path, arguments.gold),
        cast(Path, arguments.predictions),
        cast(Path, arguments.meta),
        cast(Path, arguments.pointers),
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    output = cast(Path | None, arguments.output)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(json.dumps(report["overall"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
