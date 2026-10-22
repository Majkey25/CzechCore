from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
from typing import Literal, cast

from transformers.models.bart.configuration_bart import BartConfig

COPY_FILES = (
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "generation_config.json",
)
Quantization = Literal[
    "float32",
    "float16",
    "bfloat16",
    "int16",
    "int8",
    "int8_float32",
]
QUANTIZATION: tuple[Quantization, ...] = (
    "float32",
    "float16",
    "bfloat16",
    "int16",
    "int8",
    "int8_float32",
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert the pinned Czech BART model")
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--quantization", choices=QUANTIZATION, default="float32")
    parser.add_argument("--force", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    model = cast(Path, arguments.model).resolve()
    output = cast(Path, arguments.output).resolve()
    if not (model / "model.safetensors").is_file():
        raise FileNotFoundError(f"model.safetensors not found in {model}")

    from ctranslate2.converters import TransformersConverter

    # Standard Hugging Face BART is post-norm. CTranslate2 4.8.x still reads
    # this configuration attribute, which Transformers 5 removed.
    setattr(BartConfig, "normalize_before", False)  # noqa: B010 - compatibility shim
    converter = TransformersConverter(str(model), copy_files=list(COPY_FILES))
    converted = converter.convert(
        str(output),
        quantization=cast(Quantization, arguments.quantization),
        force=cast(bool, arguments.force),
    )
    print(converted)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
