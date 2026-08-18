"""Offline Czech grammar correction."""

from importlib.metadata import version
from typing import TYPE_CHECKING

from czechcore.core import CorrectionKind, CorrectionResult, TextEdit

if TYPE_CHECKING:
    from czechcore.engine import CzechCore

__version__ = version("czechcore")

__all__ = ["CorrectionKind", "CorrectionResult", "CzechCore", "TextEdit", "__version__"]


def __getattr__(name: str) -> object:
    if name == "CzechCore":
        from czechcore.engine import CzechCore

        return CzechCore
    raise AttributeError(name)
