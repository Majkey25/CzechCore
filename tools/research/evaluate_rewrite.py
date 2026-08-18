from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, cast

if TYPE_CHECKING:
    from czechcore.rewrite import RewriteResult


class Rewriter(Protocol):
    def suggest(self, text: str, *, protected: Sequence[str] = ()) -> RewriteResult: ...


@dataclass(frozen=True, slots=True)
class RewriteEvaluation:
    total: int
    exact: int
    invariant_fallbacks: int


def evaluate_cases(
    path: Path, rewriter: Rewriter
) -> tuple[RewriteEvaluation, list[dict[str, object]]]:
    results: list[dict[str, object]] = []
    exact = invariant_fallbacks = 0
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise ValueError("rewrite benchmark is empty")
    for line_number, line in enumerate(lines, start=1):
        loaded: object = json.loads(line)
        if not isinstance(loaded, dict):
            raise ValueError(f"line {line_number}: case must be an object")
        case = cast(dict[str, object], loaded)
        source, references, protected = (
            case.get("source"),
            case.get("references"),
            case.get("protected_literals"),
        )
        if (
            not isinstance(source, str)
            or not isinstance(references, list)
            or not all(isinstance(item, str) for item in cast(list[object], references))
            or not isinstance(protected, list)
            or not all(isinstance(item, str) for item in cast(list[object], protected))
        ):
            raise ValueError(f"line {line_number}: invalid rewrite case")
        result = rewriter.suggest(source, protected=cast(list[str], protected))
        is_exact = result.suggested_text in cast(list[str], references)
        fallback = any("changed_" in warning for warning in result.warnings)
        exact += is_exact
        invariant_fallbacks += fallback
        results.append(
            {
                "line": line_number,
                "category": case.get("category"),
                "source": source,
                "references": references,
                "prediction": result.suggested_text,
                "exact": is_exact,
                "warnings": result.warnings,
            }
        )
    return RewriteEvaluation(len(lines), exact, invariant_fallbacks), results


def main(argv: Sequence[str] | None = None) -> int:
    from czechcore.backend import TransformerBackend
    from czechcore.engine import CzechCore
    from czechcore.rewrite import HybridRewriter, LocalChatRewriteBackend
    from czechcore.tokenizer import CzechTokenizer

    parser = argparse.ArgumentParser(description="Evaluate a local hybrid rewrite endpoint")
    parser.add_argument("--cases", type=Path, default=Path("benchmarks/rewrite_cases.jsonl"))
    parser.add_argument("--endpoint", default="http://127.0.0.1:8080/v1/chat/completions")
    parser.add_argument("--model", default="local")
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args(argv)
    tokenizer = CzechTokenizer()
    correction_backend = TransformerBackend()
    evaluation, results = evaluate_cases(
        cast(Path, arguments.cases),
        HybridRewriter(
            CzechCore(tokenizer=tokenizer, backend=correction_backend),
            LocalChatRewriteBackend(
                cast(str, arguments.endpoint),
                model=cast(str, arguments.model),
            ),
            context_proofreader=CzechCore(
                tokenizer=tokenizer,
                backend=correction_backend,
                suggestion_min_confidence=0,
                max_changed_ratio=1,
            ),
        ),
    )
    report = {"summary": asdict(evaluation), "results": results}
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    output = cast(Path | None, arguments.output)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(json.dumps(asdict(evaluation), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
