from collections.abc import Sequence
from typing import ClassVar

class ProcessingError:
    message: str
    def occurred(self) -> bool: ...

class Word:
    form: str
    misc: str

class Words(Sequence[Word]): ...

class Sentence:
    words: Words

class InputFormat:
    def setText(self, text: str) -> None: ...
    def nextSentence(self, sentence: Sentence, error: ProcessingError) -> bool: ...

class Model:
    DEFAULT: ClassVar[str]
    TOKENIZER_RANGES: ClassVar[str]
    @staticmethod
    def load(path: str) -> Model | None: ...
    def newTokenizer(self, options: str) -> InputFormat | None: ...
