from __future__ import annotations

from typing import Protocol

from czechcore.backend import CorrectionBackend, SentenceTooLongError, TransformerBackend
from czechcore.core import (
    CorrectionResult,
    Hypothesis,
    TextEdit,
    apply_edits,
    candidate_is_safe,
    extract_edits,
    remove_adjacent_repeated_words,
)
from czechcore.tokenizer import CzechTokenizer, SentenceSpan

SUGGESTION_MIN_CONFIDENCE = 0.25
MAX_CHANGED_RATIO = 0.35


class SentenceTokenizer(Protocol):
    def sentences(self, text: str) -> tuple[SentenceSpan, ...]: ...


class CzechCore:
    def __init__(
        self,
        tokenizer: SentenceTokenizer | None = None,
        backend: CorrectionBackend | None = None,
    ) -> None:
        self._tokenizer = tokenizer or CzechTokenizer()
        self._backend = backend or TransformerBackend()

    def correct(
        self,
        text: str,
        *,
        autocorrect: bool = False,
        min_confidence: float = 0.995,
    ) -> CorrectionResult:
        if not 0.0 <= min_confidence <= 1.0:
            raise ValueError("min_confidence must be between 0 and 1")
        if not text:
            return CorrectionResult("", "", "", ())

        edits: list[TextEdit] = []
        warnings: list[str] = []
        for sentence in self._tokenizer.sentences(text):
            source = text[sentence.start : sentence.end]
            mechanical = remove_adjacent_repeated_words(source)
            if mechanical != source:
                hypotheses = (Hypothesis(mechanical, 0.0, 0.95),)
            else:
                try:
                    hypotheses = self._backend.hypotheses(sentence.tokenized)
                except SentenceTooLongError:
                    warnings.append(f"sentence_too_long:{sentence.start}:{sentence.end}")
                    continue
            top = hypotheses[0]
            if top.text == source:
                continue
            if top.confidence < SUGGESTION_MIN_CONFIDENCE:
                warnings.append(f"low_confidence:{sentence.start}:{sentence.end}")
                continue
            if not candidate_is_safe(source, top.text, MAX_CHANGED_RATIO):
                warnings.append(f"unsafe_candidate:{sentence.start}:{sentence.end}")
                continue

            apply_candidate = autocorrect and top.confidence >= min_confidence
            edits.extend(
                TextEdit(
                    sentence.start + edit.start,
                    sentence.start + edit.end,
                    edit.source,
                    edit.replacement,
                    edit.kind,
                    edit.confidence,
                    edit.applied,
                )
                for edit in extract_edits(source, top.text, top.confidence, apply_candidate)
            )

        all_edits = tuple(edits)
        suggested_text = apply_edits(text, all_edits)
        applied_edits = tuple(edit for edit in all_edits if edit.applied)
        output_text = apply_edits(text, applied_edits)
        return CorrectionResult(text, suggested_text, output_text, all_edits, tuple(warnings))
