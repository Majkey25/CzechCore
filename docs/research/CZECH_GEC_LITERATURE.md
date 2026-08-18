# Czech GEC literature synthesis

## Scope

This synthesis connects Czech-specific grammar checking to general GEC methods.
Primary files are cached and hash-verified through
[`research/sources.json`](../../research/sources.json). PDFs are not committed.

## 2009: syntactic grammar checking

`paper-grammar-checking-czech-2009` describes experience with a Czech grammar
checker based on syntactic analysis. Its central lesson is still relevant:
surface word validity cannot establish grammaticality; non-projectivity and Czech
free word order make robust parsing difficult; hand-built grammars can deepen
linguistic understanding but are costly and brittle.

Implication: CzechCore should use syntax/morphology as evidence and validation,
not build an unbounded rule DSL as its first correction engine.

## 2012: Korektor

`paper-korektor-2012` formulates Czech contextual spelling and diacritics as
noisy-channel sequence decoding. It combines word-form, lemma, and morphological
tag language models with a learned error model and Viterbi search.

Important findings:

- real-word errors require context, not out-of-vocabulary detection;
- morphology-factor language models materially help rich Czech inflection;
- learned edit costs distinguish keyboard adjacency, diacritics, `s/z`, `i/y`,
  insertion, deletion, and transposition;
- a character language model helps add diacritics to unknown words;
- domain mismatch lowers correction quality;
- precision/recall is needed for contextual real-word detection.

Korektor reported about 98% diacritics accuracy on its evaluated settings and
substantially stronger real-word correction than the compared MS Word version.
Those historical numbers are not directly comparable to GECCC F0.5.

Implication: retain unchanged text as a candidate, learn error probabilities, and
evaluate by domain. A future hybrid can use a compact statistical candidate layer
without replacing the neural sentence model.

## 2019: AKCES-GEC and synthetic pretraining

`paper-czech-gec-low-resource-2019` introduced AKCES-GEC in M2 form and showed
that synthetic parallel data can produce strong Transformer GEC in Czech, German,
and Russian despite limited manual annotation.

Implication: synthetic errors are not optional scaffolding; they are a core Czech
data strategy. Train/dev/test provenance and synthetic/manual mixing must be
versioned.

## 2021: multilingual scaling

`paper-multilingual-gec-2021` used language-agnostic corruption and large
multilingual pretrained models. It reported Czech F0.5 of 71.88 for gT5-base and
83.15 for gT5-XXL in the cited setup, showing that scale can compensate for less
language-specific generation.

Implication: large multilingual models are useful teachers and upper bounds, but
their device cost and potential data exposure make them poor default runtimes.

## 2022: GECCC

`paper-geccc-2022` introduced 83,058 Czech sentences across four domains:

- Natives Formal;
- Natives Web Informal;
- Romani;
- Second Learners.

The work professionalized annotation, released Czech ERRANT, compared neural
systems, and meta-evaluated automatic metrics against human judgments.

Implication: an overall score is insufficient. CzechCore must report domain and
error-type slices and retain native/mostly-correct text as a false-positive guard.

## 2023: GEC survey

`paper-gec-survey-2023` reviews rule-based, statistical, machine-translation,
neural, synthetic-data, pretrained-model, and evaluation approaches. It stresses:

- grammatical error boundaries are partly subjective;
- references are incomplete;
- automatic metrics can disagree with human judgments;
- synthetic error design and clean data are central;
- multilingual/non-English GEC remains under-resourced;
- overcorrection and semantic preservation remain open challenges.

Implication: use multiple metrics, targeted human review, and selective prediction.

## 2023: efficient training

`paper-efficient-gec-2023` shows that training objective/schedule improvements can
outperform much larger backbones in evaluated English settings. It reinforces a
project principle: better data and optimization can beat indiscriminate scaling.

Implication: CzechCore should establish compact-teacher distillation and training
schedule experiments before adopting a multi-billion-parameter runtime.

## 2024: general LLM correction risks

`paper-gpt35-gec-2024` reports that GPT-3.5 can substantially alter semantics in
languages including Czech and struggles with several contextual error families.

Implication: a general LLM is not automatically a safe correction oracle.
Generated candidates need edit constraints, semantic-preservation evaluation, and
an unchanged option.

## 2025: MATE and current Czech state of the art

`paper-mate-czech-gec-2025` performs Czech-specific experiments over corpus
choice, synthetic generators, domain balancing, byte/subword tokenization, model
size, fine-tuning scale, and LLM baselines.

Published conclusions relevant to CzechCore:

- SYN-v4 was the strongest tested clean base for synthetic corruption;
- combining language-independent errors, Aspell, MorphoDiTa, and typical Czech
  errors (MATE) beat individual methods;
- domain balancing improved overall GECCC performance;
- byte-level models outperformed corresponding subword models;
- quality continued improving with more annotated data;
- specialized Czech GEC remained stronger/more efficient than much larger LLMs;
- the best reported ByT5-large profile reached 77.34 F0.5 on the paper's sampled
  GECCC comparison, while released model cards report 77.01 on the complete
  GECCC evaluation setup.

The paper also warns that public GECCC test data may have appeared in general LLM
pretraining. Zero-shot LLM scores therefore have contamination uncertainty.

## General architectures relevant to Czech

### ERRANT

`paper-errant-2017` defines automatic edit alignment/classification and per-type
precision, recall, and F-score. `repo-errant-czech` adapts classification using
MorphoDiTa and Czech-specific categories including diacritics, spelling,
inflection, quotation, word order, and morphology.

### GECToR

`paper-gector-2020` predicts token edit transformations with an encoder rather
than autoregressive rewriting. It reported up to 10x faster inference than a
seq2seq baseline in its English experiments.

Implication: a Czech edit-tagger/distilled student is a strong portable-runtime
research direction, but its transformation vocabulary must cover Czech inflection
and free word order.

### ByT5

`paper-byt5-2022` motivates byte-level models as noise-robust and preprocessing
light, at the cost of longer sequences. MATE's Czech results support the approach.

## Research conclusion

The evidence does not support one monolithic solution. The strongest CzechCore
architecture is likely hybrid:

1. exact tokenizer/protected-span layer;
2. compact neural GEC candidate model;
3. MorphoDiTa morphological validity/generation evidence;
4. optional higher-quality teacher/reranker offline profile;
5. calibrated selective policy;
6. structured edit alignment and per-family explanation;
7. standard corpus + correct-text + adversarial evaluation.
