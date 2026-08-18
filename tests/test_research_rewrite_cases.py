from __future__ import annotations

from pathlib import Path

from tools.research.validate_rewrite_cases import validate_cases

ROOT = Path(__file__).parents[1]


def test_rewrite_benchmark_has_semantic_risk_coverage() -> None:
    summary = validate_cases(ROOT / "benchmarks" / "rewrite_cases.jsonl")

    assert summary["cases"] >= 12
    assert summary["risk_tags"] >= 10
