from __future__ import annotations

import json
from pathlib import Path

import pytest
import torch
from tokenizers import Tokenizer
from tokenizers.models import WordLevel
from transformers import AutoModelForSeq2SeqLM, PreTrainedTokenizerFast
from transformers.models.bart.configuration_bart import BartConfig

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


def test_float32_bart_conversion_preserves_token_scores(tmp_path: Path) -> None:
    pytest.importorskip(
        "ctranslate2",
        reason="install the portable extra for FP32 conversion",
        exc_type=ModuleNotFoundError,
    )
    from ctranslate2 import Translator

    source = tmp_path / "source"
    vocabulary = {"<s>": 0, "<pad>": 1, "</s>": 2, "<unk>": 3, "Když": 4, "přišel": 5}
    tokenizer = PreTrainedTokenizerFast(
        tokenizer_object=Tokenizer(WordLevel(vocabulary, unk_token="<unk>")),
        bos_token="<s>",
        eos_token="</s>",
        unk_token="<unk>",
        pad_token="<pad>",
    )
    tokenizer.save_pretrained(source)
    (source / "special_tokens_map.json").write_text(
        json.dumps({"bos_token": "<s>", "eos_token": "</s>", "unk_token": "<unk>"}),
        encoding="utf-8",
    )
    config = BartConfig(
        vocab_size=len(vocabulary),
        d_model=16,
        encoder_layers=2,
        decoder_layers=2,
        encoder_attention_heads=2,
        decoder_attention_heads=2,
        encoder_ffn_dim=32,
        decoder_ffn_dim=32,
        max_position_embeddings=32,
        decoder_start_token_id=2,
        bos_token_id=0,
        pad_token_id=1,
        eos_token_id=2,
    )
    model = AutoModelForSeq2SeqLM.from_config(config).eval()
    model.save_pretrained(source)
    output = tmp_path / "converted"

    assert main(["--model", str(source), "--output", str(output)]) == 0
    for filename in COPY_FILES:
        assert (output / filename).read_bytes() == (source / filename).read_bytes()

    translator = Translator(str(output), device="cpu", compute_type="float32")
    sources = [["<s>", "Když", "přišel", "</s>"], ["<s>", "přišel", "</s>"]]
    targets = [["Když", "přišel"], ["přišel"]]
    scores = translator.score_batch(sources, targets)
    for tokens, target, score in zip(sources, targets, scores, strict=True):
        input_ids = torch.tensor([[vocabulary[token] for token in tokens]])
        labels = torch.tensor([[vocabulary[token] for token in [*target, "</s>"]]])
        with torch.inference_mode():
            logits = model(
                input_ids=input_ids, attention_mask=torch.ones_like(input_ids), labels=labels
            ).logits
        expected = logits.log_softmax(dim=-1).gather(-1, labels.unsqueeze(-1)).squeeze(-1)[0]
        assert score.tokens == [*target, "</s>"]
        torch.testing.assert_close(torch.tensor(score.log_probs), expected, rtol=1e-5, atol=1e-5)
