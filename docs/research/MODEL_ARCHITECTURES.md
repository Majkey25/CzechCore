# Model architecture research

## Decision problem

CzechCore must maximize Czech correction quality while preserving exact edits,
privacy, deterministic deployment, and a path to Windows/Android. Accuracy alone
does not choose a runtime; size, latency, semantic drift, calibration, licensing,
and exportability are co-equal constraints.

## 1. Statistical noisy-channel model

Korektor represents candidate sentences with a weighted combination of word-form,
lemma, and morphological-tag n-gram language models plus an error channel. Viterbi
decoding searches the sequence.

Strengths:

- compact and explainable candidate costs;
- explicit error probabilities;
- strong contextual spelling/diacritics;
- unchanged candidates naturally represented;
- morphology factors fit Czech.

Limits:

- n-gram context is short;
- broad syntax/punctuation/semantic corrections are limited;
- retraining requires corpora and error models;
- historical model/data licenses remain relevant.

Best role: candidate generation, lexical/diacritics fallback, or precision feature
inside a hybrid.

## 2. Subword encoder-decoder Transformer

The current baseline is a six-layer encoder/decoder BART-style model with a 32k
WordPiece vocabulary and approximately 60.8M parameters.

Strengths:

- full-sentence contextual generation;
- substantially smaller than released ByT5 profiles;
- published GECCC F0.5 73.73;
- practical CPU baseline;
- standard PyTorch/Transformers implementation.

Limits:

- autoregressive decoder latency;
- tokenizer compatibility is an explicit invariant;
- can rewrite text beyond a local edit;
- one candidate score is shared by all extracted edits;
- 256-position sentence limit;
- published license is non-commercial.

Best role: current runtime baseline and student target.

## 3. Byte-level ByT5

ByT5 consumes UTF-8 bytes rather than subwords. Published work argues that byte
models reduce tokenizer complexity and improve noise robustness; MATE reports
strong Czech results and increasing quality with model size.

Strengths:

- robust character/diacritics/spelling representation;
- no language-specific subword vocabulary;
- released Czech models and metrics;
- ByT5-large is the current released MATE quality leader.

Limits:

- byte sequences are longer;
- 300M/582M/1.275B profiles are heavy for devices;
- autoregressive decoding remains;
- full F32 weights are impractical for default mobile use;
- same non-commercial model license.

Best role: teacher, desktop quality profile, distillation source, and research
upper bound. Actual use requires downloading and benchmarking weights, not merely
trusting the model-card score.

## 4. Edit sequence tagging

GECToR predicts token transformations with an encoder and lightweight output head.
The paper reports up to 10x faster inference than its seq2seq comparison.

Potential Czech advantages:

- low-latency structured edits;
- reduced free-form rewriting;
- easier per-edit confidence;
- natural mobile/desktop integration.

Czech-specific challenges:

- rich inflection requires a large or generative transformation vocabulary;
- split/join, word order, punctuation, and multi-token replacements are harder;
- unknown word forms/proper names need morphology or copy mechanisms;
- a Czech tagger must be trained/evaluated; English results do not transfer by
  assumption.

Best role: distilled portable student if Czech coverage is proven.

## 5. General-purpose LLM

Large instruction models can correct Czech zero-shot or after fine-tuning. MATE
reports competitive results for fine-tuned recent LLMs, while specialized GEC
models remain stronger/more efficient in the reported comparison.

Risks:

- multi-billion-parameter size;
- semantic paraphrasing and overcorrection;
- nondeterministic prompting/runtime behavior;
- uncertain public benchmark contamination;
- difficult device deployment;
- instruction-following can conflict with exact edit preservation.

Best role: research teacher or constrained reranker after semantic-preservation
tests, not an unconditional runtime oracle.

## 6. Morphological/syntactic hybrid

MorphoDiTa can analyze/generate Czech forms and tag context. UDPipe can add
dependency structure. Neither alone is a complete correction system.

Useful hybrid signals:

- source/candidate lexical validity;
- same-lemma inflection alternatives;
- gender/animacy/number/case/person features;
- subject/predicate and attribute dependencies;
- preposition/case government features;
- candidate explanation metadata;
- synthetic Czech error generation.

The hybrid must not reject valid unknown names/technical terms or treat parser
output as truth. Morphological/parser confidence and coverage require evaluation.

## Recommended architecture program

```text
protected text + exact ranges
        -> compact candidate model
        -> optional morphology/dependency evidence
        -> candidate set including unchanged text
        -> optional teacher/reranker profile
        -> calibrated selective policy
        -> atomic structured edits + explanations
```

Experiments should compare:

1. current compact Transformer;
2. ByT5-base/large teacher quality;
3. morphology-informed reranking without retraining;
4. compact model fine-tuned with updated MATE/data balancing;
5. distilled encoder-decoder student;
6. Czech edit-tagger student;
7. quantized/exported variants.

No candidate becomes default without full GECCC/domain/error-type, correct-text,
semantic-preservation, latency, memory, startup, and license gates.
