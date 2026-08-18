# Offline Czech Correction Engine Design

## Goal

Build a production-shaped, fully local Czech grammar correction engine. It must
correct spelling, diacritics, punctuation, agreement, and contextual grammar,
return exact edits for underlines, and support opt-in high-confidence automatic
application. Android and Windows integration are separate later projects.

No grammar checker can guarantee every suggestion is correct. CzechCore therefore
optimizes for precision and abstains when a candidate is ambiguous or unsafe.

## Product contract

- User text never leaves the device.
- A network connection is allowed only to download model assets explicitly.
- Normal mode returns suggestions and keeps the original text unchanged.
- Autocorrect is opt-in and applies only candidates above a confidence threshold.
- All edit offsets are zero-based Unicode code-point offsets into the original text.
- The engine considers a whole sentence. It does not pretend truncated fragments
  have complete context.
- Model or tokenizer failure is explicit. The engine does not silently return a
  result that looks verified.

## Baseline selection

Use `ufal/transformer-base-geccc-mate` as the first runtime model.

| Model | Parameters | GECCC F0.5 | Runtime decision |
| --- | ---: | ---: | --- |
| UFAL Transformer base | 60.8M | 73.73 | Default |
| UFAL ByT5 small | 300M | 72.56 | Rejected: larger and worse |
| UFAL ByT5 base | 582M | 75.15 | Too large for default device runtime |
| UFAL ByT5 large | 1.275B | 77.01 | Evaluation/teacher candidate only |

Source: <https://huggingface.co/ufal/transformer-base-geccc-mate>

The model is a sentence-to-sentence Czech GEC Transformer trained with synthetic
Czech errors and GECCC. It handles the contextual classes the product needs more
directly than a hand-written rule list or an n-gram spell checker.

The Hugging Face metadata currently names `BartTokenizer`, but the shipped
`tokenizer.json` is WordPiece. `AutoTokenizer` under Transformers 5.15 loaded the
wrong byte-level backend in a live probe. CzechCore must load the artifact with
`PreTrainedTokenizerFast` and verify the backend model is WordPiece before any
inference.

## Licenses

- CzechCore source: MIT.
- `ufal/transformer-base-geccc-mate`: CC BY-NC-SA 4.0.
- Czech UDPipe model: CC BY-NC-SA 4.0.
- `ufal.udpipe` bindings: MPL 2.0.

Restricted assets are downloaded into the user cache and are not committed into
the source repository. Documentation must state that the default model stack is
for non-commercial use. Commercial distribution requires separately licensed or
replacement model data.

## Architecture

```text
original text
    -> UDPipe sentence/token ranges
    -> protected-span detection
    -> WordPiece + Transformer beam generation
    -> candidate scoring including the unchanged sentence
    -> safety policy and abstention
    -> Unicode edit alignment
    -> suggestion result / optional applied result
```

### Public types

```python
class CorrectionKind(StrEnum):
    SPELLING = "spelling"
    DIACRITICS = "diacritics"
    PUNCTUATION = "punctuation"
    CAPITALIZATION = "capitalization"
    WHITESPACE = "whitespace"
    GRAMMAR = "grammar"


@dataclass(frozen=True, slots=True)
class TextEdit:
    start: int
    end: int
    source: str
    replacement: str
    kind: CorrectionKind
    confidence: float
    applied: bool


@dataclass(frozen=True, slots=True)
class CorrectionResult:
    original_text: str
    suggested_text: str
    output_text: str
    edits: tuple[TextEdit, ...]
    warnings: tuple[str, ...]
```

`CzechCore.correct(text, autocorrect=False, min_confidence=0.995)` is the single
entry point. Empty text returns an empty result. Invalid confidence values raise
`ValueError`.

### Sentence and token boundaries

Use the exact Czech UDPipe 1 tokenizer requested by the selected model. Token
ranges come from `TOKENIZER_RANGES`; they preserve offsets in the original text.
Each sentence is corrected independently. Original whitespace between sentences
is preserved.

The Transformer has 256 positions including special tokens. A sentence whose
encoded form exceeds that limit is returned unchanged with `sentence_too_long`.
Silent truncation is forbidden.

### Protected spans

Detect mechanical formats only: URLs, email addresses, Windows paths, semantic
versions, and code-like tokens containing `++`, `#`, or mixed lower/upper case.
Regex is allowed here because this is format recognition, not semantic intent.

A candidate is rejected if any protected literal from its source sentence is not
present unchanged in the candidate. This chooses a missed suggestion over damage
to user data.

### Candidate confidence

Generate four unique beam candidates. Score each candidate and the unchanged
tokenized sentence by normalized conditional log likelihood. Convert the unique
candidate scores to a relative posterior with softmax. The top candidate's value
is exposed as model confidence; it is not described as empirical correctness.

The unchanged sentence is always a candidate. A correction must beat it.

### Safety policy

Reject a candidate when any condition holds:

- protected content changed;
- encoded sentence is too long;
- replacement is empty for a non-empty sentence;
- changed-character ratio exceeds `0.35`;
- candidate confidence is below the suggestion threshold;
- autocorrect is requested and confidence is below `min_confidence`.

Suggestion mode may return edits without applying them. Autocorrect applies all
edits from one accepted sentence atomically; it never applies half a neural
rewrite.

### Edit extraction

Use `difflib.SequenceMatcher(autojunk=False)` over original and corrected Unicode
strings. Convert non-equal opcodes to non-overlapping `TextEdit` values. Apply
edits from right to left and assert the reconstructed result equals the candidate.

Kinds are mechanical:

- only whitespace changed -> `whitespace`;
- only Unicode punctuation changed -> `punctuation`;
- removing diacritics makes source/replacement equal -> `diacritics`;
- lowercase forms match -> `capitalization`;
- otherwise -> `grammar` for real-word changes, `spelling` only when the backend
  later supplies lexical evidence.

No keyword-based semantic classification is added.

## CLI

`czechcore download` downloads and hash-verifies tokenizer/model assets.

`czechcore check TEXT` prints the suggested corrected text.

`czechcore check --json TEXT` prints the complete structured result once as JSON.

`czechcore check --autocorrect --min-confidence 0.995 TEXT` applies only accepted
high-confidence sentence corrections.

## Evaluation

Unit tests cover offset-safe edits, classifications, protections, thresholds,
empty input, invalid settings, and atomic application.

A marked integration test runs the real UFAL model against at least:

- incorrect and correct subject-predicate agreement;
- context-sensitive `Bili psa.` / `Byli doma.`;
- missing subordinate-clause commas;
- missing diacritics;
- a spelling error;
- protected email/version/code text.

The repository includes a JSONL benchmark runner for source/reference pairs. It
reports exact sentence accuracy, changed-correct-sentence rate, correction rate,
latency, and accepted autocorrect count. Full GECCC/ERRANT scoring stays external
until the licensed corpus is configured.

## Deferred deliberately

- Android `SpellCheckerService` and Windows Spell Checking API adapters.
- ONNX/INT8 export and mobile decoder orchestration.
- Fine-tuning or distillation from ByT5-large.
- Hand-written Czech rule DSL.
- Personalized dictionaries.

These are justified only after baseline errors and device measurements identify
a real gap. The structured API and backend boundary keep those additions possible.
