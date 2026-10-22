from __future__ import annotations

from collections.abc import Sequence

import pytest

from czechcore.assets import AssetMissingError
from czechcore.backend import (
    MAX_INFERENCE_BATCH,
    MAX_SENTENCE_CHARACTERS,
    SentenceTooLongError,
    TransformerBackend,
    normalize_hypotheses,
)
from czechcore.core import Hypothesis


def test_softmax_confidences_sum_to_one() -> None:
    hypotheses = normalize_hypotheses((("oprava", -0.1), ("zdroj", -2.0)))

    assert sum(item.confidence for item in hypotheses) == pytest.approx(1.0)
    assert hypotheses[0].text == "oprava"
    assert hypotheses[0].confidence > hypotheses[1].confidence


def test_normalization_keeps_best_score_for_duplicate_text() -> None:
    hypotheses = normalize_hypotheses((("stejné", -2.0), ("stejné", -0.2), ("jiné", -1.0)))

    assert [(item.text, item.score) for item in hypotheses] == [("stejné", -0.2), ("jiné", -1.0)]


def test_normalization_rejects_empty_input() -> None:
    with pytest.raises(ValueError, match="hypothesis"):
        normalize_hypotheses(())


class PreflightTokenizer:
    def __init__(self) -> None:
        self.encoded = False

    def encode(self, text: str, *, add_special_tokens: bool, truncation: bool) -> list[int]:
        self.encoded = True
        assert add_special_tokens and not truncation
        return [0] * 257

    def __call__(
        self, text: Sequence[str], *, return_tensors: str, truncation: bool, padding: bool
    ) -> None:
        raise AssertionError("oversized sentence reached tensor allocation")


@pytest.mark.parametrize("character_overflow", [False, True])
def test_length_limits_run_before_tensor_allocation(
    monkeypatch: pytest.MonkeyPatch, character_overflow: bool
) -> None:
    backend = TransformerBackend.__new__(TransformerBackend)
    tokenizer = PreflightTokenizer()
    monkeypatch.setattr(backend, "_tokenizer", tokenizer, raising=False)
    monkeypatch.setattr(backend, "_max_tokens", 256, raising=False)
    sentence = " " * (MAX_SENTENCE_CHARACTERS + 1) if character_overflow else "dlouhá věta"

    with pytest.raises(SentenceTooLongError):
        backend.hypotheses(sentence)

    assert tokenizer.encoded is not character_overflow


class RecordingBackend(TransformerBackend):
    def __init__(self) -> None:
        self.seen: list[str] = []

    def _hypotheses_batch(
        self, tokenized_sentences: Sequence[str]
    ) -> tuple[tuple[Hypothesis, ...], ...]:
        assert len(tokenized_sentences) <= MAX_INFERENCE_BATCH
        self.seen.extend(tokenized_sentences)
        return tuple((Hypothesis(sentence, -0.1, 1.0),) for sentence in tokenized_sentences)


def test_backend_bounds_direct_batch_calls_without_losing_inputs() -> None:
    backend = RecordingBackend()
    sources = tuple(f"Věta {index}." for index in range(MAX_INFERENCE_BATCH * 2 + 1))

    predictions = backend.hypotheses_many(sources)

    assert tuple(backend.seen) == sources
    assert tuple(prediction[0].text for prediction in predictions) == sources


@pytest.fixture(scope="module")
def backend() -> TransformerBackend:
    try:
        return TransformerBackend()
    except AssetMissingError:
        pytest.skip("run `czechcore download` to install model assets")


@pytest.mark.model
@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("Muži přišly domů .", "Muži přišli domů."),
        ("Když přišel domů šel spát .", "Když přišel domů, šel spát."),
        ("Bili psa .", "Bili psa."),
    ],
)
def test_real_model_contextual_corrections(
    backend: TransformerBackend,
    source: str,
    expected: str,
) -> None:
    assert backend.hypotheses(source)[0].text == expected


@pytest.mark.model
def test_real_model_batch_matches_single_predictions(backend: TransformerBackend) -> None:
    sources = ("Muži přišly domů .", "Když přišel domů šel spát .", "Bili psa .")

    predictions = backend.hypotheses_many(sources)

    assert [items[0].text for items in predictions] == [
        "Muži přišli domů.",
        "Když přišel domů, šel spát.",
        "Bili psa.",
    ]
