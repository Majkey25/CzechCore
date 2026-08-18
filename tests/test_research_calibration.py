from __future__ import annotations

import json
from pathlib import Path

from tools.research.calibrate_confidence import calibrate


def test_calibration_filters_low_confidence_false_change(tmp_path: Path) -> None:
    diagnostics = tmp_path / "diagnostics.jsonl"
    gold = tmp_path / "gold.txt"
    records = [
        {
            "source": "Muži přišly.",
            "prediction": "Muži přišli.",
            "edit_confidences": [0.9],
        },
        {
            "source": "Kdy přijdeš?",
            "prediction": "Kdy přijedeš?",
            "edit_confidences": [0.4],
        },
    ]
    diagnostics.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )
    gold.write_text("Muži přišli.\nKdy přijdeš?\n", encoding="utf-8")

    low, high = calibrate(diagnostics, gold, (0.25, 0.5))

    assert low.false_changes == 1
    assert high.false_changes == 0
    assert high.corrected_errors == 1
