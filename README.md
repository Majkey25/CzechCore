# CzechCore

[![CI](https://github.com/Majkey25/CzechCore/actions/workflows/ci.yml/badge.svg)](https://github.com/Majkey25/CzechCore/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/Majkey25/CzechCore?display_name=tag&sort=semver)](https://github.com/Majkey25/CzechCore/releases/latest)
[![Python 3.12–3.14](https://img.shields.io/badge/Python-3.12--3.14-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/Code-MIT-yellow.svg)](https://github.com/Majkey25/CzechCore/blob/main/LICENSE)
[![Model license](https://img.shields.io/badge/Model-CC_BY--NC--SA_4.0-orange)](https://github.com/Majkey25/CzechCore/blob/main/NOTICE.md)
[![Inference: offline](https://img.shields.io/badge/Inference-offline-2E7D32)](#safety-and-limits)

Offline, context-aware Czech grammar correction. CzechCore returns exact text
edits for underlines and keeps automatic application behind an explicit
confidence threshold.

**Status:** `v0.1.0` alpha. The engine and CLI work; Windows and Android system
adapters are deliberately not part of this release.

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

## Documentation

| Document | Purpose |
| --- | --- |
| [Documentation index](https://github.com/Majkey25/CzechCore/blob/main/docs/README.md) | Source of truth and update policy |
| [Scientific basis](https://github.com/Majkey25/CzechCore/blob/main/docs/SCIENTIFIC_BASIS.md) | Czech phenomena, model, formulas, citations |
| [Evaluation](https://github.com/Majkey25/CzechCore/blob/main/docs/EVALUATION.md) | Metrics, reproducibility, measured baseline |
| [API](https://github.com/Majkey25/CzechCore/blob/main/docs/API.md) | Python and CLI contracts, offsets, warnings |
| [Architecture](https://github.com/Majkey25/CzechCore/blob/main/docs/ARCHITECTURE.md) | Components, data flow, assets, trust boundaries |
| [Development](https://github.com/Majkey25/CzechCore/blob/main/docs/DEVELOPMENT.md) | Setup, quality gates, release process |
| [Roadmap](https://github.com/Majkey25/CzechCore/blob/main/docs/ROADMAP.md) | Evidence-gated next work |
| [Decisions](https://github.com/Majkey25/CzechCore/blob/main/docs/decisions/README.md) | Accepted architectural decisions |

## Install

Python 3.12–3.14 is supported. Python 3.12 is the release baseline.

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

### Release wheel

```powershell
python -m pip install https://github.com/Majkey25/CzechCore/releases/download/v0.1.0/czechcore-0.1.0-py3-none-any.whl
czechcore download
```

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
- about 212 ms per sentence after model load.

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

Contributions must keep the benchmark honest and the offline boundary intact.
See [CONTRIBUTING.md](https://github.com/Majkey25/CzechCore/blob/main/CONTRIBUTING.md)
and [SECURITY.md](https://github.com/Majkey25/CzechCore/blob/main/SECURITY.md).

## Licenses

CzechCore source code is MIT licensed. The default UFAL neural and UDPipe model
assets are CC BY-NC-SA 4.0 and therefore non-commercial. They are downloaded at
runtime and are not part of this repository. See
[NOTICE.md](https://github.com/Majkey25/CzechCore/blob/main/NOTICE.md).

Research basis: Petr Pechman, Milan Straka, Jana Straková, and Jakub Náplava,
*Refining Czech GEC: Insights from a Multi-Experiment Approach* (TSD 2025/2026),
<https://doi.org/10.1007/978-3-032-02551-7_7>.

For software citation metadata, see
[CITATION.cff](https://github.com/Majkey25/CzechCore/blob/main/CITATION.cff).
Release history is maintained in
[CHANGELOG.md](https://github.com/Majkey25/CzechCore/blob/main/CHANGELOG.md).
