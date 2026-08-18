from __future__ import annotations

from pathlib import Path

import pytest

from tools.portable.convert_model import COPY_FILES, main


def test_converter_requires_a_real_model_directory(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match=r"model\.safetensors"):
        main(["--model", str(tmp_path), "--output", str(tmp_path / "converted")])


def test_converter_copies_tokenizer_and_generation_contract() -> None:
    assert COPY_FILES == (
        "tokenizer.json",
        "tokenizer_config.json",
        "special_tokens_map.json",
        "generation_config.json",
    )
