# Development and release

## Environment

Python 3.12 is the release baseline.

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\czechcore download
```

The asset command is explicit because runtime inference must remain offline.

MorphoDiTa ranker experiments additionally use the optional research extra:

```powershell
.venv\Scripts\python -m pip install -e ".[dev,research]"
```

The core engine and CI import path do not require this optional binding.

## Quality gates

```powershell
.venv\Scripts\python -m pytest
.venv\Scripts\python -m ruff check . --no-cache
.venv\Scripts\python -m ruff format --check .
.venv\Scripts\python -m pyright --pythonpath .venv\Scripts\python.exe
.venv\Scripts\python -m pip check
```

Build:

```powershell
.venv\Scripts\python -m pip wheel . --no-deps --wheel-dir .reference\tmp\dist
```

GitHub CI intentionally excludes `model` tests because they require large
non-commercial assets. A release cannot rely on CI alone: all real-model tests
must pass locally before tagging.

## Test layers

| Layer | Purpose |
| --- | --- |
| Core unit tests | Edit invariants, protection, classification, thresholds |
| Dependency-injected engine tests | Orchestration without model cost |
| Real model tests | Correct tokenizer backend and contextual outputs |
| Live CLI scenarios | User-visible suggestion/autocorrect/JSON behavior |
| Acceptance benchmark | Small linguistic regression score and false-positive guards |

For behavior changes, follow RED -> GREEN -> refactor. A model correction bug needs
a failing realistic case before production logic changes.

## Documentation maintenance

- Public behavior: update `API.md` and README.
- Model/scoring/safety: update `SCIENTIFIC_BASIS.md`, `ARCHITECTURE.md`, ADR, and
  benchmark evidence.
- Benchmark changes: rerun and replace measured values in `EVALUATION.md`.
- User-visible change: add `CHANGELOG.md` entry.
- Release: update package version, `CITATION.cff`, changelog date, tag, and notes.

Do not copy generated benchmark output without its command, environment, date, and
dataset revision.

## Release checklist

1. Confirm the worktree is clean and `main` matches `origin/main`.
2. Confirm package version, changelog version, citation version, and intended tag
   are identical.
3. Run all local quality gates, including model tests and `pip check`.
4. Run live suggestion, autocorrect, correct-negative, protected-text,
   multi-sentence, long-sentence, and repeated-word scenarios.
5. Run `czechcore-benchmark benchmarks/cases.jsonl`; update measured docs if the
   output changed.
6. Build the wheel and install it into an isolated target or environment.
7. Inspect wheel contents; model assets and caches must be absent.
8. Commit and push; wait for GitHub Actions success on the exact release commit.
9. Create annotated tag `vMAJOR.MINOR.PATCH` on that commit and push it.
10. Create the GitHub release with curated notes and the wheel artifact.
11. Verify public release, asset download, tag/commit identity, and wheel SHA-256.

## Versioning

CzechCore follows SemVer from `0.1.0` onward:

- patch: compatible bug/documentation fix;
- minor: backward-compatible public behavior;
- major: breaking API or correction-policy contract.

During alpha, every observable behavior still requires a changelog entry even
when SemVer permits change under `0.x`.
