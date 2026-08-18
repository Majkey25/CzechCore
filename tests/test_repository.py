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
        "PLATFORM_INTEGRATION.md",
        "RESEARCH_REPORT.md",
        "ROADMAP.md",
        "SCIENTIFIC_BASIS.md",
        "decisions/README.md",
    )

    assert all((ROOT / "docs" / document).is_file() for document in documents)


def test_device_setup_guides_are_versioned_and_linked() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    version = project["version"]
    expected_hash = "8d1aab92dce9d854e15f18107f3f987edf7d49806efa24759994717396412621"
    guide_paths = (
        ROOT / "docs" / "GETTING_STARTED.md",
        ROOT / "docs" / "setup" / "WINDOWS.md",
        ROOT / "docs" / "setup" / "MACOS.md",
        ROOT / "docs" / "setup" / "LINUX.md",
        ROOT / "docs" / "setup" / "ANDROID.md",
    )

    assert all(path.is_file() for path in guide_paths)
    for path in guide_paths[:-1]:
        text = path.read_text(encoding="utf-8")
        assert f"v{version}" in text
        assert expected_hash in text
    for path in guide_paths[1:-1]:
        text = path.read_text(encoding="utf-8")
        assert "czechcore download" in text
        assert "Když přišel domů šel spát." in text
        assert "Když přišel domů, šel spát." in text

    chooser = guide_paths[0].read_text(encoding="utf-8")
    for filename in ("WINDOWS.md", "MACOS.md", "LINUX.md", "ANDROID.md"):
        assert f"setup/{filename}" in chooser

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    docs_index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    assert "docs/GETTING_STARTED.md" in readme
    assert "GETTING_STARTED.md" in docs_index

    android = guide_paths[-1].read_text(encoding="utf-8")
    assert "No APK is available" in android
    assert "Termux is not supported" in android


def test_platform_smoke_uses_real_model_on_all_desktop_runners() -> None:
    workflow = (ROOT / ".github" / "workflows" / "platform-smoke.yml").read_text(encoding="utf-8")

    for runner in ("windows-latest", "macos-latest", "ubuntu-latest"):
        assert runner in workflow
    assert "python -m venv" in workflow
    assert "czechcore download" in workflow
    assert "-m model" in workflow
    assert "shell: ${{ matrix.shell }}" not in workflow
