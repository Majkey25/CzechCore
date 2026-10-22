from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from czechcore.backend import (
    MAX_INFERENCE_BATCH,
    BatchCorrectionBackend,
    CorrectionBackend,
    SentenceTooLongError,
    TransformerBackend,
)
from czechcore.core import (
    CorrectionResult,
    Hypothesis,
    TextEdit,
    apply_edits,
    candidate_is_safe,
    candidate_preserves_invariants,
    extract_edits,
    remove_adjacent_repeated_words,
)
from czechcore.tokenizer import CzechTokenizer, SentenceSpan

SUGGESTION_MIN_CONFIDENCE = 0.25
MAX_CHANGED_RATIO = 0.35
MAX_DOCUMENT_CHARACTERS = 1_000_000


class SentenceTokenizer(Protocol):
    def sentences(self, text: str) -> tuple[SentenceSpan, ...]: ...


class CzechCore:
    def __init__(
        self,
        tokenizer: SentenceTokenizer | None = None,
        backend: CorrectionBackend | None = None,
        *,
        suggestion_min_confidence: float = SUGGESTION_MIN_CONFIDENCE,
        max_changed_ratio: float = MAX_CHANGED_RATIO,
    ) -> None:
        if not 0.0 <= suggestion_min_confidence <= 1.0:
            raise ValueError("suggestion_min_confidence must be between 0 and 1")
        if not 0.0 <= max_changed_ratio <= 1.0:
            raise ValueError("max_changed_ratio must be between 0 and 1")
        self._tokenizer = tokenizer or CzechTokenizer()
        self._backend = backend or TransformerBackend()
        self._suggestion_min_confidence = suggestion_min_confidence
        self._max_changed_ratio = max_changed_ratio

    def correct(
        self,
        text: str,
        *,
        autocorrect: bool = False,
        min_confidence: float = 0.995,
    ) -> CorrectionResult:
        return self.correct_many(
            (text,),
            autocorrect=autocorrect,
            min_confidence=min_confidence,
        )[0]

    def correct_many(
        self,
        texts: Sequence[str],
        *,
        autocorrect: bool = False,
        min_confidence: float = 0.995,
    ) -> tuple[CorrectionResult, ...]:
        if not 0.0 <= min_confidence <= 1.0:
            raise ValueError("min_confidence must be between 0 and 1")

        results: list[CorrectionResult] = []
        batch: list[str] = []
        characters = 0
        for text in texts:
            if len(text) > MAX_DOCUMENT_CHARACTERS:
                raise ValueError(f"document exceeds {MAX_DOCUMENT_CHARACTERS} characters")
            if batch and (
                len(batch) >= MAX_INFERENCE_BATCH
                or characters + len(text) > MAX_DOCUMENT_CHARACTERS
            ):
                results.extend(self._correct_batch(batch, autocorrect, min_confidence))
                batch = []
                characters = 0
            batch.append(text)
            characters += len(text)
        if batch:
            results.extend(self._correct_batch(batch, autocorrect, min_confidence))
        return tuple(results)

    def _correct_batch(
        self, texts: Sequence[str], autocorrect: bool, min_confidence: float
    ) -> tuple[CorrectionResult, ...]:
        sentence_work: list[list[tuple[SentenceSpan, str, tuple[Hypothesis, ...] | int]]] = []
        requests: list[str] = []
        for text in texts:
            work: list[tuple[SentenceSpan, str, tuple[Hypothesis, ...] | int]] = []
            for sentence in self._tokenizer.sentences(text):
                source = text[sentence.start : sentence.end]
                mechanical = remove_adjacent_repeated_words(source)
                if mechanical != source:
                    hypotheses: tuple[Hypothesis, ...] | int = (Hypothesis(mechanical, 0.0, 0.95),)
                else:
                    hypotheses = len(requests)
                    requests.append(sentence.tokenized)
                work.append((sentence, source, hypotheses))
            sentence_work.append(work)

        generated = self._hypotheses_many(requests)
        return tuple(
            self._build_result(
                text,
                work,
                generated,
                autocorrect,
                min_confidence,
                self._suggestion_min_confidence,
                self._max_changed_ratio,
            )
            for text, work in zip(texts, sentence_work, strict=True)
        )

    def _hypotheses_many(
        self,
        requests: Sequence[str],
    ) -> tuple[tuple[Hypothesis, ...] | None, ...]:
        if not requests:
            return ()
        if len(requests) > MAX_INFERENCE_BATCH:
            return tuple(
                hypothesis
                for offset in range(0, len(requests), MAX_INFERENCE_BATCH)
                for hypothesis in self._hypotheses_many(
                    requests[offset : offset + MAX_INFERENCE_BATCH]
                )
            )
        if isinstance(self._backend, BatchCorrectionBackend):
            try:
                return self._backend.hypotheses_many(requests)
            except SentenceTooLongError:
                pass

        generated: list[tuple[Hypothesis, ...] | None] = []
        for request in requests:
            try:
                generated.append(self._backend.hypotheses(request))
            except SentenceTooLongError:
                generated.append(None)
        return tuple(generated)

    @staticmethod
    def _build_result(
        text: str,
        work: Sequence[tuple[SentenceSpan, str, tuple[Hypothesis, ...] | int]],
        generated: Sequence[tuple[Hypothesis, ...] | None],
        autocorrect: bool,
        min_confidence: float,
        suggestion_min_confidence: float,
        max_changed_ratio: float,
    ) -> CorrectionResult:
        if not text:
            return CorrectionResult("", "", "", ())

        edits: list[TextEdit] = []
        warnings: list[str] = []
        for sentence, source, hypothesis_source in work:
            hypotheses = (
                generated[hypothesis_source]
                if isinstance(hypothesis_source, int)
                else hypothesis_source
            )
            if hypotheses is None:
                warnings.append(f"sentence_too_long:{sentence.start}:{sentence.end}")
                continue
            top = hypotheses[0]
            if top.text == source:
                continue
            if top.confidence < suggestion_min_confidence:
                warnings.append(f"low_confidence:{sentence.start}:{sentence.end}")
                continue
            if not candidate_is_safe(source, top.text, max_changed_ratio):
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
        if not candidate_preserves_invariants(text, suggested_text):
            return CorrectionResult(
                text,
                text,
                text,
                (),
                (*warnings, f"unsafe_document:0:{len(text)}"),
            )
        applied_edits = tuple(edit for edit in all_edits if edit.applied)
        output_text = apply_edits(text, applied_edits)
        return CorrectionResult(text, suggested_text, output_text, all_edits, tuple(warnings))
