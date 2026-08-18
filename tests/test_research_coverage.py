from __future__ import annotations

from pathlib import Path

from tools.research.build_coverage import build_coverage, load_object

ROOT = Path(__file__).parents[1]


def test_coverage_accounts_for_every_phenomenon_and_benchmark_case() -> None:
    coverage = build_coverage(
        load_object(ROOT / "research" / "taxonomy.json"),
        load_object(ROOT / "research" / "benchmark-mapping.json"),
        (ROOT / "benchmarks" / "cases.jsonl").read_text(encoding="utf-8").splitlines(),
    )

    summary = coverage["summary"]
    assert isinstance(summary, dict)
    assert summary["phenomena"] == 101
    assert summary["benchmark_cases"] == 65
