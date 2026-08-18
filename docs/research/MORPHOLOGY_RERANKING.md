# MorphoDiTa features for Czech candidate reranking

## Objective

The current beam-relative confidence does not predict correctness. MorphoDiTa and
MorfFlex can add Czech lexical/morphological evidence to a learned selective
ranker, but must not become a brittle hardcoded grammar system.

## Verified local probe

Using `czech-morfflex2.1-250909.dict` from source
`dataset-morphodita-250909` with `NO_GUESSER`:

| Form | Dictionary result |
| --- | --- |
| `přijdeš` | lemma `přijít`, tag `VB-S---2P-AAP--` |
| `přijedeš` | lemma `přijet`, tag `VB-S---2P-AAP--` |
| `přišly` | lemma `přijít`, feminine/neuter plural participle analyses |
| `přišli` | lemma `přijít`, masculine animate plural participle |
| `vyděli` | unknown without guesser |
| `viděli` | lemma `vidět`, masculine animate plural participle |
| `mě` | lemma `já`, case 2/4/6 analyses |
| `mně` | lemma `já`, case 3/6 analyses |

This separates the observed semantic drift `přijdeš → přijedeš` from a normal
same-lemma agreement repair `přišly → přišli`, and distinguishes unknown spelling
from a known candidate.

## Why it is not a hard gate

Different lemmas do not automatically imply an invalid correction. Czech
contextual homographs (`být/bít`), lexical choice, prepositions, derivation, and
real-word learner errors can require a different lemma. Conversely, equal lemmas
do not prove that case, number, gender, person, or sentence meaning is correct.

A rule such as `reject when lemma differs` would raise a small acceptance score
while silently blocking valid Czech. It is rejected.

## Ranker features

For every model candidate and unchanged source, extract bounded features:

- source/candidate dictionary-known flags without guesser;
- raw lemma overlap and derivational relation;
- POS and PDT tag compatibility;
- case/gender/number/person/tense differences;
- token insertion/deletion/reordering counts;
- UDPipe dependency relation and subject-predicate feature compatibility;
- Czech ERRANT operation/type where available;
- model source/top scores and score margin;
- changed ratio, length, protected-literal and typography signals;
- local semantic-equivalence score for lexical/broad changes.

Train/calibrate on GECCC development only, with separate labels for exact edit,
valid alternative, unnecessary change, wrong rewrite, and abstention. Evaluate
precision-coverage by domain/type; freeze before test.

## Runtime profile

The full MorfFlex dictionary used by the probe is about 3.9 MB; the full context
tagger is about 26 MB. Both run locally. The model data is CC BY-NC-SA 4.0, so it
does not resolve the current non-commercial asset constraint. Start with the
dictionary for cheap candidate features; add the tagger only if measured context
gain justifies memory/latency.

## First learned-ranker screen: 2026-08-18

A 19-feature logistic calibration layer was trained on 2,764 changed GECCC dev
candidates, calibrated on 705, and validated on 371. Splits were grouped by
document pointer, not random sentence, to reduce author/document leakage.

- target: at least 90% exact-sentence precision and 20 calibration accepts;
- ranker: no threshold met the target, so coverage is zero;
- diagnostic top frontier: 5/5 on calibration became only 5/6 (83.3%) on
  validation;
- with at least 20 validation accepts: 19/28 (67.9%);
- confidence-only calibration was much weaker (best reported calibration slice
  115/280 = 41.1%).

The experiment proves that morphology/surface features help ordering but are not
enough for production autocorrect. The local artifact is rejected and not
committed. Results and split counts are in
`research/evaluations/ranker-screen-2026-08-18.json`. Next features must include
source-vs-top score margins, beam edit agreement, dependency evidence, semantic
equivalence, and human labels for valid alternatives missing from single
references.
