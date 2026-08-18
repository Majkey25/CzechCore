from collections.abc import Sequence
from typing import ClassVar

class ProcessingError:
    message: str
    def occurred(self) -> bool: ...

class Word:
    id: int
    form: str
    misc: str
    def getTokenRangeStart(self) -> int: ...
    def getTokenRangeEnd(self) -> int: ...

class MultiwordToken:
    idFirst: int
    idLast: int
    form: str
    def getTokenRangeStart(self) -> int: ...
    def getTokenRangeEnd(self) -> int: ...

class Words(Sequence[Word]): ...
class MultiwordTokens(Sequence[MultiwordToken]): ...

class Sentence:
    words: Words
    multiwordTokens: MultiwordTokens

class InputFormat:
    def setText(self, text: str) -> None: ...
    def nextSentence(self, sentence: Sentence, error: ProcessingError) -> bool: ...

class Model:
    DEFAULT: ClassVar[str]
    TOKENIZER_RANGES: ClassVar[str]
    @staticmethod
    def load(path: str) -> Model | None: ...
    def newTokenizer(self, options: str) -> InputFormat | None: ...
