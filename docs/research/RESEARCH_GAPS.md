# Research gaps and prioritized experiments

## Current verified strengths

- Offline full-sentence neural correction works.
- Exact source edits and punctuation insertions are preserved.
- The small acceptance set corrects 24/25 erroneous sentences exactly and changes
  none of its 10 correct sentences.
- Real model tests cover contextual agreement, comma insertion, and homograph
  preservation.
- Protected technical literals, rewrite ratio, and over-length abstention work.
- Research provenance now covers 40 primary sources/artifacts, 202 official IJP explanations,
  65 GECCC error types, and 101 taxonomy phenomena.

These are engineering/research foundations, not complete Czech coverage.

## Critical quality gaps

### No standard CzechCore GECCC score

Published model-card F0.5 cannot substitute for evaluating CzechCore's tokenizer,
safety policy, candidate scoring, and abstentions. Implement full inference and
Czech ERRANT scoring on frozen GECCC dev/test.

### Coordinated-subject agreement

Current explicit miss:

```text
Petr a Jana šla domů. -> Petr a Jana šli domů.
```

Research paths:

- MATE generator coverage for coordinated subjects;
- MorphoDiTa/UDPipe subject features;
- ByT5 teacher behavior;
- candidate-generation versus ranking diagnosis;
- fine-tuning and per-family evaluation.

Do not add name-specific or shallow regex correction.

### Confidence is not calibrated

Current confidence is beam-relative. Build frozen prediction datasets, edit-level
labels, reliability/precision-coverage reports, and a bounded calibrator before
changing default autocorrect.

### Error explanations are coarse

Runtime categories are mechanical and most semantic replacements become
`grammar`. Add Czech ERRANT/taxonomy mapping and morphology evidence without
claiming rule causality the model did not establish.

### Sentence-only context

Paragraph context can resolve references, ellipsis, capitalization, discourse
particles, and cross-sentence consistency. It also raises model-length and
semantic rewrite risks. Evaluate before expanding input context.

## Data gaps

- Training source acquisition/license/dedup manifests are not built yet.
- Native correct/low-error-density Czech needs a large dedicated false-positive
  suite.
- Technical, legal, medical, conversational, and code-mixed domains need separate
  evaluation.
- Proper names, foreign words, abbreviations, dates, and typography need broader
  protected/normalization tests.
- Human semantic-preservation judgments are absent.

## Model gaps

- Released ByT5 teacher profiles are not locally benchmarked yet.
- No morphology-informed reranking experiment exists.
- No Czech edit-tagger/distilled student exists.
- No portable/quantized parity experiment exists.
- No calibrated per-edit confidence exists.

## Evaluation gaps

- No Czech ERRANT end-to-end scorer integration in CzechCore.
- No multiple-reference handling report.
- No bootstrap confidence intervals/significance tests.
- No domain/error-family model comparison report.
- No cold-start/peak-memory measurement in the benchmark command.
- Android has one x86_64 source-debug emulator PSS/RSS measurement; no physical
  arm64 or Windows system-adapter device benchmark exists.

## Priority experiment queue

1. Implement GECCC prediction adapter and Czech ERRANT evaluation.
2. Run current baseline by domain/error type; publish failure inventory.
3. Benchmark ByT5-base/large on a fixed representative subset and coordinated
   agreement targets.
4. Add MorphoDiTa candidate analysis/generation prototype.
5. Build expanded correct-text/adversarial suite from licensed/constructed data.
6. Reproduce updated MATE training with exact manifests.
7. Fine-tune compact baseline and compare against teacher/distilled candidates.
8. Calibrate selective policy.
9. Export/quantize the winning compact runtime.
10. Begin Windows/Android adapters only after parity/device gates.

## Definition of progress

A gap closes only with:

- code/data/config revision;
- test or evaluation record;
- quantitative before/after;
- no safety/false-positive regression;
- license review;
- updated coverage matrix and documentation.
