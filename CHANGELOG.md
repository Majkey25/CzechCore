# Changelog

All notable changes are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.1] - 2026-10-22

### Security

- Bypass environment and system proxies for loopback rewrite requests while
  retaining redirect rejection.
- Bound inference to 16 sentences per batch and validate sentence length before
  allocating tensors. Process complete documents in successive batches; reject
  documents over 1,000,000 characters explicitly.
- Replace the shared Windows pipe name with a random endpoint published inside a
  private namespace restricted to the current user and logon session. Keep the
  pipe open between requests and verify the server image, user SID, and logon SID
  before either client sends text.

## [0.3.0] - 2026-08-19

### Added

- Device-specific Windows, macOS, Linux, and Android setup/status guides with a
  single installation entry point, release hash verification, model/cache
  lifecycle, live scenarios, updates, removal, and troubleshooting.
- Clean virtual-environment model-smoke workflow for the public wheel on hosted
  Windows x64, macOS arm64, and Ubuntu x64 runners.
- Measured CTranslate2 FP32/INT8 BART parity screen and successful Android
  arm64-v8a/API 26 native runtime build; INT8 remains rejected after a punctuation
  regression.
- Source-only Android debug APK probe with Java WordPiece, JNI FP32 inference,
  protected-literal fallback, JVM tests, and real Android 35 emulator flows.
- Android CzechCore IME with Czech QWERTZ/symbol layouts, cross-app candidates,
  `SuggestionSpan` underlines, confirmation, undo, sensitive-field exclusion,
  stale-result rejection, and bounded deterministic automatic repair.
- Native Windows C++20 CTranslate2 broker, current-user-only named pipe, x64/x86
  TSF display-attribute service, confirmation shortcuts, settings GUI, and
  UAC-aware source installer payload.
- CodeQL security-extended analysis for C/C++, Java, and Python.

### Security

- Bound Android model/vocabulary sizes, keep at most one pending inference, and
  hide native exception details from the UI.
- Reduce Windows IPC from 1 MiB to 16 KiB, add 5-second overlapped I/O timeouts,
  reject remote clients, verify the broker process image, and test rogue-pipe,
  stalled-client, oversized-request, and protected-literal cases.
- Restrict setup DLL dependency loading to the installed DLL directory and
  System32, then verify the copied payload before TSF registration.

### Performance

- Preload one mutex-protected Windows broker when TSF activates and release its
  306.82 MiB measured working set after 10 minutes idle.
- Measure 159.92 ms warm median and 170.96 ms warm p95 end-to-end Windows broker
  latency across ten local requests.

## [0.2.0] - 2026-08-18

### Added

- Versioned research program for full Czech grammar/GEC coverage.
- Provenance manifest for 39 primary papers, repositories, datasets, model cards,
  and the complete official IJP rule collection.
- Machine-readable outline of 22 IJP chapters/202 explanations, aggregate mapping
  of all 65 GECCC error types, and 13-family/101-phenomenon correction taxonomy.
- Typed source/taxonomy validators enforced in CI.
- Scientific syntheses for Czech grammar, GEC literature, corpora/licenses,
  architectures, synthetic training, confidence, evaluation, portable runtime,
  and measured research gaps.
- Machine-readable 101-phenomenon coverage matrix, 65-case proofread acceptance
  suite, and 12-case semantic rewrite/invariant suite.
- Full 8,478-sentence GECCC development baseline with M2Scorer, Czech ERRANT,
  multiple-reference, domain, runtime, and failure reporting.
- Batched model scoring/correction, configurable research safety thresholds, and
  detailed benchmark failures.
- Hybrid local GEC + LLM semantic rewrite architecture and pinned llama.cpp,
  Qwen, Qwen3.5, and Aya feasibility artifacts with explicit pass/fail evidence.
- Loopback-only `HybridRewriter` Python API and `czechcore rewrite` CLI with
  protected-literal masking, high-recall GEC context, conservative fallback,
  invariant checks, review-only output, and diagnostic post-check disagreement.
- Fixed batch-16 GECCC confidence/coverage curve proving that scalar beam
  confidence cannot support useful autocorrect.
- Reproducible document-grouped MorphoDiTa/logistic ranker experiment; the model
  artifact remains rejected because validation precision misses the 90% gate.
- Consolidated scientific research report separating implemented behavior,
  measured results, published evidence, failure analysis, and release readiness.
- Concrete Windows/Android live-text architecture with shared runtime contract,
  user modes, scheduling, privacy, performance targets, and acceptance gates.
- ADR for one portable runtime, thin platform adapters, a Windows engine broker,
  and native Android runtime consumption.

### Fixed

- Preserve UDPipe surface multiword tokens such as `kdybych` and their exact
  source ranges.
- Protect phone numbers, calendar dates, and Czech quotation boundaries from
  neural punctuation rewrites.
- Enforce token boundaries for protected literals and recheck invariants globally
  after all sentence edits, including when UDPipe splits inside a URL/version.
- Force UTF-8 for benchmark JSON on Windows.
- Replace the old script-oriented repository landing page with a product,
  architecture, evidence, reproducibility, and deployment overview.
- Clarify that beam-relative confidence is not correctness calibration and the
  current default threshold has zero measured GECCC development coverage.

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

[Unreleased]: https://github.com/Majkey25/CzechCore/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/Majkey25/CzechCore/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/Majkey25/CzechCore/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Majkey25/CzechCore/releases/tag/v0.1.0
