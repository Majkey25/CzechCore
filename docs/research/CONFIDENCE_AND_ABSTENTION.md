# Confidence, calibration, and abstention

## Current score

CzechCore generates four beams and adds the unchanged sentence. For normalized
candidate scores `s_i`, it reports:

```text
q_i = exp(s_i - max(s)) / sum_j exp(s_j - max(s))
```

`q_i` is relative mass within this small candidate set. It is not a probability
that the edit is correct. It depends on beam diversity, sequence length scoring,
candidate deduplication, and whether the true correction is present.

## Measured GECCC development result

The complete fixed batch-16 run confirms that `q_i` is not a usable correctness
calibrator. Sentence change precision rises only from 37.03% at threshold `0.25`
to a maximum measured 49.73% at `0.40`, while coverage falls from 45.29% to 8.78%.
Higher thresholds become anti-useful: at `0.60` precision is 23.53%, and `0.995`
accepts nothing. M2 F0.5 falls from `0.6337` at `0.25` to `0.1648` at `0.40`.

Conclusion: do not lower autocorrect or claim that a higher current value means a
more correct sentence. Train a separate ranker/calibrator from source/top margins,
beam agreement, edit structure, MorphoDiTa/UDPipe features, domain, and semantic
equivalence labels.

## Why rank is insufficient

- The top candidate can be wrong while much higher than the second.
- Several beams can share the same edit but differ elsewhere.
- An unchanged sentence may be valid even when its model score is lower.
- Sequence confidence does not identify which individual edit is uncertain.
- Domain shift changes score distributions.
- A public/test-contaminated teacher can appear overconfident.

## Selective prediction

The correction system chooses among:

1. apply automatically;
2. show a suggestion;
3. abstain.

The goal is a precision-coverage frontier, not maximum edit count. For threshold
`t`:

```text
coverage(t) = accepted candidate sentences / eligible sentences
precision(t) = correct accepted edits / all accepted edits
```

Autocorrect threshold selection must state a minimum precision goal and report the
resulting coverage with confidence intervals.

## Calibration protocol

1. Generate frozen n-best predictions on development data.
2. Convert candidate output to Czech ERRANT edits.
3. Define sentence correctness and per-edit correctness against all references.
4. Build features without test access:
   - top score and top-second margin;
   - unchanged-candidate margin;
   - beam agreement per edit;
   - edit count/type/size;
   - morphology validity/compatibility;
   - protected-text/rewrite ratio;
   - sentence length and domain.
5. Fit simple calibration first: temperature scaling or logistic regression.
6. Compare isotonic calibration only if data volume supports it.
7. Evaluate reliability diagram, expected calibration error, Brier score, and
   precision-coverage curves.
8. Freeze thresholds before final test evaluation.

The calibrator must be bounded, versioned, and included in the model manifest.

## Edit confidence

Sequence-level confidence currently applies to all edits in a candidate. Better
per-edit evidence can come from:

- edit presence across unique beams;
- local token log-probability difference;
- unchanged-local-span alternative score;
- morphology and dependency compatibility;
- a dedicated edit correctness head;
- teacher/reranker agreement.

Partial application remains unsafe unless the resulting sentence itself is scored
and validated. Atomic sentence edits stay the default.

## Hard safety gates

Confidence does not override deterministic safety:

- protected literals must remain exact;
- over-length sentences are not truncated;
- broad rewrite ratio is bounded;
- invalid source offsets fail;
- missing assets/runtime errors are explicit.

## Human-facing language

Do not label current `q_i` as “99.5% correct.” UI/API documentation should use
“relative model confidence” until empirical calibration exists. Explanations must
separate model evidence from authoritative grammar rules.

## Release gate

A default autocorrect threshold can be lowered only after:

- standard held-out Czech evaluation;
- correct-text/low-error-density evaluation;
- per-domain/error precision;
- calibration and confidence intervals;
- adversarial semantic-preservation review;
- no regression in protected text and offset safety.
