from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Sequence
from html import unescape
from pathlib import Path
from typing import TypedDict
from urllib.parse import quote, unquote

SECTION = re.compile(r"baleni\(\"div(\d+)\"\).*?<b>.*?</span>(.*?)</b>")
RULE = re.compile(r"\?id=([^']+)'>zobrazit</a>&emsp;</span>(.*?)<br />")
TAG = re.compile(r"<[^>]+>")


class Rule(TypedDict):
    id: str
    title: str
    url: str


class Section(TypedDict):
    id: str
    title: str
    rules: list[Rule]


class Outline(TypedDict):
    schema_version: int
    source_id: str
    source_sha256: str
    section_count: int
    rule_count: int
    sections: list[Section]


def clean(raw: str) -> str:
    return " ".join(unescape(TAG.sub("", raw)).split())


def build_outline(index_path: Path) -> Outline:
    content = index_path.read_text(encoding="utf-8")
    sections: list[Section] = []
    current: Section | None = None
    for line in content.splitlines():
        section_match = SECTION.search(line)
        if section_match and "Zobrazit všechny" not in line:
            current = {
                "id": f"ijc-{section_match.group(1)}",
                "title": clean(section_match.group(2)),
                "rules": [],
            }
            sections.append(current)
            continue
        rule_match = RULE.search(line)
        if rule_match and current is not None:
            identifier = unquote(rule_match.group(1))
            rules = current["rules"]
            rules.append(
                {
                    "id": identifier,
                    "title": clean(rule_match.group(2)),
                    "url": f"https://prirucka.ujc.cas.cz/?id={quote(identifier, safe='')}",
                }
            )
    rule_count = sum(len(section["rules"]) for section in sections)
    if len(sections) != 22 or rule_count != 202:
        raise RuntimeError(f"unexpected IJP outline: {len(sections)} sections, {rule_count} rules")
    return {
        "schema_version": 1,
        "source_id": "collection-ijc-general-rules",
        "source_sha256": hashlib.sha256(index_path.read_bytes()).hexdigest(),
        "section_count": len(sections),
        "rule_count": rule_count,
        "sections": sections,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="build-ijc-outline")
    parser.add_argument("index", type=Path)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args(argv)
    index_path = arguments.index
    output_path = arguments.output
    assert isinstance(index_path, Path) and isinstance(output_path, Path)
    outline = build_outline(index_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(outline, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"ijc_sections={outline['section_count']}")
    print(f"ijc_rules={outline['rule_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
