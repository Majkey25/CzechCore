"""Offline Czech grammar correction."""

from importlib.metadata import version
from typing import TYPE_CHECKING

from czechcore.core import CorrectionKind, CorrectionResult, TextEdit

if TYPE_CHECKING:
    from czechcore.engine import CzechCore
    from czechcore.rewrite import HybridRewriter, LocalChatRewriteBackend, RewriteResult

__version__ = version("czechcore")

__all__ = [
    "CorrectionKind",
    "CorrectionResult",
    "CzechCore",
    "HybridRewriter",
    "LocalChatRewriteBackend",
    "RewriteResult",
    "TextEdit",
    "__version__",
]


def __getattr__(name: str) -> object:
    if name == "CzechCore":
        from czechcore.engine import CzechCore

        return CzechCore
    if name in {"HybridRewriter", "LocalChatRewriteBackend", "RewriteResult"}:
        from czechcore import rewrite

        return getattr(rewrite, name)
    raise AttributeError(name)
