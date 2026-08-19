# Research documentation

This directory contains CzechCore's maintained scientific syntheses. Downloaded
papers, HTML snapshots, repositories, and datasets live in
`.reference/research/` and are intentionally not committed.

> [!NOTE]
> Start with the consolidated [research and engineering
> report](../RESEARCH_REPORT.md). This index exposes the underlying methods and
> machine-readable evidence behind that report.

## Evidence snapshot

| Surface | Current evidence |
| --- | ---: |
| Normative IJP structure | 22 chapters / 202 explanations |
| Czech correction taxonomy | 13 families / 101 phenomena |
| GECCC aggregate | 83,058 sentences / 228,805 edits / 65 types |
| GECCC development evaluation | 8,478 sentences |
| Focused proofread acceptance | 65 cases |
| Semantic rewrite acceptance | 12 cases |
| Source provenance | 40 records |

## Current program

- [Research program](PROGRAM.md)
- [Committed source manifest](../../research/sources.json)
- [Manifest usage and local-cache verification](../../research/README.md)
- [Machine-readable IJP outline](../../research/ijc-outline.json)
- [Machine-readable Czech correction taxonomy](../../research/taxonomy.json)
- [Machine-readable coverage matrix](../../research/coverage.json)
- [Benchmark-to-phenomenon mapping](../../research/benchmark-mapping.json)
- [GECCC error-type statistics](../../research/geccc-error-types.json)
- [GECCC development evaluation record](../../research/evaluations/geccc-dev-2026-08-18.json)
- [Local rewrite model screen](../../research/evaluations/rewrite-model-screen-2026-08-18.json)
- [Morphology ranker screen](../../research/evaluations/ranker-screen-2026-08-18.json)
- [Portable runtime and Android arm64 build screen](../../research/evaluations/portable-runtime-screen-2026-08-18.json)
- [Semantic rewrite acceptance cases](../../benchmarks/rewrite_cases.jsonl)

## Maintained syntheses

- [Czech grammar and correction taxonomy](CZECH_GRAMMAR_TAXONOMY.md)
- [Czech GEC literature synthesis](CZECH_GEC_LITERATURE.md)
- [Corpora, models, and licenses](CORPORA_AND_LICENSES.md)
- [Model architecture research](MODEL_ARCHITECTURES.md)
- [Training and synthetic errors](TRAINING_AND_SYNTHETIC_ERRORS.md)
- [Confidence, calibration, and abstention](CONFIDENCE_AND_ABSTENTION.md)
- [Full evaluation protocol](EVALUATION_PROTOCOL.md)
- [Full GECCC development baseline](GECCC_BASELINE.md)
- [Portable runtime research](PORTABLE_RUNTIME_RESEARCH.md)
- [Live typing adapter evidence](../../research/evaluations/live-typing-adapters-2026-08-19.json)
- [Hybrid local semantic rewrite architecture](HYBRID_SEMANTIC_REWRITE.md)
- [MorphoDiTa candidate-reranking research](MORPHOLOGY_RERANKING.md)
- [Research gaps and prioritized experiments](RESEARCH_GAPS.md)

Each document must follow the evidence labels in `docs/README.md` and link its
claims to `research/sources.json` identifiers.
