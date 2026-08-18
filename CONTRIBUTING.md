# Contributing

CzechCore accepts focused changes that preserve offline inference, explicit
failure handling, exact source offsets, and honest evaluation.

## Setup

```powershell
git clone https://github.com/Majkey25/CzechCore.git
cd CzechCore
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\czechcore download
```

## Workflow

1. Create `feat/<change>/DD-MM-YYYY` or `fix/<change>/DD-MM-YYYY`.
2. Write a failing test for behavior changes.
3. Implement the smallest root-cause change.
4. Run the relevant live model scenario when inference changes.
5. Update documentation and `CHANGELOG.md` when users can observe the change.
6. Open a focused pull request with commands and results.

Do not commit model files, corpora, caches, `.venv`, or generated wheels.

## Required checks

```powershell
.venv\Scripts\python -m pytest
.venv\Scripts\python -m ruff check . --no-cache
.venv\Scripts\python -m ruff format --check .
.venv\Scripts\python -m pyright --pythonpath .venv\Scripts\python.exe
.venv\Scripts\python -m pip check
.venv\Scripts\python -m tools.research.validate_sources --schema-only
.venv\Scripts\python -m tools.research.validate_taxonomy
```

Run `czechcore-benchmark benchmarks\cases.jsonl` for changes that can alter model
selection, tokenization, confidence, edit extraction, or safety policy.

## Benchmark cases

Each JSONL line has three required string fields:

```json
{"source":"Ženy šli domů.","reference":"Ženy šly domů.","category":"subject_predicate_agreement"}
```

- Add both positive and negative examples for a changed linguistic phenomenon.
- Do not delete a failing case to improve the score.
- Do not hardcode a reference sentence in production code.
- Keep new examples short enough that reviewers can verify them against an
  authoritative Czech source.
- Record corpus-derived examples only when their license permits redistribution.

## Code requirements

- Python 3.12 typing must pass strict Pyright.
- Ruff and repository formatting are mandatory.
- Blocking model inference remains synchronous; do not place it directly inside
  an asynchronous server route.
- External assets must be version-pinned and integrity-checked where the provider
  exposes stable hashes.
- Semantic corrections belong in the model/training/evaluation path, not regex
  keyword rules. Regex is limited to mechanical formats and protections.

## Documentation policy

Use the evidence labels defined in [docs/README.md](docs/README.md). Published,
measured, and planned claims must never be mixed. Significant decisions need an
ADR under `docs/decisions/`.
