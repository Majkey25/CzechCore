from __future__ import annotations

import json
from pathlib import Path
from typing import cast

ROOT = Path(__file__).parents[1]


def test_portable_runtime_screen_preserves_evidence_and_open_gates() -> None:
    record = cast(
        dict[str, object],
        json.loads(
            (
                ROOT / "research" / "evaluations" / "portable-runtime-screen-2026-08-18.json"
            ).read_text(encoding="utf-8")
        ),
    )
    acceptance = cast(dict[str, object], record["acceptance_probe"])
    float32 = cast(dict[str, object], record["float32"])
    int8 = cast(dict[str, object], record["int8"])
    android = cast(dict[str, object], record["android_arm64_build"])
    emulator = cast(dict[str, object], record["android_x86_64_emulator_probe"])
    apk = cast(dict[str, object], record["android_debug_apk_probe"])
    remaining = cast(list[str], record["remaining_gates"])

    assert float32["top_output_matches"] == acceptance["sentence_spans"] == 66
    assert int8["top_output_matches"] == 65
    assert cast(str, int8["decision"]).startswith("rejected")
    assert android["build_result"] == "success"
    assert android["abi"] == "arm64-v8a"
    assert android["shared_library_stripped_bytes"] == 3_911_616
    assert emulator["result"] == "local native inference success"
    assert emulator["desktop_model_server_used"] is False
    assert emulator["output_tokens"] == ["Když", "přišel", "domů", ",", "šel", "spát", "."]
    assert apk["result"] == "source debug APK local correction probe passed"
    assert apk["crash_buffer_after_final_runs"] == "empty"
    assert apk["raw_user_text_in_app_logcat"] is False
    assert "release-signed APK emulator acceptance matrix" in remaining
