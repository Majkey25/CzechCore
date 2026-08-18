from __future__ import annotations

from collections.abc import Iterable
from math import exp, isfinite
from pathlib import Path
from typing import Protocol

import torch
from torch import Tensor
from transformers import AutoModelForSeq2SeqLM, PreTrainedTokenizerFast

from czechcore.assets import local_transformer_model
from czechcore.core import Hypothesis


class SentenceTooLongError(ValueError):
    pass


class CorrectionBackend(Protocol):
    def hypotheses(self, tokenized_sentence: str) -> tuple[Hypothesis, ...]: ...


def normalize_hypotheses(items: Iterable[tuple[str, float]]) -> tuple[Hypothesis, ...]:
    unique: dict[str, float] = {}
    for text, score in items:
        if not text or not isfinite(score):
            raise ValueError("hypothesis text and score must be valid")
        unique[text] = max(score, unique.get(text, float("-inf")))
    if not unique:
        raise ValueError("at least one hypothesis is required")

    ordered = sorted(unique.items(), key=lambda item: item[1], reverse=True)
    highest = ordered[0][1]
    weights = [exp(score - highest) for _, score in ordered]
    total = sum(weights)
    return tuple(
        Hypothesis(text, score, weight / total)
        for (text, score), weight in zip(ordered, weights, strict=True)
    )


class TransformerBackend:
    def __init__(self, model_path: Path | None = None, device: str = "cpu") -> None:
        path = model_path or local_transformer_model()
        self._tokenizer = PreTrainedTokenizerFast.from_pretrained(path, local_files_only=True)
        tokenizer_model = type(self._tokenizer.backend_tokenizer.model).__name__
        if tokenizer_model != "WordPiece":
            raise RuntimeError(f"expected WordPiece tokenizer, got {tokenizer_model}")
        self._device = torch.device(device)
        self._model = AutoModelForSeq2SeqLM.from_pretrained(path, local_files_only=True)
        self._model.to(self._device)
        self._model.eval()
        self._max_tokens = int(self._model.config.max_position_embeddings)

    def _score_target(self, input_ids: Tensor, attention_mask: Tensor, target: str) -> float:
        encoded_target = self._tokenizer(target, return_tensors="pt")
        target_ids = encoded_target["input_ids"].to(self._device)
        with torch.inference_mode():
            output = self._model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=target_ids,
            )
            log_probabilities = torch.log_softmax(output.logits, dim=-1)
            selected = log_probabilities.gather(-1, target_ids.unsqueeze(-1)).squeeze(-1)
        mask = target_ids.ne(self._tokenizer.pad_token_id)
        selected = selected[:, 1:]
        mask = mask[:, 1:]
        return float(selected[mask].mean().item())

    def hypotheses(self, tokenized_sentence: str) -> tuple[Hypothesis, ...]:
        if not tokenized_sentence.strip():
            raise ValueError("tokenized sentence cannot be empty")
        encoded = self._tokenizer(tokenized_sentence, return_tensors="pt", truncation=False)
        input_ids = encoded["input_ids"].to(self._device)
        attention_mask = encoded["attention_mask"].to(self._device)
        if input_ids.shape[1] > self._max_tokens:
            raise SentenceTooLongError(
                f"sentence has {input_ids.shape[1]} tokens; maximum is {self._max_tokens}"
            )
        with torch.inference_mode():
            generated = self._model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                max_new_tokens=self._max_tokens - 1,
                num_beams=4,
                num_return_sequences=4,
                do_sample=False,
                return_dict_in_generate=True,
                output_scores=True,
            )
        candidates: list[tuple[str, float]] = list(
            zip(
                self._tokenizer.batch_decode(generated.sequences, skip_special_tokens=True),
                (float(score) for score in generated.sequences_scores),
                strict=True,
            )
        )
        normalized_source = self._tokenizer.decode(input_ids[0], skip_special_tokens=True)
        candidates.append(
            (
                normalized_source,
                self._score_target(input_ids, attention_mask, normalized_source),
            )
        )
        return normalize_hypotheses(candidates)
