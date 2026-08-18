from __future__ import annotations

from dataclasses import dataclass

import pytest

from czechcore.backend import SentenceTooLongError
from czechcore.core import Hypothesis
from czechcore.engine import CzechCore
from czechcore.tokenizer import SentenceSpan


@dataclass(frozen=True)
class StaticTokenizer:
    tokenized: str

    def sentences(self, text: str) -> tuple[SentenceSpan, ...]:
        return (SentenceSpan(0, len(text), self.tokenized),) if text else ()


@dataclass(frozen=True)
class StaticBackend:
    values: tuple[Hypothesis, ...]

    def hypotheses(self, tokenized_sentence: str) -> tuple[Hypothesis, ...]:
        return self.values


class TooLongBackend:
    def hypotheses(self, tokenized_sentence: str) -> tuple[Hypothesis, ...]:
        raise SentenceTooLongError("too long")


class BatchBackend:
    def hypotheses(self, tokenized_sentence: str) -> tuple[Hypothesis, ...]:
        raise AssertionError("batch path expected")

    def hypotheses_many(
        self,
        tokenized_sentences: tuple[str, ...] | list[str],
    ) -> tuple[tuple[Hypothesis, ...], ...]:
        return tuple(
            (Hypothesis(sentence.replace("přišly", "přišli"), -0.1, 0.9),)
            for sentence in tokenized_sentences
        )


class SplitTokenizer:
    def sentences(self, text: str) -> tuple[SentenceSpan, ...]:
        return (
            SentenceSpan(0, 9, text[:9]),
            SentenceSpan(9, len(text), text[9:]),
        )


class SplitBackend:
    def hypotheses(self, tokenized_sentence: str) -> tuple[Hypothesis, ...]:
        candidate = "2.30 funguje." if tokenized_sentence == "2.3 funguje." else tokenized_sentence
        return (Hypothesis(candidate, -0.1, 0.9),)


def _engine(confidence: float = 0.9) -> CzechCore:
    return CzechCore(
        tokenizer=StaticTokenizer("Muži přišly domů ."),
        backend=StaticBackend(
            (
                Hypothesis("Muži přišli domů.", -0.1, confidence),
                Hypothesis("Muži přišly domů.", -2.0, 1.0 - confidence),
            )
        ),
    )


def test_suggestion_does_not_apply_candidate() -> None:
    result = _engine().correct("Muži přišly domů.")

    assert result.suggested_text == "Muži přišli domů."
    assert result.output_text == result.original_text
    assert result.edits and not result.edits[0].applied


def test_suggests_clear_top_beam_with_relative_confidence_below_half() -> None:
    engine = CzechCore(
        tokenizer=StaticTokenizer("Když přišel domů šel spát ."),
        backend=StaticBackend((Hypothesis("Když přišel domů, šel spát.", -0.001, 0.37),)),
    )

    result = engine.correct("Když přišel domů šel spát.")

    assert result.suggested_text == "Když přišel domů, šel spát."
    assert result.warnings == ()


def test_exact_repeated_word_uses_safe_mechanical_correction() -> None:
    source = "To je je vážný problém."
    engine = CzechCore(
        tokenizer=StaticTokenizer("To je je vážný problém ."),
        backend=StaticBackend((Hypothesis("To je jen vážný problém.", -0.01, 0.9),)),
    )

    result = engine.correct(source)

    assert result.suggested_text == "To je vážný problém."
    assert result.edits[0].confidence == 0.95
    assert not result.edits[0].applied


def test_autocorrect_applies_candidate_above_threshold() -> None:
    result = _engine().correct("Muži přišly domů.", autocorrect=True, min_confidence=0.8)

    assert result.output_text == "Muži přišli domů."
    assert result.edits and all(edit.applied for edit in result.edits)


def test_autocorrect_abstains_below_threshold_but_keeps_suggestion() -> None:
    result = _engine().correct("Muži přišly domů.", autocorrect=True, min_confidence=0.95)

    assert result.suggested_text == "Muži přišli domů."
    assert result.output_text == result.original_text
    assert result.edits and not any(edit.applied for edit in result.edits)


def test_rejects_candidate_that_changes_protected_text() -> None:
    source = "Použij C++20."
    engine = CzechCore(
        tokenizer=StaticTokenizer("Použij C + + 20 ."),
        backend=StaticBackend((Hypothesis("Použij C + + 20.", -0.1, 0.99),)),
    )

    result = engine.correct(source)

    assert result.suggested_text == source
    assert result.edits == ()
    assert result.warnings == ("unsafe_candidate:0:13",)


def test_too_long_sentence_is_left_unchanged() -> None:
    source = "Velmi dlouhá věta."
    engine = CzechCore(tokenizer=StaticTokenizer(source), backend=TooLongBackend())

    result = engine.correct(source)

    assert result.output_text == source
    assert result.warnings == ("sentence_too_long:0:18",)


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_rejects_invalid_autocorrect_threshold(confidence: float) -> None:
    with pytest.raises(ValueError, match="min_confidence"):
        _engine().correct("text", min_confidence=confidence)


def test_empty_text_needs_no_model_work() -> None:
    result = _engine().correct("")

    assert result.original_text == result.suggested_text == result.output_text == ""
    assert result.edits == ()


def test_correct_many_uses_batch_backend() -> None:
    engine = CzechCore(tokenizer=StaticTokenizer("Muži přišly domů."), backend=BatchBackend())

    results = engine.correct_many(("Muži přišly domů.", "Muži přišly domů."))

    assert [result.suggested_text for result in results] == [
        "Muži přišli domů.",
        "Muži přišli domů.",
    ]


def test_configurable_suggestion_threshold_abstains() -> None:
    engine = CzechCore(
        tokenizer=StaticTokenizer("Muži přišly domů."),
        backend=StaticBackend((Hypothesis("Muži přišli domů.", -0.1, 0.9),)),
        suggestion_min_confidence=0.91,
    )

    result = engine.correct("Muži přišly domů.")

    assert result.suggested_text == result.original_text
    assert result.warnings == ("low_confidence:0:17",)


def test_rejects_invalid_safety_configuration() -> None:
    with pytest.raises(ValueError, match="between 0 and 1"):
        CzechCore(
            tokenizer=StaticTokenizer("text"),
            backend=StaticBackend(()),
            suggestion_min_confidence=1.1,
        )
    with pytest.raises(ValueError, match="between 0 and 1"):
        CzechCore(
            tokenizer=StaticTokenizer("text"),
            backend=StaticBackend(()),
            max_changed_ratio=-0.1,
        )


def test_global_safety_catches_literal_split_across_sentence_spans() -> None:
    source = "Verze v1.2.3 funguje."
    engine = CzechCore(tokenizer=SplitTokenizer(), backend=SplitBackend())

    result = engine.correct(source)

    assert result.suggested_text == source
    assert result.edits == ()
    assert result.warnings == ("unsafe_document:0:21",)
