from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_top_level_import_defers_ml_runtime() -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "tests" / "verify_lazy_import.py")],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
