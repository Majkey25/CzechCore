# Changelog

All notable changes are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-08-18

### Added

- Offline Czech sentence correction using the pinned
  `ufal/transformer-base-geccc-mate` model.
- Exact UDPipe sentence/token ranges and Unicode `TextEdit` output.
- Suggestion-first operation plus opt-in confidence-gated autocorrect.
- Safety rejection for large rewrites and changed URLs, email addresses, paths,
  versions, and code-like tokens.
- Exact adjacent repeated-word correction with conservative confidence.
- CLI commands for asset download, text checking, JSON output, benchmarking, and
  package version reporting.
- A 35-sentence Czech acceptance benchmark and real-model integration tests.
- Strict Ruff, formatting, Pyright, pytest, coverage, and GitHub Actions gates.
- Scientific, API, architecture, evaluation, contribution, security, citation,
  and release documentation.

### Fixed

- Explicitly loads the model's shipped WordPiece tokenizer. Current Transformers
  otherwise interprets its legacy `BartTokenizer` metadata as byte-level BPE and
  corrupts Czech output.
- Reuses a valid hash-verified UDPipe cache instead of downloading 56 MB again.
- Defers importing PyTorch/Transformers until correction starts, so `--version`
  and asset-management startup do not load the ML runtime.

### Known limitations

- The compact model leaves `Petr a Jana šla domů.` unchanged in the current
  acceptance set.
- Confidence is relative beam confidence, not calibrated probability of
  correctness.
- The default model assets are CC BY-NC-SA 4.0 and are not commercially licensed.
- Android, Windows, ONNX/INT8, paragraph context, and personalization are not part
  of `v0.1.0`.

[Unreleased]: https://github.com/Majkey25/CzechCore/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Majkey25/CzechCore/releases/tag/v0.1.0
