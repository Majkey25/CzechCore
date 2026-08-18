from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_release_version_is_consistent_across_repository_metadata() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    version = project["version"]

    assert f"version: {version}" in (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    assert f"## [{version}]" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"`v{version}`" in (ROOT / "README.md").read_text(encoding="utf-8")


def test_documentation_index_targets_exist() -> None:
    documents = (
        "ARCHITECTURE.md",
        "API.md",
        "DEVELOPMENT.md",
        "EVALUATION.md",
        "ROADMAP.md",
        "SCIENTIFIC_BASIS.md",
        "decisions/README.md",
    )

    assert all((ROOT / "docs" / document).is_file() for document in documents)
