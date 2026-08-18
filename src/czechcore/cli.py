from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Sequence
from dataclasses import asdict
from io import TextIOWrapper
from typing import Protocol, cast

from czechcore.assets import AssetMissingError, download_assets
from czechcore.core import CorrectionResult
from czechcore.engine import CzechCore


class Engine(Protocol):
    def correct(
        self,
        text: str,
        *,
        autocorrect: bool = False,
        min_confidence: float = 0.995,
    ) -> CorrectionResult: ...


class ReconfigurableOutput(Protocol):
    def reconfigure(self, *, encoding: str) -> None: ...


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="czechcore")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("download", help="download and verify local model assets")

    check = commands.add_parser("check", help="check Czech text")
    check.add_argument("text", nargs="+")
    check.add_argument("--json", action="store_true", dest="as_json")
    check.add_argument("--autocorrect", action="store_true")
    check.add_argument("--min-confidence", type=float, default=0.995)
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    engine_factory: Callable[[], Engine] = CzechCore,
) -> int:
    standard_output = sys.stdout  # pyright: ignore[reportUnknownMemberType] Python 3.14 stub
    if isinstance(standard_output, TextIOWrapper):
        cast(ReconfigurableOutput, standard_output).reconfigure(encoding="utf-8")
    arguments = _parser().parse_args(argv)
    command = cast(str, arguments.command)
    if command == "download":
        udpipe_path, model_path = download_assets()
        print(f"UDPipe: {udpipe_path}")
        print(f"Transformer: {model_path}")
        return 0

    text = " ".join(cast(list[str], arguments.text))
    autocorrect = cast(bool, arguments.autocorrect)
    min_confidence = cast(float, arguments.min_confidence)
    try:
        result = engine_factory().correct(
            text,
            autocorrect=autocorrect,
            min_confidence=min_confidence,
        )
    except AssetMissingError as error:
        print(error, file=sys.stderr)
        return 2

    if cast(bool, arguments.as_json):
        print(json.dumps(asdict(result), ensure_ascii=False))
    else:
        print(result.output_text if autocorrect else result.suggested_text)
    return 0
