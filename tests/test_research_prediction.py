from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from czechcore.core import CorrectionResult
from tools.research.predict_corpus import predict_file


class UppercaseEngine:
    def correct(
        self,
        text: str,
        *,
        autocorrect: bool = False,
        min_confidence: float = 0.995,
    ) -> CorrectionResult:
        return CorrectionResult(text, text.upper(), text, ())


def test_prediction_file_preserves_line_alignment(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    output = tmp_path / "predictions.txt"
    source_copy = tmp_path / "evaluated-source.txt"
    diagnostics = tmp_path / "diagnostics.jsonl"
    source.write_text("První věta.\nDruhá věta.\nTřetí věta.\n", encoding="utf-8")

    summary = predict_file(
        source,
        output,
        UppercaseEngine(),
        limit=2,
        source_copy=source_copy,
        diagnostics_path=diagnostics,
    )

    assert output.read_text(encoding="utf-8").splitlines() == ["PRVNÍ VĚTA.", "DRUHÁ VĚTA."]
    assert source_copy.read_text(encoding="utf-8").splitlines() == ["První věta.", "Druhá věta."]
    first_record = json.loads(diagnostics.read_text(encoding="utf-8").splitlines()[0])
    assert cast(dict[str, object], first_record)["line"] == 1
    assert summary.sentences == summary.changed == 2
