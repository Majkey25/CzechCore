from __future__ import annotations

import pytest

from czechcore.assets import AssetMissingError
from czechcore.backend import TransformerBackend, normalize_hypotheses


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
