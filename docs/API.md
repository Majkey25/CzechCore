# API reference

## Stability

The `0.1.x` API is alpha. Public names are exported from `czechcore`; backend,
asset, and tokenizer modules are implementation details unless stated otherwise.

## Install and assets

```powershell
python -m pip install czechcore-0.1.0-py3-none-any.whl
czechcore download
```

The wheel contains code only. `download` installs the pinned model assets into
local caches. Inference does not download missing assets automatically.

## Python API

```python
from czechcore import CzechCore

engine = CzechCore()
result = engine.correct("Když přišel domů šel spát.")
print(result.suggested_text)
```

### `CzechCore.correct`

```python
def correct(
    text: str,
    *,
    autocorrect: bool = False,
    min_confidence: float = 0.995,
) -> CorrectionResult
```

| Parameter | Contract |
| --- | --- |
| `text` | Original Unicode text. It is never uploaded. |
| `autocorrect` | If false, `output_text` remains original. If true, accepted sentences can be applied. |
| `min_confidence` | Inclusive `[0, 1]` threshold for application. Invalid values raise `ValueError`. |

Empty text returns an empty result without invoking the model.

### `CorrectionResult`

| Field | Type | Meaning |
| --- | --- | --- |
| `original_text` | `str` | Exact input |
| `suggested_text` | `str` | Input with all accepted suggestions applied |
| `output_text` | `str` | Input with only autocorrect-approved edits applied |
| `edits` | `tuple[TextEdit, ...]` | Ordered, non-overlapping source edits |
| `warnings` | `tuple[str, ...]` | Machine-readable abstention reasons |

### `TextEdit`

| Field | Type | Meaning |
| --- | --- | --- |
| `start`, `end` | `int` | Half-open Unicode code-point range `[start, end)` |
| `source` | `str` | Must equal `original_text[start:end]` |
| `replacement` | `str` | Suggested replacement; insertion uses `start == end` |
| `kind` | `CorrectionKind` | Mechanical edit category |
| `confidence` | `float` | Relative beam confidence, not calibrated accuracy |
| `applied` | `bool` | Whether this edit contributes to `output_text` |

Apply multiple edits from right to left. Library users can use
`czechcore.core.apply_edits` when they intentionally depend on the internal
helper, but it is not part of the stable public surface in `0.1.x`.

### `CorrectionKind`

- `diacritics`
- `punctuation`
- `capitalization`
- `whitespace`
- `grammar`
- `spelling` — reserved for future lexical evidence

### Warnings

Warnings use `name:start:end` where offsets refer to the original full text:

| Name | Meaning |
| --- | --- |
| `sentence_too_long` | Encoded sentence exceeds the 256-position model limit |
| `low_confidence` | Top candidate did not reach the suggestion floor |
| `unsafe_candidate` | Candidate changed protected content or exceeded the rewrite ratio |

Warnings cause the affected sentence to remain unchanged.

### Offset interoperability

Python offsets count Unicode code points. Windows and Android text APIs commonly
use UTF-16 code units. Platform adapters must convert offsets explicitly; direct
reuse is incorrect for characters outside the Basic Multilingual Plane, including
many emoji.

### Concurrency

`CzechCore` is designed for synchronous inference. `0.1.x` makes no shared-instance
thread-safety guarantee. Use one engine per worker or serialize access. Do not call
the blocking model directly from an asynchronous event loop.

## CLI

### Version

```text
czechcore --version
```

### Download assets

```text
czechcore download
```

Existing valid UDPipe files are hash-checked and reused.

### Suggestion mode

```text
czechcore check "Muži přišly domů."
czechcore check --json "Když přišel domů šel spát."
```

### Autocorrect mode

```text
czechcore check --autocorrect --min-confidence 0.60 "Muži přišly domů."
```

The lower `0.60` value is an explicit caller choice, not the release default.

### Benchmark

```text
czechcore-benchmark benchmarks/cases.jsonl
```

The command emits one JSON object with sentence-exact counts and elapsed time.

## Exit behavior

- `0`: completed command;
- `2`: argparse usage error or missing model assets;
- unexpected model/tokenizer/runtime failure: non-zero process failure with the
  original exception preserved for diagnosis.
