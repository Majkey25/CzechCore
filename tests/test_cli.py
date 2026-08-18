from __future__ import annotations

import json

import pytest

from czechcore.cli import main
from czechcore.core import CorrectionKind, CorrectionResult, TextEdit


class StaticEngine:
    def correct(
        self,
        text: str,
        *,
        autocorrect: bool = False,
        min_confidence: float = 0.995,
    ) -> CorrectionResult:
        edit = TextEdit(0, 1, "a", "A", CorrectionKind.CAPITALIZATION, 0.99, autocorrect)
        return CorrectionResult(text, "Ahoj.", "Ahoj." if autocorrect else text, (edit,))


def test_check_prints_suggestion_by_default(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["check", "ahoj."], engine_factory=StaticEngine)

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "Ahoj."


def test_check_json_serializes_structured_result_once(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["check", "--json", "ahoj."], engine_factory=StaticEngine)

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["suggested_text"] == "Ahoj."
    assert payload["edits"][0]["kind"] == "capitalization"
    assert isinstance(payload["edits"], list)


def test_cli_reports_installed_package_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])

    assert exit_info.value.code == 0
    assert capsys.readouterr().out.strip() == "czechcore 0.1.0"
