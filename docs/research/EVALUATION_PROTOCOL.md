# Full Czech GEC evaluation protocol

## Objective

Measure whether CzechCore improves erroneous Czech while leaving correct Czech
unchanged, preserving meaning/protected text, and meeting offline runtime budgets.

The 65-case acceptance suite remains a fast regression test. It is not the
standard evaluation described here.

## Frozen data

### GECCC

Use handle `11234/1-4861`, whose ZIP SHA-256 is recorded in
`research/sources.json`. Preserve released train/dev/test and four domains. Use
sentence M2 for standard edit metrics and input/gold/meta for exact/domain reports.

### AKCES-GEC

Use handle `11234/1-3057` as a separate learner-domain evaluation. Do not merge
its test data into GECCC selection or training.

### Additional suites

- CzechCore acceptance cases;
- large correct-text/low-error-density suite;
- protected technical text;
- proper names and foreign expressions;
- ambiguity/minimal-pair suite;
- long/Unicode/emoji/offset safety;
- paragraph/document context once supported.

Every suite needs a manifest, license, hash, and frozen version.

## Inference protocol

Record:

- code commit and clean status;
- model/tokenizer/calibrator revisions and hashes;
- dependency/hardware versions;
- beam/search parameters;
- batch size and exact sentence grouping;
- confidence and safety thresholds;
- input preprocessing/detokenization;
- random/deterministic settings;
- failed/abstained records.

Run inference once per frozen system. Do not retune from test output.

## Edit metrics

Use Czech ERRANT/M2-compatible scoring to obtain true positives (`TP`), false
positives (`FP`), and false negatives (`FN`):

```text
precision = TP / (TP + FP)
recall = TP / (TP + FN)
F_beta = (1 + beta^2) * precision * recall /
         (beta^2 * precision + recall)
```

Primary GEC metric: `F0.5`, weighting precision twice as strongly as recall.

## Reproducible local commands

The corpus and scorer assets stay under the ignored `.reference/research/`
cache. Their revisions and hashes are pinned in `research/sources.json`.

Generate post-safety CzechCore predictions and an aligned source copy:

```powershell
.venv\Scripts\python -m tools.research.predict_corpus `
  .reference\research\datasets\geccc-4861\data\dev\sentence.input `
  .reference\research\evaluation\geccc-dev.prediction.txt `
  --source-copy .reference\research\evaluation\geccc-dev.source.txt `
  --diagnostics .reference\research\evaluation\geccc-dev.diagnostics.jsonl `
  --batch-size 16
```

Produce deterministic multi-reference/domain sentence metrics:

```powershell
.venv\Scripts\python -m tools.research.evaluate_corpus `
  .reference\research\datasets\geccc-4861\data\dev\sentence.input `
  .reference\research\datasets\geccc-4861\data\dev\sentence.gold `
  .reference\research\evaluation\geccc-dev.prediction.txt `
  .reference\research\datasets\geccc-4861\data\meta.tsv `
  .reference\research\datasets\geccc-4861\data\dev\sentence.meta `
  --output .reference\research\evaluation\geccc-dev.sentence-metrics.json
```

For the exact MATE M2Scorer protocol, first UDPipe-tokenize predictions, then
run the pinned `petrpechman/m2scorer@heuristic-lower-bound` revision:

```powershell
.venv\Scripts\python -m tools.research.tokenize_corpus `
  .reference\research\evaluation\geccc-dev.prediction.txt `
  .reference\research\evaluation\geccc-dev.prediction.tokenized.txt

.reference\research\errant-venv\Scripts\m2scorer `
  .reference\research\evaluation\geccc-dev.prediction.tokenized.txt `
  .reference\research\datasets\geccc-4861\data\dev\sentence.m2
```

For Czech ERRANT span/type analysis, use the pinned `ufal/errant_czech`
revision in UTF-8 mode, generate hypothesis M2 from the aligned source and
prediction files, then run `errant_compare -b 0.5 -cat 2`. M2Scorer and ERRANT
results are reported separately; their alignments are not numerically
interchangeable.

Report:

- overall edit precision/recall/F0.5;
- detection and correction separately where possible;
- per-operation `R/M/U`;
- all 65 Czech ERRANT types;
- taxonomy-family aggregation;
- macro and micro domain results;
- abstention-aware precision and coverage.

## Sentence metrics

- exact sentence accuracy against all references;
- erroneous sentence corrected exactly;
- erroneous sentence unchanged;
- wrong alternative rewrite;
- correct sentence changed (false-change rate);
- mean/median/p95 edits per changed sentence;
- broad rewrite and protected-text rejection rates.

Multiple references must be respected. Exact match alone can undercount valid
alternatives.

## Semantic preservation

Automatic reference metrics do not fully detect meaning changes. Sample and
human-review:

- high-confidence autocorrections;
- wrong rewrites;
- low-error-density native text;
- lexical substitutions and deletions;
- word-order changes;
- proper-name/technical sentences;
- candidate/reference disagreement with fluent output.

Use blinded paired review with at least grammaticality, meaning preservation, and
necessity labels. Record disagreement and adjudication.

## Confidence evaluation

- reliability diagram;
- expected calibration error;
- Brier/log loss for defined correctness labels;
- precision-coverage curves;
- autocorrect precision and coverage at frozen thresholds;
- breakdown by domain, family, sentence length, and edit count.

Calibration uses development data only.

## Runtime metrics

Measure cold and warm separately:

- asset/model load time;
- first correction latency;
- mean/median/p95 sentence latency;
- throughput;
- peak resident memory;
- model/tokenizer/calibrator disk size;
- CPU threads and GPU/accelerator use;
- energy/battery where device tooling permits.

Profiles:

- reference Windows CPU;
- low/mid/high Windows systems;
- representative Android arm64 devices;
- optional desktop GPU quality profile.

## Statistical reporting

- bootstrap confidence intervals for aggregate metrics;
- exact/appropriate intervals for autocorrect precision when accepted edits are
  rare;
- paired significance/bootstrap for model comparisons;
- no claim from differences smaller than uncertainty;
- publish raw counts with rates.

## Error analysis loop

For each false positive/negative/wrong rewrite:

1. map Czech ERRANT type and taxonomy family;
2. inspect source/reference/model candidates/scores;
3. distinguish missing candidate, ranking, calibration, tokenization, protection,
   morphology, syntax, domain, or reference ambiguity;
4. link to data/training/runtime issue;
5. add a licensed minimal regression example when possible;
6. fix the root system layer, not the sentence.

## Release acceptance gates

A model/runtime release must publish:

- frozen source/model manifests;
- complete commands/config;
- standard and safety results;
- comparison against the previous release;
- known regressions and failures;
- license review;
- artifact hashes;
- local and CI checks.

The default model changes only when it improves the approved quality/safety/runtime
Pareto criteria. A higher F0.5 alone is insufficient if false changes, memory, or
licensing regress materially.
