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
    expected_hash = "c96f86e2471992b75872c66de5ddbb526f7cc5dcb4cd428f7813c5bab1ff902d"
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
    assert "No signed APK is available" in android
    assert "Termux is not supported" in android


def test_platform_smoke_uses_real_model_on_all_desktop_runners() -> None:
    workflow = (ROOT / ".github" / "workflows" / "platform-smoke.yml").read_text(encoding="utf-8")

    for runner in ("windows-latest", "macos-latest", "ubuntu-latest"):
        assert runner in workflow
    assert "python -m venv" in workflow
    assert "czechcore download" in workflow
    assert "-m model" in workflow
    assert "shell: ${{ matrix.shell }}" not in workflow


def test_android_ime_keeps_model_and_network_out_of_source_apk() -> None:
    android = ROOT / "android" / "app" / "src" / "main"
    required = (
        android / "AndroidManifest.xml",
        android / "cpp" / "CMakeLists.txt",
        android / "cpp" / "native_bridge.cpp",
        android / "java" / "cz" / "czechcore" / "app" / "CzechCoreImeService.java",
        android / "java" / "cz" / "czechcore" / "app" / "MainActivity.java",
        android / "java" / "cz" / "czechcore" / "app" / "WordPieceTokenizer.java",
        android / "res" / "xml" / "input_method.xml",
        ROOT / "android" / "README.md",
    )
    assert all(path.is_file() for path in required)

    manifest = required[0].read_text(encoding="utf-8")
    assert "android.permission.INTERNET" not in manifest
    assert "android.permission.BIND_ACCESSIBILITY_SERVICE" not in manifest
    assert "android.permission.BIND_INPUT_METHOD" in manifest
    assert "android.view.InputMethod" in manifest

    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "android/local-libs/" in ignored
    assert "android/app/build/" in ignored

    build = (ROOT / "android" / "app" / "build.gradle").read_text(encoding="utf-8")
    assert 'abiFilters "x86_64", "arm64-v8a"' in build
    engine = (
        android / "java" / "cz" / "czechcore" / "app" / "LocalCorrectionEngine.java"
    ).read_text(encoding="utf-8")
    assert "new ArrayBlockingQueue<>(1)" in engine
    assert "MAX_MODEL_BYTES = 512 * 1024 * 1024" in engine

    wrapper = (ROOT / "android" / "gradle" / "wrapper" / "gradle-wrapper.properties").read_text(
        encoding="utf-8"
    )
    assert "gradle-9.8.1-bin.zip" in wrapper
    assert (
        "distributionSha256Sum=dce76f55f8e251a3a1f130eb120f30b3d271de2b76c9b0729d316b5a1b6dc01f"
    ) in wrapper


def test_windows_live_typing_uses_tsf_and_one_local_broker() -> None:
    windows = ROOT / "windows"
    required = (
        windows / "CMakeLists.txt",
        windows / "README.md",
        windows / "client" / "engine_client.cpp",
        windows / "client" / "broker_identity.cpp",
        windows / "client" / "broker_identity.h",
        windows / "client" / "pipe_io.cpp",
        windows / "client" / "pipe_io.h",
        windows / "engine" / "main.cpp",
        windows / "settings" / "main.cpp",
        windows / "setup" / "main.cpp",
        windows / "tsf" / "module.cpp",
        windows / "tsf" / "text_service.cpp",
        windows / "tsf" / "display_attribute.cpp",
        windows / "tests" / "text_test.cpp",
        windows / "tests" / "client_security_test.cpp",
        windows / "tests" / "tsf_host_test.cpp",
    )
    assert all(path.is_file() for path in required)

    source = "\n".join(path.read_text(encoding="utf-8") for path in required)
    assert "ITfTextInputProcessor" in source
    assert "GUID_PROP_ATTRIBUTE" in source
    assert "CreateNamedPipeW" in source
    assert "PIPE_REJECT_REMOTE_CLIENTS" in source
    assert "GetNamedPipeServerProcessId" in source
    assert "kMaxPipeMessageBytes = 16 * 1024" in source
    assert "CancelIoEx" in source
    assert "SetWindowsHookEx" not in source
