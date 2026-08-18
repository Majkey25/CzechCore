# CzechCore

Offline, context-aware Czech grammar correction. CzechCore returns exact text
edits for underlines and keeps automatic application behind an explicit
confidence threshold.

```text
Když přišel domů šel spát.
                    ↓
Když přišel domů, šel spát.
```

## What works

- full-sentence Czech neural correction;
- spelling, diacritics, punctuation, agreement, and contextual grammar;
- exact Unicode source ranges and structured edits;
- suggestions without changing the source by default;
- opt-in confidence-gated autocorrect;
- protected URLs, email addresses, paths, versions, and code-like tokens;
- fully local inference after one explicit asset download;
- CLI and JSON output ready for later Windows/Android adapters.

CzechCore uses the 60.8M-parameter
[`ufal/transformer-base-geccc-mate`](https://huggingface.co/ufal/transformer-base-geccc-mate)
model. Its published GECCC F0.5 is 73.73. It is much smaller and slightly more
accurate than the published 300M ByT5-small baseline, which makes it the best
available starting point for a future device runtime.

## Install

Python 3.12 is required.

### Windows

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\czechcore download
```

### Linux/macOS

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/czechcore download
```

`download` fetches a pinned Transformer snapshot and a pinned UDPipe model. The
UDPipe file is accepted only when its SHA-256 matches the value in `assets.py`.
No user text is uploaded.

## Use

Suggestion mode leaves `output_text` unchanged:

```powershell
czechcore check "Muži přišly domů."
czechcore check --json "Když přišel domů šel spát."
```

Opt-in autocorrect applies a sentence only when the top candidate reaches the
chosen relative model confidence:

```powershell
czechcore check --autocorrect --min-confidence 0.60 "Muži přišly domů."
```

The default autocorrect threshold is intentionally conservative (`0.995`). The
confidence is relative to the returned beams and unchanged sentence. It is not a
claim of empirical 99.5% correctness.

Example JSON:

```json
{
  "original_text": "Když přišel domů šel spát.",
  "suggested_text": "Když přišel domů, šel spát.",
  "output_text": "Když přišel domů šel spát.",
  "edits": [
    {
      "start": 16,
      "end": 16,
      "source": "",
      "replacement": ",",
      "kind": "punctuation",
      "confidence": 0.37000428836961735,
      "applied": false
    }
  ],
  "warnings": []
}
```

Offsets index Python/Unicode code points in the exact original text.

## Measured baseline

Run:

```powershell
czechcore-benchmark benchmarks\cases.jsonl
```

Measured on 2026-08-18 with CPU inference:

- 35 focused Czech acceptance sentences;
- 34 exact outputs;
- 24/25 erroneous sentences corrected exactly;
- 0 wrong alternative rewrites;
- 0/10 already-correct sentences changed;
- about 215 ms per sentence after model load.

This small repository suite is regression evidence, not a corpus-wide accuracy
claim. The remaining known miss is `Petr a Jana šla domů.`; the compact model
does not currently change `šla` to `šli`. A regex patch would be unsafe. The next
accuracy step is measured fine-tuning or distillation, not hardcoded sentence
answers.

## Safety and limits

- No grammar checker is correct for every ambiguous sentence.
- CzechCore abstains on large rewrites, low-confidence candidates, changed
  protected literals, and sentences beyond the model's 256-token limit.
- A protected literal can make CzechCore leave the whole sentence unchanged.
- The neural model is sentence-based; it does not use preceding paragraphs.
- Android and Windows integration, ONNX/INT8 export, and personalization are not
  implemented yet. They follow after engine evaluation.

## Development

```powershell
python -m pytest -m "not model"
python -m pytest -m model
python -m ruff check .
python -m ruff format --check .
.venv\Scripts\python -m pyright --pythonpath .venv\Scripts\python.exe
```

The `model` tests require `czechcore download` first.

## Licenses

CzechCore source code is MIT licensed. The default UFAL neural and UDPipe model
assets are CC BY-NC-SA 4.0 and therefore non-commercial. They are downloaded at
runtime and are not part of this repository. See [NOTICE.md](NOTICE.md).

Research basis: Petr Pechman, Milan Straka, Jana Straková, and Jakub Náplava,
*Refining Czech GEC: Insights from a Multi-Experiment Approach* (TSD 2025/2026),
<https://doi.org/10.1007/978-3-032-02551-7_7>.
