from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Never

import pytest

from czechcore import assets
from czechcore.assets import AssetMissingError, download_udpipe_model, local_udpipe_model
from czechcore.tokenizer import CzechTokenizer, parse_token_range


def test_parses_token_range_from_udpipe_metadata() -> None:
    assert parse_token_range("TokenRange=7:12|SpaceAfter=No") == (7, 12)


@pytest.mark.parametrize("metadata", ["", "SpaceAfter=No", "TokenRange=x:2"])
def test_rejects_invalid_token_range(metadata: str) -> None:
    with pytest.raises(ValueError, match="TokenRange"):
        parse_token_range(metadata)


def test_missing_cached_model_is_explicit(tmp_path: Path) -> None:
    with pytest.raises(AssetMissingError, match="czechcore download"):
        local_udpipe_model(tmp_path)


def test_download_reuses_valid_cached_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = b"verified tokenizer"
    path = tmp_path / assets.UDPIPE_FILENAME
    path.write_bytes(payload)
    monkeypatch.setattr(assets, "UDPIPE_SHA256", hashlib.sha256(payload).hexdigest())

    def fail_urlopen(url: str, timeout: int) -> Never:
        raise AssertionError(f"unexpected download: {url} ({timeout})")

    monkeypatch.setattr(assets, "urlopen", fail_urlopen)

    assert download_udpipe_model(tmp_path) == path


@pytest.mark.model
def test_sentence_ranges_preserve_original_text() -> None:
    try:
        tokenizer = CzechTokenizer()
    except AssetMissingError:
        pytest.skip("run `czechcore download` to install model assets")

    text = "První věta.  Druhá věta!"
    spans = tokenizer.sentences(text)

    assert [text[item.start : item.end] for item in spans] == ["První věta.", "Druhá věta!"]
    assert spans[0].tokenized == "První věta ."


@pytest.mark.model
def test_multiword_token_preserves_surface_form_and_range() -> None:
    try:
        tokenizer = CzechTokenizer()
    except AssetMissingError:
        pytest.skip("run `czechcore download` to install model assets")

    text = "Kdybych měla čas, nespěchala bych do práce."
    span = tokenizer.sentences(text)[0]

    assert text[span.start : span.end] == text
    assert span.tokenized.startswith("Kdybych měla čas")
