from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ufal.udpipe import Model, ProcessingError, Sentence

from czechcore.assets import local_udpipe_model


@dataclass(frozen=True, slots=True)
class SentenceSpan:
    start: int
    end: int
    tokenized: str

    def __post_init__(self) -> None:
        if self.start < 0 or self.end <= self.start:
            raise ValueError("invalid sentence range")
        if not self.tokenized:
            raise ValueError("tokenized sentence cannot be empty")


def parse_token_range(metadata: str) -> tuple[int, int]:
    for item in metadata.split("|"):
        key, separator, value = item.partition("=")
        if key != "TokenRange" or not separator:
            continue
        try:
            start_text, end_text = value.split(":", maxsplit=1)
            start, end = int(start_text), int(end_text)
        except ValueError as error:
            raise ValueError(f"invalid TokenRange metadata: {metadata!r}") from error
        if start < 0 or end <= start:
            raise ValueError(f"invalid TokenRange metadata: {metadata!r}")
        return start, end
    raise ValueError(f"missing TokenRange metadata: {metadata!r}")


class CzechTokenizer:
    def __init__(self, model_path: Path | None = None) -> None:
        path = model_path or local_udpipe_model()
        model = Model.load(str(path))
        if model is None:
            raise RuntimeError(f"cannot load UDPipe model: {path}")
        self._model = model

    def sentences(self, text: str) -> tuple[SentenceSpan, ...]:
        if not text:
            return ()
        tokenizer = self._model.newTokenizer(Model.TOKENIZER_RANGES)
        if tokenizer is None:
            raise RuntimeError("UDPipe model has no tokenizer")
        tokenizer.setText(text)
        sentence = Sentence()
        error = ProcessingError()
        spans: list[SentenceSpan] = []
        while tokenizer.nextSentence(sentence, error):
            if len(sentence.words) <= 1:
                continue
            words = sentence.words[1:]
            start, _ = parse_token_range(words[0].misc)
            _, end = parse_token_range(words[-1].misc)
            spans.append(SentenceSpan(start, end, " ".join(word.form for word in words)))
        if error.occurred():
            raise RuntimeError(error.message)
        return tuple(spans)
