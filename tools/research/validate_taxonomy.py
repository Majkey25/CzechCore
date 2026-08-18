from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

SCOPES = {"correction", "reference"}
STATUSES = {"guarded", "out_of_scope", "partial", "supported", "unmeasured"}
EVIDENCE = {"ambiguity", "negative", "positive"}


def load_json(path: Path) -> dict[str, object]:
    loaded: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"expected JSON object: {path}")
    return cast(dict[str, object], loaded)


def _string(item: Mapping[str, object], field: str, owner: str) -> str:
    value = item.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{owner}: {field} must be a non-empty string")
    return value


def _string_list(item: Mapping[str, object], field: str, owner: str) -> list[str]:
    value = item.get(field)
    if not isinstance(value, list) or not all(
        isinstance(entry, str) for entry in cast(list[object], value)
    ):
        raise ValueError(f"{owner}: {field} must be a string list")
    return cast(list[str], value)


def validate_taxonomy(
    taxonomy: Mapping[str, object],
    ijc_outline: Mapping[str, object],
    geccc: Mapping[str, object],
) -> dict[str, int]:
    if taxonomy.get("schema_version") != 1:
        raise ValueError("taxonomy schema_version must be 1")
    raw_sections = ijc_outline.get("sections")
    if not isinstance(raw_sections, list):
        raise ValueError("IJP outline sections must be a list")
    section_ids: set[str] = set()
    rule_ids: set[str] = set()
    for raw_section in cast(list[object], raw_sections):
        if not isinstance(raw_section, dict):
            raise ValueError("IJP section must be an object")
        section = cast(dict[str, object], raw_section)
        section_id = _string(section, "id", "IJP section")
        section_ids.add(section_id)
        raw_rules = section.get("rules")
        if not isinstance(raw_rules, list):
            raise ValueError(f"{section_id}: rules must be a list")
        for raw_rule in cast(list[object], raw_rules):
            if not isinstance(raw_rule, dict):
                raise ValueError(f"{section_id}: rule must be an object")
            rule_ids.add(_string(cast(dict[str, object], raw_rule), "id", section_id))

    raw_error_types = geccc.get("error_types")
    if not isinstance(raw_error_types, dict):
        raise ValueError("GECCC error_types must be an object")
    geccc_types = set(cast(dict[str, object], raw_error_types))

    raw_families = taxonomy.get("families")
    if not isinstance(raw_families, list):
        raise ValueError("taxonomy families must be a list")
    family_ids: set[str] = set()
    phenomenon_ids: set[str] = set()
    assigned_sections: list[str] = []
    assigned_types: list[str] = []
    for raw_family in cast(list[object], raw_families):
        if not isinstance(raw_family, dict):
            raise ValueError("taxonomy family must be an object")
        family = cast(dict[str, object], raw_family)
        family_id = _string(family, "id", "taxonomy family")
        if family_id in family_ids:
            raise ValueError(f"duplicate family id: {family_id}")
        family_ids.add(family_id)
        scope = _string(family, "scope", family_id)
        status = _string(family, "baseline_status", family_id)
        if scope not in SCOPES or status not in STATUSES:
            raise ValueError(f"{family_id}: invalid scope or status")
        evidence = set(_string_list(family, "required_evidence", family_id))
        if scope == "correction" and evidence != EVIDENCE:
            raise ValueError(
                f"{family_id}: correction evidence must be positive/negative/ambiguity"
            )
        sections = _string_list(family, "ijc_sections", family_id)
        error_types = _string_list(family, "geccc_types", family_id)
        if not set(sections) <= section_ids:
            raise ValueError(f"{family_id}: unknown IJP section")
        if not set(error_types) <= geccc_types:
            raise ValueError(f"{family_id}: unknown GECCC type")
        assigned_sections.extend(sections)
        assigned_types.extend(error_types)

        raw_phenomena = family.get("phenomena")
        if not isinstance(raw_phenomena, list) or not raw_phenomena:
            raise ValueError(f"{family_id}: phenomena must be a non-empty list")
        for raw_phenomenon in cast(list[object], raw_phenomena):
            if not isinstance(raw_phenomenon, dict):
                raise ValueError(f"{family_id}: phenomenon must be an object")
            phenomenon = cast(dict[str, object], raw_phenomenon)
            phenomenon_id = _string(phenomenon, "id", family_id)
            if not phenomenon_id.startswith(f"{family_id}.") or phenomenon_id in phenomenon_ids:
                raise ValueError(f"invalid or duplicate phenomenon id: {phenomenon_id}")
            phenomenon_ids.add(phenomenon_id)
            _string(phenomenon, "name", phenomenon_id)
            phenomenon_status = _string(phenomenon, "baseline_status", phenomenon_id)
            if phenomenon_status not in STATUSES:
                raise ValueError(f"{phenomenon_id}: invalid status")
            source_rules = _string_list(phenomenon, "source_rule_ids", phenomenon_id)
            if not source_rules or not set(source_rules) <= rule_ids:
                raise ValueError(f"{phenomenon_id}: missing or unknown source rule")

    if (
        len(assigned_sections) != len(set(assigned_sections))
        or set(assigned_sections) != section_ids
    ):
        raise ValueError("every IJP section must be assigned exactly once")
    if len(assigned_types) != len(set(assigned_types)) or set(assigned_types) != geccc_types:
        raise ValueError("every GECCC error type must be assigned exactly once")
    return {
        "families": len(family_ids),
        "phenomena": len(phenomenon_ids),
        "ijc_sections": len(section_ids),
        "ijc_rules": len(rule_ids),
        "geccc_error_types": len(geccc_types),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="validate-research-taxonomy")
    parser.add_argument("--taxonomy", type=Path, default=Path("research/taxonomy.json"))
    parser.add_argument("--ijc", type=Path, default=Path("research/ijc-outline.json"))
    parser.add_argument("--geccc", type=Path, default=Path("research/geccc-error-types.json"))
    arguments = parser.parse_args(argv)
    summary = validate_taxonomy(
        taxonomy=load_json(cast(Path, arguments.taxonomy)),
        ijc_outline=load_json(cast(Path, arguments.ijc)),
        geccc=load_json(cast(Path, arguments.geccc)),
    )
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
