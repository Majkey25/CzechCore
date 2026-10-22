# Evaluation

## Security patch verification, 2026-10-22

For `v0.3.1`, `.venv/Scripts/czechcore-benchmark.exe benchmarks/cases.jsonl --details`
retained 60/65 exact outputs, 34/38 erroneous sentences corrected, 1/27 correct
sentences changed, four unchanged errors, and no wrong alternative rewrites.
The unchanged dataset comes from commit `27631059189fc9ae1cc3549dc5255532df4ef0a9`;
the model remains pinned to `86338eff14fd318c3e8875c911f0778563b4b3b7`.
The run used Windows 10.0.26300, Python 3.12.0, PyTorch 2.14.1+cpu,
Transformers 5.20.2, and ufal.udpipe 1.4.0.1. It took 10.046 seconds
(154.55 ms/sentence) while other tests ran; this is not an isolated latency
comparison with earlier measurements. All 107 local tests, including six real
model tests, passed.

## Three evidence layers

1. **Published evidence** comes from the UFAL model card and peer-reviewed GEC
   work. CzechCore cites it but does not claim to reproduce it locally.
2. **Repository acceptance evidence** detects regressions in concrete product
   behavior. It is small, curated, and not a replacement for GECCC/ERRANT.
3. **Standard corpus evidence** evaluates the complete tokenizer/model/ranking/
   safety pipeline on frozen GECCC with M2Scorer, Czech ERRANT, multiple
   references, and domain slices.

## Acceptance dataset

`benchmarks/cases.jsonl` contains one JSON object per line:

```json
{"source":"Ženy šli domů.","reference":"Ženy šly domů.","category":"subject_predicate_agreement"}
```

Version `0.1.0` contains 35 cases:

- 25 sentences with an expected correction;
- 10 already-correct sentences acting as false-positive guards;
- agreement, commas, diacritics, contextual homographs, `mě/mně`, `s sebou`,
  repeated words, spacing, capitalization, conditional forms, and protected
  technical literals.

## Metrics

For source `x_i`, reference `r_i`, and prediction `p_i`:

```text
exact accuracy = sum[ p_i = r_i ] / N
correction rate = sum[ x_i != r_i and p_i = r_i ] / sum[ x_i != r_i ]
false-change rate = sum[ x_i = r_i and p_i != x_i ] / sum[ x_i = r_i ]
wrong-rewrite count = sum[ x_i != r_i and p_i not in {x_i, r_i} ]
```

These are sentence-exact metrics. They do not give partial credit and do not
compute ERRANT edit precision/recall/F0.5.

## Measured `v0.1.0` baseline

Command:

```powershell
.venv\Scripts\czechcore-benchmark benchmarks\cases.jsonl
```

Environment:

| Property | Value |
| --- | --- |
| Date | 2026-08-18 |
| OS | Windows 10.0.26200 |
| CPU | AMD Ryzen 5 3600, 6 cores / 12 logical processors |
| RAM | 31.9 GiB |
| Python | 3.12.10 |
| PyTorch | 2.13.0, CPU inference |
| Transformers | 5.15.0 |
| `ufal.udpipe` | 1.4.0.1 |

Results:

| Measure | Count | Rate |
| --- | ---: | ---: |
| Exact outputs | 34 / 35 | 97.14% |
| Erroneous sentences corrected exactly | 24 / 25 | 96.00% |
| Correct sentences changed | 0 / 10 | 0.00% |
| Wrong alternative rewrites | 0 | 0.00% of all cases |
| Erroneous sentences left unchanged | 1 / 25 | 4.00% |
| Mean latency after model load | — | 211.90 ms/sentence |

Raw CLI output:

```json
{"total":35,"exact_matches":34,"source_correct":10,"changed_correct_sentences":0,"corrected_incorrect_sentences":24,"unchanged_incorrect_sentences":1,"wrong_incorrect_predictions":0,"elapsed_seconds":7.4164788000052795,"mean_latency_ms":211.89939428586513}
```

The remaining failure is:

```text
source:    Petr a Jana šla domů.
reference: Petr a Jana šli domů.
prediction: unchanged
```

This is retained as a regression target. It is not patched with a sentence or
name-specific rule.

## Engineering verification

The `v0.1.0` release gate also requires:

- 50 pytest tests after repository polish, including real model/tokenizer tests;
- 81% combined branch-aware code coverage in the release run; uncovered lines
  are mainly network/error/CLI defensive paths, not a linguistic quality score;
- Ruff lint and format checks;
- strict Pyright with zero diagnostics;
- `pip check` dependency consistency;
- wheel build and installation smoke test;
- live suggestion, autocorrect, negative, protected-text, multi-sentence, and
  long-sentence scenarios;
- successful GitHub Actions on the release commit.

The exact final counts are updated during release verification. They are not
substitutes for linguistic corpus evaluation.

## Measured `v0.2.0` research baseline

The acceptance suite now has 65 cases and the complete GECCC development split
has been evaluated. The current safety replay produces:

| Measure | Result |
| --- | ---: |
| Acceptance exact | 60 / 65 |
| Acceptance false changes | 1 / 27 |
| Acceptance batch-16 mean latency | 72.79 ms/sentence |
| GECCC dev sentence exact | 4,152 / 8,478 |
| GECCC dev false changes | 558 / 3,288 correct sources |
| GECCC dev M2 precision / recall / F0.5 | 0.7884 / 0.3551 / 0.6337 |
| Initial Czech ERRANT precision / recall / F0.5 | 0.7172 / 0.3473 / 0.5912 |

This fails the production-autocorrect gate. See
[`docs/research/GECCC_BASELINE.md`](research/GECCC_BASELINE.md) and the committed
machine-readable evaluation record for full configuration and category results.

Final focused-suite command:

```powershell
.venv\Scripts\czechcore-benchmark benchmarks\cases.jsonl --batch-size 16
```

Final focused-suite output:

```json
{"total":65,"exact_matches":60,"source_correct":27,"changed_correct_sentences":1,"corrected_incorrect_sentences":34,"unchanged_incorrect_sentences":4,"wrong_incorrect_predictions":0,"elapsed_seconds":4.731189700018149,"mean_latency_ms":72.78753384643306}
```

## How to extend the benchmark

- Add the minimal sentence that isolates one phenomenon.
- Add a corresponding correct/negative case where false positives are plausible.
- Verify Czech against an authoritative source such as the
  [Internetová jazyková příručka](https://prirucka.ujc.cas.cz/pda).
- Keep category names stable and machine-readable.
- Never remove a failure merely to raise the headline score.
- Do not copy corpus examples unless redistribution is licensed.

## Required next evaluation

Before enabling a lower default autocorrect threshold:

1. evaluate on a held-out, redistributable Czech GEC corpus;
2. compute edit precision, recall, and F0.5 with Czech ERRANT or an equivalent
   reproducible scorer;
3. report results separately by domain and error type;
4. calibrate confidence on development data only;
5. freeze thresholds before the final test run;
6. measure CPU, memory, startup, and mobile-export latency.
