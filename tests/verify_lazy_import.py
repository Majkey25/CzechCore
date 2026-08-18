from __future__ import annotations

import importlib
import sys

package = importlib.import_module("czechcore")

if "torch" in sys.modules:
    raise RuntimeError("top-level czechcore import loaded torch")

CzechCore = package.CzechCore

if (
    not isinstance(CzechCore, type)
    or "torch" not in sys.modules
    or CzechCore.__name__ != "CzechCore"
):
    raise RuntimeError("lazy CzechCore export did not load the engine")
