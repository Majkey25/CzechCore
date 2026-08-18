# Offline Czech Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a tested offline Czech sentence correction engine with structured edits, safe abstention, CLI access, and a real UFAL model smoke test.

**Architecture:** Python orchestrates the exact UDPipe tokenizer and the compact UFAL Transformer baseline. The core stays backend-neutral, converts accepted sentence hypotheses into Unicode edits, protects technical literals, and applies edits only under an explicit confidence policy.

**Tech Stack:** Python 3.12, PyTorch, Transformers, `ufal.udpipe`, pytest, Ruff, Pyright.

**Spec:** `docs/superpowers/specs/2026-08-18-offline-czech-engine-design.md`

## Global Constraints

- User text never leaves the device.
- Normal mode returns suggestions and preserves the original output text.
- Autocorrect is opt-in and defaults to `min_confidence=0.995`.
- Source offsets are zero-based Unicode code-point offsets.
- Default model assets remain external and CC BY-NC-SA 4.0.
- Python version is 3.12.
- No silent truncation, cloud inference, rule DSL, or platform adapter.

---

### Task 1: Project contract and core edits

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `src/czechcore/__init__.py`
- Create: `src/czechcore/core.py`
- Create: `tests/test_core.py`

**Interfaces:**
- Produces: `CorrectionKind`, `TextEdit`, `CorrectionResult`, `Hypothesis`, `extract_edits()`, `apply_edits()`.

- [ ] **Step 1: Create strict project configuration**

Use Python 3.12, a `src` layout, Ruff, strict Pyright, and pytest. Runtime
dependencies are `torch`, `transformers`, and `ufal.udpipe`; development
dependencies are pytest, pytest-cov, Ruff, and Pyright.

- [ ] **Step 2: Write failing edit tests**

```python
def test_extracts_diacritics_and_punctuation_with_original_offsets() -> None:
    edits = extract_edits("Rekl ze prijde.", "Řekl, že přijde.", 0.99, False)
    assert apply_edits("Rekl ze prijde.", edits) == "Řekl, že přijde."
    assert [edit.kind for edit in edits] == [
        CorrectionKind.DIACRITICS,
        CorrectionKind.PUNCTUATION,
        CorrectionKind.DIACRITICS,
        CorrectionKind.DIACRITICS,
    ]
```

- [ ] **Step 3: Run the test and confirm RED**

Run: `.venv/Scripts/python -m pytest tests/test_core.py -q`

Expected: collection fails because `czechcore` does not exist.

- [ ] **Step 4: Implement immutable result types and edit extraction**

Use `SequenceMatcher(autojunk=False)`, Unicode categories, and NFD diacritic
stripping. Validate edit bounds, order, source slices, and confidence in
`TextEdit.__post_init__`.

- [ ] **Step 5: Run the test and confirm GREEN**

Run: `.venv/Scripts/python -m pytest tests/test_core.py -q`

Expected: all core edit tests pass.

### Task 2: Protected content and sentence policy

**Files:**
- Modify: `src/czechcore/core.py`
- Modify: `tests/test_core.py`

**Interfaces:**
- Produces: `protected_literals(text: str) -> tuple[str, ...]`, `candidate_is_safe(source: str, candidate: str, max_changed_ratio: float) -> bool`.

- [ ] **Step 1: Write failing protection tests**

```python
@pytest.mark.parametrize(
    ("source", "candidate"),
    [
        ("Piš na majkey25@example.cz.", "Piš na majkey25 @ example.cz."),
        ("Použij C++20.", "Použij C + + 20."),
        ("Verze je v1.2.3.", "Verze je v 1.2.3."),
    ],
)
def test_rejects_candidate_that_changes_protected_literal(source: str, candidate: str) -> None:
    assert not candidate_is_safe(source, candidate, 0.35)
```

- [ ] **Step 2: Run the test and confirm RED**

Run: `.venv/Scripts/python -m pytest tests/test_core.py -q`

Expected: import fails for the missing safety functions.

- [ ] **Step 3: Implement mechanical protection and edit-ratio checks**

Compile only format regexes for URL, email, Windows path, semantic version, and
code-like tokens. Reject candidates that do not preserve each literal exactly.

- [ ] **Step 4: Run the test and confirm GREEN**

