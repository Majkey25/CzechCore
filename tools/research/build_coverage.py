from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

EVIDENCE = ("positive", "negative", "ambiguity")


def load_object(path: Path) -> dict[str, object]:
    loaded: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"expected JSON object: {path}")
    return cast(dict[str, object], loaded)


def _objects(value: object, owner: str) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise ValueError(f"{owner} must be a list of objects")
    objects: list[dict[str, object]] = []
    for item in cast(list[object], value):
        if not isinstance(item, dict):
            raise ValueError(f"{owner} must be a list of objects")
        objects.append(cast(dict[str, object], item))
    return objects


def _strings(value: object, owner: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{owner} must be a string list")
    strings: list[str] = []
    for item in cast(list[object], value):
        if not isinstance(item, str):
            raise ValueError(f"{owner} must be a string list")
        strings.append(item)
    return strings


def _text(item: Mapping[str, object], field: str, owner: str) -> str:
    value = item.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{owner}.{field} must be a non-empty string")
    return value


def build_coverage(
    taxonomy: Mapping[str, object],
    mapping: Mapping[str, object],
    benchmark_lines: Sequence[str],
) -> dict[str, object]:
    families = _objects(taxonomy.get("families"), "taxonomy.families")
    category_root = mapping.get("categories")
    if not isinstance(category_root, dict):
        raise ValueError("mapping.categories must be an object")
    categories = cast(dict[str, object], category_root)

    case_categories: dict[str, list[int]] = {}
    for index, line in enumerate(benchmark_lines, start=1):
        loaded: object = json.loads(line)
        if not isinstance(loaded, dict):
            raise ValueError(f"benchmark line {index} must be an object")
        category = _text(cast(dict[str, object], loaded), "category", f"benchmark[{index}]")
        case_categories.setdefault(category, []).append(index)
    if set(categories) != set(case_categories):
        raise ValueError("benchmark mapping categories must match benchmark categories exactly")

    evidence_by_phenomenon: dict[str, dict[str, list[dict[str, object]]]] = {}
    global_cases: list[dict[str, object]] = []
    for category, raw_mapping in categories.items():
        if not isinstance(raw_mapping, dict):
            raise ValueError(f"mapping category must be an object: {category}")
        entry = cast(dict[str, object], raw_mapping)
        evidence = _text(entry, "evidence", category)
        if evidence not in EVIDENCE:
            raise ValueError(f"invalid evidence type: {category}")
        phenomenon_ids = _strings(entry.get("phenomenon_ids"), category)
        case_refs: list[dict[str, object]] = [
            {"line": line, "category": category} for line in case_categories[category]
        ]
        if not phenomenon_ids:
            global_cases.extend({**case, "evidence": evidence} for case in case_refs)
        for phenomenon_id in phenomenon_ids:
            evidence_by_phenomenon.setdefault(
                phenomenon_id,
                {kind: [] for kind in EVIDENCE},
            )[evidence].extend(case_refs)

    coverage: list[dict[str, object]] = []
    known_ids: set[str] = set()
    for family in families:
        family_id = _text(family, "id", "family")
        geccc_types = _strings(family.get("geccc_types"), family_id)
        required = _strings(family.get("required_evidence"), family_id)
        for phenomenon in _objects(family.get("phenomena"), f"{family_id}.phenomena"):
            phenomenon_id = _text(phenomenon, "id", family_id)
            known_ids.add(phenomenon_id)
            evidence = evidence_by_phenomenon.get(
                phenomenon_id,
                {kind: [] for kind in EVIDENCE},
            )
            missing = [kind for kind in required if not evidence[kind]]
            status = _text(phenomenon, "baseline_status", phenomenon_id)
            coverage.append(
                {
                    "id": phenomenon_id,
                    "name": _text(phenomenon, "name", phenomenon_id),
                    "family_id": family_id,
                    "scope": _text(family, "scope", family_id),
                    "baseline_status": status,
                    "source_rule_ids": _strings(phenomenon.get("source_rule_ids"), phenomenon_id),
                    "geccc_proxy_types": geccc_types,
                    "benchmark_evidence": evidence,
                    "missing_evidence": missing,
                    "coverage_state": (
                        "out_of_scope"
                        if status == "out_of_scope"
                        else "complete"
                        if not missing
                        else "partial"
                        if any(evidence.values())
                        else "gap"
                    ),
                }
            )
    unknown = set(evidence_by_phenomenon) - known_ids
    if unknown:
        raise ValueError(f"unknown phenomenon ids in benchmark mapping: {sorted(unknown)}")

    return {
        "schema_version": 1,
        "taxonomy_schema_version": taxonomy.get("schema_version"),
        "phenomena": coverage,
        "global_cases": global_cases,
        "summary": {
            "phenomena": len(coverage),
            "complete": sum(item["coverage_state"] == "complete" for item in coverage),
            "partial": sum(item["coverage_state"] == "partial" for item in coverage),
            "gaps": sum(item["coverage_state"] == "gap" for item in coverage),
            "out_of_scope": sum(item["coverage_state"] == "out_of_scope" for item in coverage),
            "benchmark_cases": sum(len(lines) for lines in case_categories.values()),
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build or verify taxonomy coverage metadata")
    parser.add_argument("--taxonomy", type=Path, default=Path("research/taxonomy.json"))
    parser.add_argument("--mapping", type=Path, default=Path("research/benchmark-mapping.json"))
    parser.add_argument("--benchmark", type=Path, default=Path("benchmarks/cases.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("research/coverage.json"))
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args(argv)
    output = cast(Path, arguments.output)
    coverage = build_coverage(
        load_object(cast(Path, arguments.taxonomy)),
        load_object(cast(Path, arguments.mapping)),
        cast(Path, arguments.benchmark).read_text(encoding="utf-8").splitlines(),
    )
    rendered = json.dumps(coverage, ensure_ascii=False, indent=2) + "\n"
    if arguments.check:
        if not output.is_file() or output.read_text(encoding="utf-8") != rendered:
            raise ValueError("coverage metadata is stale; run tools.research.build_coverage")
    else:
        output.write_text(rendered, encoding="utf-8")
    print(json.dumps(coverage["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
