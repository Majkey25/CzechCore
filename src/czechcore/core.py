from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher
from enum import StrEnum
from math import isfinite
from unicodedata import category, normalize

_PROTECTED_PATTERNS = tuple(
    re.compile(pattern)
    for pattern in (
        r"https?://[^\s<>()\[\]{}]+",
        r"(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+(?![\w-])",
        r"(?<!\w)[A-Za-z]:\\[^\r\n\t<>\"|?*]+",
        r"(?<!\w)v?\d+(?:\.\d+){2,}(?!\w)",
        r"(?<!\w)(?:[A-Za-z][A-Za-z0-9_]*(?:\+\+|#)[A-Za-z0-9_]*|"
        r"[A-Za-z0-9_]*[a-z][A-Za-z0-9_]*[A-Z][A-Za-z0-9_]*)(?!\w)",
    )
)
_TRAILING_SENTENCE_PUNCTUATION = ".,;:!?"
_ADJACENT_REPEATED_WORD = re.compile(r"(?iu)(?<!\w)([^\W\d_]+)(\s+)\1(?!\w)")


class CorrectionKind(StrEnum):
    SPELLING = "spelling"
    DIACRITICS = "diacritics"
    PUNCTUATION = "punctuation"
    CAPITALIZATION = "capitalization"
    WHITESPACE = "whitespace"
    GRAMMAR = "grammar"


@dataclass(frozen=True, slots=True)
class TextEdit:
    start: int
    end: int
    source: str
    replacement: str
    kind: CorrectionKind
    confidence: float
    applied: bool

    def __post_init__(self) -> None:
        if self.start < 0 or self.end < self.start:
            raise ValueError("invalid edit range")
        if len(self.source) != self.end - self.start:
            raise ValueError("source length does not match edit range")
        if self.source == self.replacement:
            raise ValueError("edit must change text")
        if not isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class CorrectionResult:
    original_text: str
    suggested_text: str
    output_text: str
    edits: tuple[TextEdit, ...]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Hypothesis:
    text: str
    score: float
    confidence: float

    def __post_init__(self) -> None:
        if not self.text:
            raise ValueError("hypothesis text cannot be empty")
        if not isfinite(self.score):
            raise ValueError("hypothesis score must be finite")
        if not isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("hypothesis confidence must be between 0 and 1")


def _without_diacritics(text: str) -> str:
    return "".join(char for char in normalize("NFD", text) if category(char) != "Mn")


def _classify(source: str, replacement: str) -> CorrectionKind:
    changed = source + replacement
    if changed and all(char.isspace() for char in changed):
        return CorrectionKind.WHITESPACE
    visible = [char for char in changed if not char.isspace()]
    if visible and all(category(char).startswith("P") for char in visible):
        return CorrectionKind.PUNCTUATION
    if source and replacement and _without_diacritics(source) == _without_diacritics(replacement):
        return CorrectionKind.DIACRITICS
    if source and replacement and source.casefold() == replacement.casefold():
        return CorrectionKind.CAPITALIZATION
    return CorrectionKind.GRAMMAR


def extract_edits(
    source: str,
    replacement: str,
    confidence: float,
    applied: bool,
) -> tuple[TextEdit, ...]:
    edits: list[TextEdit] = []
    for operation, start, end, replacement_start, replacement_end in SequenceMatcher(
        None,
        source,
        replacement,
        autojunk=False,
    ).get_opcodes():
        if operation == "equal":
            continue
        original = source[start:end]
        corrected = replacement[replacement_start:replacement_end]
        edits.append(
            TextEdit(
                start,
                end,
                original,
                corrected,
                _classify(original, corrected),
                confidence,
                applied,
            )
        )
    return tuple(edits)


def apply_edits(text: str, edits: Sequence[TextEdit]) -> str:
    previous_end = 0
    for edit in edits:
        if edit.start < previous_end:
            raise ValueError("edits overlap or are out of order")
        if text[edit.start : edit.end] != edit.source:
            raise ValueError("edit source text does not match input")
        previous_end = edit.end

    output = text
    for edit in reversed(edits):
        output = output[: edit.start] + edit.replacement + output[edit.end :]
    return output


def protected_literals(text: str) -> tuple[str, ...]:
    matches: list[tuple[int, int, str]] = []
    for pattern in _PROTECTED_PATTERNS:
        for match in pattern.finditer(text):
            literal = match.group().rstrip(_TRAILING_SENTENCE_PUNCTUATION)
            if literal:
                matches.append((match.start(), match.start() + len(literal), literal))

    literals: list[str] = []
    previous_end = 0
    for start, end, literal in sorted(matches, key=lambda item: (item[0], -item[1])):
        if start < previous_end:
            continue
        literals.append(literal)
        previous_end = end
    return tuple(literals)


def candidate_is_safe(source: str, candidate: str, max_changed_ratio: float) -> bool:
    if not 0.0 <= max_changed_ratio <= 1.0:
        raise ValueError("max_changed_ratio must be between 0 and 1")
    if source and not candidate:
        return False
    for literal in protected_literals(source):
        if candidate.count(literal) < source.count(literal):
            return False

    changed = sum(
        max(source_end - source_start, candidate_end - candidate_start)
        for operation, source_start, source_end, candidate_start, candidate_end in SequenceMatcher(
            None,
            source,
            candidate,
            autojunk=False,
        ).get_opcodes()
        if operation != "equal"
    )
    return changed / max(len(source), 1) <= max_changed_ratio


def remove_adjacent_repeated_words(text: str) -> str:
    return _ADJACENT_REPEATED_WORD.sub(r"\1", text)
