from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from czechcore.rewrite import RewriteResult
from tools.research.evaluate_rewrite import evaluate_cases


@dataclass(frozen=True)
class StaticRewriter:
    candidate: str

    def suggest(self, text: str, *, protected: Sequence[str] = ()) -> RewriteResult:
        return RewriteResult(text, text, self.candidate, ())


def test_rewrite_evaluation_counts_exact_reference(tmp_path: Path) -> None:
    cases = tmp_path / "cases.jsonl"
    cases.write_text(
        '{"source":"spatne","references":["Správně."],"protected_literals":[],"category":"test"}\n',
        encoding="utf-8",
    )

    summary, results = evaluate_cases(cases, StaticRewriter("Správně."))

    assert summary.exact == summary.total == 1
    assert results[0]["exact"] is True
