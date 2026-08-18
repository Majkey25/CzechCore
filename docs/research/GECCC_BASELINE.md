# CzechCore GECCC development baseline

## Verdict

The first full standard-corpus run fails the release gate. The compact model is
useful, especially for diacritics and punctuation, but the current selective
policy changes too many already-correct sentences and misses broad Czech syntax.
The earlier 35-case acceptance score substantially overestimated production
quality.

Machine-readable results are in
`research/evaluations/geccc-dev-2026-08-18.json`. Raw predictions, M2 files, and
corpus data remain in the ignored `.reference/research/` cache.

## Frozen inputs

- GECCC handle `11234/1-4861`, dev split, 8,478 sentences;
- source, gold, and metadata hashes recorded in the local sentence report;
- `ufal/transformer-base-geccc-mate` revision
  `86338eff14fd318c3e8875c911f0778563b4b3b7`;
- UDPipe model SHA-256 pinned in `src/czechcore/assets.py`;
- four-beam CPU inference, unchanged candidate, suggestion floor `0.25`, changed
  ratio `0.35`;
- MATE M2Scorer fork revision
  `ebd05e6a1cdd15e96b05d30aa5379d623052a9ea` and Czech ERRANT revision
  `fcbe82b582aa2f9c64dc943a7659cd4400b07a52`.

## Runtime

| Metric | Result |
| --- | ---: |
| Sentences | 8,478 |
| Elapsed | 1,939.09 s |
| Mean latency | 228.72 ms/sentence |
| Changed sentences | 3,985 |
| Abstention warnings | 1,961 |

Batch 16 produced identical predictions to single-sentence inference on the fixed
100-sentence comparison sample and reduced mean latency from 401.63 ms to
196.13 ms there. Batch 32 was slower on the full split (290.98 ms/sentence) and
changed 5/8,478 outputs relative to batch 16 because padded numerical execution
altered close rankings. Exact reproducibility therefore pins batch size 16.

## Sentence results

| Metric | Initial pipeline | Current safety replay |
| --- | ---: | ---: |
| Exact | 4,108 | 4,152 |
| Correct source sentences | 3,288 | 3,288 |
| False changes | 605 | 558 |
| Erroneous sentences corrected exactly | 1,381 | 1,378 |
| Erroneous sentences unchanged | 1,810 | 1,908 |
| Wrong alternative rewrites | 1,999 | 1,904 |

The current phone/date/abbreviation/quotation invariants reject 153 old candidates.
They remove 47 false changes and 95 wrong rewrites while losing three exact
corrections and increasing unchanged errors by 98. The remaining 558 false
changes are not acceptable for default suggestions or autocorrect.

## Edit metrics

| Protocol | Precision | Recall | F0.5 |
| --- | ---: | ---: | ---: |
| MATE M2Scorer, initial | 0.7802 | 0.3673 | 0.6370 |
| MATE M2Scorer, current safety replay | 0.7884 | 0.3551 | 0.6337 |
| Czech ERRANT, initial | 0.7172 | 0.3473 | 0.5912 |

M2Scorer and Czech ERRANT use different alignment/selection behavior and are not
interchangeable. Both are kept. The released model card reports M2 F0.5 `0.7373`
for the model evaluation; CzechCore's tokenizer, unchanged-candidate scoring,
confidence floor, protected literals, and rewrite-ratio gate materially change
the product output.

## Confidence threshold result

The fixed batch-16 diagnostics prove that current relative beam confidence cannot
select safe corrections:

| Threshold | Coverage | Sentence change precision | False-change rate | M2 P / R / F0.5 |
| ---: | ---: | ---: | ---: | ---: |
| 0.25 | 45.29% | 37.03% | 16.97% | 0.7884 / 0.3551 / 0.6337 |
| 0.30 | 25.03% | 45.62% | 12.99% | 0.8080 / 0.1491 / 0.4289 |
| 0.35 | 14.53% | 48.30% | 8.94% | 0.8146 / 0.0748 / 0.2735 |
| 0.40 | 8.78% | 49.73% | 6.66% | 0.8035 / 0.0394 / 0.1648 |
| 0.995 | 0% | no accepted changes | 0% | not meaningful |

Sentence change precision is intentionally strict: a changed sentence must match
one released reference exactly. It is not edit precision. Raising the scalar
threshold destroys recall, never reaches autocorrect-grade precision, and becomes
zero-coverage at the current default. A learned ranker/calibrator with model
margins, morphology, dependency, edit, domain, and semantic features is required.

## Czech ERRANT category findings

Selected F0.5 values:

| Category | F0.5 | Main observation |
| --- | ---: | --- |
| `PROPN:INFL` | 0.8333 | Strong but low-count proper-name inflection |
| `DIACR` | 0.7580 | Best high-volume category |
| `NUM:INFL` | 0.6818 | High precision, limited recall |
| `PRON:INFL` | 0.6649 | Useful inflectional signal |
| `ADJ:INFL` | 0.6604 | Useful agreement/inflection signal |
| `PUNCT` | 0.6108 | Material value, recall only 0.3633 |
| `MORPH` | 0.5694 | Moderate morphology |
| `WO` | 0.4240 | Weak word order |
| `VERB` | 0.2964 | Weak broad verb corrections |
| `OTHER` | 0.2916 | Major heterogeneous gap |
| `CCONJ` | 0.1274 | Very low coordination recall |

## Required next work

1. Build development-set precision/coverage curves from per-candidate confidence;
   do not choose thresholds from the test split.
2. Separate harmless reference alternatives from semantic drift with human and
   semantic-equivalence review.
3. Evaluate raw top beam versus unchanged-candidate ranking to locate the published
   model/product score gap.
4. Add local-LLM semantic rewrite as an explicit mode, never silent autocorrect.
5. Improve coordinated agreement, valency, pronouns, vocative, verbs, conjunctions,
   and word order through model/data work, not lexical special cases.
6. Freeze the policy, then run untouched GECCC test and adversarial/correct-text
   suites.
