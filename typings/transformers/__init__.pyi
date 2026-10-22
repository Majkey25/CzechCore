from collections.abc import Sequence
from os import PathLike
from typing import Self

from torch import Tensor, device

class TokenizerModel: ...

class BackendTokenizer:
    model: TokenizerModel

class PreTrainedTokenizerFast:
    backend_tokenizer: BackendTokenizer
    pad_token_id: int
    @classmethod
    def from_pretrained(
        cls,
        pretrained_model_name_or_path: str | PathLike[str],
        *,
        local_files_only: bool = ...,
    ) -> Self: ...
    def __call__(
        self,
        text: str | Sequence[str],
        *,
        return_tensors: str,
        truncation: bool = ...,
        padding: bool = ...,
    ) -> dict[str, Tensor]: ...
    def batch_decode(self, sequences: Tensor, *, skip_special_tokens: bool) -> list[str]: ...
    def encode(self, text: str, *, add_special_tokens: bool, truncation: bool) -> list[int]: ...
    def decode(self, token_ids: Tensor, *, skip_special_tokens: bool) -> str: ...

class Seq2SeqConfig:
    max_position_embeddings: int

class Seq2SeqOutput:
    logits: Tensor

class GenerateOutput:
    sequences: Tensor
    sequences_scores: Tensor

class Seq2SeqModel:
    config: Seq2SeqConfig
    def to(self, target: device) -> Self: ...
    def eval(self) -> Self: ...
    def __call__(
        self,
        *,
        input_ids: Tensor,
        attention_mask: Tensor,
        labels: Tensor,
    ) -> Seq2SeqOutput: ...
    def generate(
        self,
        *,
        input_ids: Tensor,
        attention_mask: Tensor,
        max_new_tokens: int,
        num_beams: int,
        num_return_sequences: int,
        do_sample: bool,
        return_dict_in_generate: bool,
        output_scores: bool,
    ) -> GenerateOutput: ...

class AutoModelForSeq2SeqLM:
    @classmethod
    def from_pretrained(
        cls,
        pretrained_model_name_or_path: str | PathLike[str],
        *,
        local_files_only: bool = ...,
    ) -> Seq2SeqModel: ...
