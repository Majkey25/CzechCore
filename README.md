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
- measured support for spelling, diacritics, punctuation, agreement, and
  contextual grammar, with substantial known syntax/false-positive gaps;
- exact Unicode source ranges and structured edits;
- suggestions without changing the source by default;
- opt-in confidence-gated autocorrect;
- protected URLs, email addresses, paths, versions, and code-like tokens;
- fully local inference after one explicit asset download;
- CLI and JSON output ready for later Windows/Android adapters.
- experimental local hybrid rewrite API/CLI with explicit review and invariant
  fallback; no rewrite model is accepted as default yet.

CzechCore uses the 60.8M-parameter
[`ufal/transformer-base-geccc-mate`](https://huggingface.co/ufal/transformer-base-geccc-mate)
model. Its published model-card GECCC F0.5 is 73.73; CzechCore's reproduced
post-safety development score is lower and reported separately below. The model
is much smaller than the published ByT5 alternatives, making it a useful compact
baseline, not a finished device engine.

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
| [Research program](https://github.com/Majkey25/CzechCore/blob/main/docs/research/README.md) | 202 IJP rules, 65 GECCC types, 101 phenomena, literature/training/eval |
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

- 65 focused Czech acceptance sentences;
- 60 exact outputs;
- 34/38 erroneous sentences corrected exactly;
- 0 wrong alternative rewrites;
- 1/27 already-correct sentences changed;
- about 77 ms per sentence with fixed batch-16 warm CPU inference after model load.

This small repository suite is regression evidence, not a corpus-wide accuracy
claim. The full 8,478-sentence GECCC development run currently reaches M2
precision `0.7884`, recall `0.3551`, and F0.5 `0.6337` after the current safety
replay, while still changing 558/3,288 already-correct source sentences. It
therefore fails the release gate. See the
[full baseline](https://github.com/Majkey25/CzechCore/blob/main/docs/research/GECCC_BASELINE.md).

## Safety and limits

- No grammar checker is correct for every ambiguous sentence.
- CzechCore abstains on large rewrites, low-confidence candidates, changed
  protected literals, and sentences beyond the model's 256-token limit.
- A protected literal can make CzechCore leave the whole sentence unchanged.
- The neural model is sentence-based; it does not use preceding paragraphs.
- Meaning-preserving whole-sentence rewrite is specified and benchmarked but not
  yet part of the public API; the first 0.6B mobile LLM candidate was rejected.
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
