from __future__ import annotations

import json

import pytest

from czechcore.cli import main
from czechcore.core import CorrectionKind, CorrectionResult, TextEdit
from czechcore.rewrite import RewriteBackend


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


class StaticRewriteBackend:
    def rewrite(self, source: str, proofread: str) -> str:
        return "Jako jo, je to širší nástroj než pip."


class IdentityEngine:
    def correct(
        self,
        text: str,
        *,
        autocorrect: bool = False,
        min_confidence: float = 0.995,
    ) -> CorrectionResult:
        return CorrectionResult(text, text, text, ())


def rewrite_backend_factory(endpoint: str, model: str) -> RewriteBackend:
    assert endpoint.startswith("http://127.0.0.1:")
    assert model == "local"
    return StaticRewriteBackend()


def test_check_prints_suggestion_by_default(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["check", "ahoj."], engine_factory=StaticEngine)

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "Ahoj."


def test_rewrite_prints_explicit_local_suggestion(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(
        ["rewrite", "jako", "jo", "pip", "--protect", "pip"],
        engine_factory=IdentityEngine,
        rewrite_backend_factory=rewrite_backend_factory,
    )

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "Jako jo, je to širší nástroj než pip."


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
