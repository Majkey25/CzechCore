"""CTranslate2 typing surface used by portable research tools."""

class ScoringResult:
    tokens: list[str]
    log_probs: list[float]

class Translator:
    def __init__(self, model_path: str, device: str = ..., *, compute_type: str = ...) -> None: ...
    def score_batch(
        self, source: list[list[str]], target: list[list[str]]
    ) -> list[ScoringResult]: ...