Run: `.venv/Scripts/python -m pytest tests/test_core.py -q`

Expected: all protection tests pass.

### Task 3: Exact UDPipe asset and tokenizer

**Files:**
- Create: `src/czechcore/assets.py`
- Create: `src/czechcore/tokenizer.py`
- Create: `tests/test_tokenizer.py`

**Interfaces:**
- Produces: `ensure_udpipe_model(cache_dir: Path | None = None) -> Path`.
- Produces: `SentenceSpan(start: int, end: int, tokenized: str)` and `CzechTokenizer.sentences(text: str) -> tuple[SentenceSpan, ...]`.

- [ ] **Step 1: Write failing tokenizer boundary tests**

```python
def test_sentence_ranges_preserve_original_text(tokenizer: CzechTokenizer) -> None:
    text = "První věta.  Druhá věta!"
    spans = tokenizer.sentences(text)
    assert [text[item.start : item.end] for item in spans] == ["První věta.", "Druhá věta!"]
    assert spans[0].tokenized == "První věta ."
```

- [ ] **Step 2: Run the test and confirm RED**

Run: `.venv/Scripts/python -m pytest tests/test_tokenizer.py -q`

Expected: missing tokenizer module.

- [ ] **Step 3: Implement verified asset download**

Download the pinned upstream file with `urllib.request.urlretrieve`, calculate
SHA-256 while streaming, atomically replace the destination only on hash match,
and delete invalid temporary files. Expected SHA-256:
`8ced138bf1c2121cf03d2494f08c663a8b27b5218fb9c322064a7d943ba02266`.

- [ ] **Step 4: Implement UDPipe ranges**

Load the model once per tokenizer instance, use `Model.TOKENIZER_RANGES`, parse
`TokenRange=start:end`, and build each sentence's exact outer span plus
space-joined forms.

- [ ] **Step 5: Run the test and confirm GREEN**

Run: `.venv/Scripts/python -m pytest tests/test_tokenizer.py -q`

Expected: tokenizer tests pass with the already cached fixture model.

### Task 4: Real Transformer backend

**Files:**
- Create: `src/czechcore/backend.py`
- Create: `tests/test_backend.py`

**Interfaces:**
- Produces: `TransformerBackend(model_id: str = DEFAULT_MODEL_ID)`.
- Produces: `TransformerBackend.hypotheses(tokenized_sentence: str) -> tuple[Hypothesis, ...]`.

- [ ] **Step 1: Write failing lightweight backend contract tests**

```python
def test_softmax_confidences_sum_to_one() -> None:
    hypotheses = normalize_hypotheses([("oprava", -0.1), ("zdroj", -2.0)])
    assert sum(item.confidence for item in hypotheses) == pytest.approx(1.0)
    assert hypotheses[0].confidence > hypotheses[1].confidence
```

- [ ] **Step 2: Run the test and confirm RED**

Run: `.venv/Scripts/python -m pytest tests/test_backend.py -q`

Expected: missing backend module.

- [ ] **Step 3: Implement explicit WordPiece loading and beam inference**

Load `PreTrainedTokenizerFast`, verify the backend model class contains
`WordPiece`, then load `AutoModelForSeq2SeqLM`. Generate four beams without
sampling, decode unique outputs, include the unchanged sentence, and score
candidate targets using mean token log likelihood.

- [ ] **Step 4: Run unit tests and confirm GREEN**

Run: `.venv/Scripts/python -m pytest tests/test_backend.py -q`

Expected: math/validation tests pass without model download.

- [ ] **Step 5: Run real model smoke scenarios**

Run: `.venv/Scripts/python -m pytest tests/test_backend.py -m model -q`

Expected corrections include `Muži přišli domů.`, `Ženy šly do obchodu.`,
`Když přišel domů, šel spát.`, and unchanged `Bili psa.` / `Byli doma.`.

### Task 5: Engine and CLI

**Files:**
- Create: `src/czechcore/engine.py`
- Create: `src/czechcore/cli.py`
- Modify: `src/czechcore/__init__.py`
- Create: `tests/test_engine.py`
- Create: `tests/test_cli.py`

