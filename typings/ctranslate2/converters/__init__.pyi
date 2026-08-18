from typing import Literal

Quantization = Literal[
    "float32",
    "float16",
    "bfloat16",
    "int16",
    "int8",
    "int8_float32",
]

class TransformersConverter:
    def __init__(self, model_name_or_path: str, copy_files: list[str] | None = None) -> None: ...
    def convert(
        self,
        output_dir: str,
        vmap: str | None = None,
        quantization: Quantization | None = None,
        force: bool = False,
    ) -> str: ...