**Interfaces:**
- Produces: `CzechCore.correct(text: str, *, autocorrect: bool = False, min_confidence: float = 0.995) -> CorrectionResult`.
- Produces console script: `czechcore`.

- [ ] **Step 1: Write failing engine policy tests**

```python
def test_suggestion_does_not_apply_candidate(engine: CzechCore) -> None:
    result = engine.correct("Muži přišly domů.")
    assert result.suggested_text == "Muži přišli domů."
    assert result.output_text == result.original_text
    assert result.edits and not result.edits[0].applied


def test_autocorrect_abstains_below_threshold(engine: CzechCore) -> None:
    result = engine.correct("Muži přišly domů.", autocorrect=True, min_confidence=0.99)
    assert result.output_text == result.original_text
```

- [ ] **Step 2: Run tests and confirm RED**

Run: `.venv/Scripts/python -m pytest tests/test_engine.py tests/test_cli.py -q`

Expected: missing engine and CLI.

- [ ] **Step 3: Implement sentence orchestration and atomic edits**

Validate thresholds, gather accepted sentence hypotheses, offset local edits into
the full input, and compute suggested/output text with right-to-left application.
Dependency-inject tokenizer/backend protocols so policy tests run without a model.

- [ ] **Step 4: Implement stdlib CLI**

Use `argparse`. Serialize dataclasses exactly once with `json.dumps`; UTF-8 Czech
must remain readable with `ensure_ascii=False`.

- [ ] **Step 5: Run tests and confirm GREEN**

Run: `.venv/Scripts/python -m pytest tests/test_engine.py tests/test_cli.py -q`

Expected: all engine and CLI tests pass.

### Task 6: Benchmark, documentation, and publication

**Files:**
- Create: `benchmarks/cases.jsonl`
- Create: `src/czechcore/benchmark.py`
- Create: `README.md`
- Create: `LICENSE`
- Create: `NOTICE.md`
- Create: `.github/workflows/ci.yml`
- Create: `tests/test_benchmark.py`

**Interfaces:**
- Produces console script: `czechcore-benchmark PATH`.

- [ ] **Step 1: Write failing benchmark metric tests**

```python
def test_metrics_count_false_changes_to_correct_sentences() -> None:
    metrics = evaluate_pairs([("Správně.", "Správně.", "Špatně.")])
    assert metrics.changed_correct_sentences == 1
    assert metrics.exact_matches == 0
```

- [ ] **Step 2: Run test and confirm RED**

Run: `.venv/Scripts/python -m pytest tests/test_benchmark.py -q`

Expected: missing benchmark module.

- [ ] **Step 3: Implement metrics and a Czech acceptance corpus**

JSONL fields are `source`, `reference`, and `category`. Include correct/incorrect
pairs for agreement, commas, diacritics, contextual homographs, and protected
technical text. Report counts and latency without claiming corpus-wide accuracy.

- [ ] **Step 4: Document exact use and limitations**

README must include installation, download, suggestion/autocorrect examples,
structured JSON, offline behavior, model attribution, non-commercial asset
restriction, measured sample results, and no correctness guarantee.

- [ ] **Step 5: Run all quality gates**

Run:

```text
.venv/Scripts/python -m pytest -m "not model" --cov=czechcore --cov-report=term-missing
.venv/Scripts/python -m ruff check .
.venv/Scripts/python -m ruff format --check .
.venv/Scripts/python -m pyright --pythonpath .venv/Scripts/python.exe
```

Expected: zero failures/errors.

- [ ] **Step 6: Run live engine scenarios and benchmark**

Run:

```text
.venv/Scripts/czechcore check --json "Když přišel domů šel spát."
.venv/Scripts/czechcore check --autocorrect --min-confidence 0.5 "Muži přišly domů."
.venv/Scripts/czechcore check "Kontakt je majkey25@example.cz a verze v1.2.3."
.venv/Scripts/czechcore-benchmark benchmarks/cases.jsonl
```

Expected: valid JSON, gated application, protected literals preserved, and honest
benchmark totals.

- [ ] **Step 7: Review diff, clean scratch data, commit, and push**

Inspect `git diff --check`, `git diff --stat`, and `git status -sb`. Remove
`.reference/tmp`. Commit only project files with `feat: add offline Czech correction engine`, then push the new public repository's default branch.
