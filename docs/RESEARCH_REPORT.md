# CzechCore research and engineering report

## Document control

| Field | Value |
| --- | --- |
| Report date | 2026-08-18 |
| Software release | `v0.2.0` research alpha |
| Primary task | Offline Czech grammatical error correction |
| Reference implementation | Python 3.12, PyTorch, Transformers, UDPipe |
| Default correction model | `ufal/transformer-base-geccc-mate` |
| Evaluation corpus | GECCC development split, 8,478 sentences |
| Publication policy | Measured, published, and planned claims are separated |

## Abstract

CzechCore is a fully local, sentence-context Czech grammatical error correction
(GEC) system designed to return exact source edits for underlines, suggestions,
and controlled application. It combines a compact 60.8M-parameter Czech
encoder-decoder Transformer, the model-compatible UDPipe tokenizer, deterministic
content-preservation checks, and Unicode edit alignment. A separate review-only
path combines the proofreader with a caller-supplied local instruction model for
broader sentence reconstruction.

The complete GECCC development evaluation reaches M2 precision `0.7884`, recall
`0.3551`, and F0.5 `0.6337`. The system corrects useful diacritic,
punctuation, and inflectional errors, but changes 558 of 3,288 already-correct
source sentences and leaves substantial coordination, verb, conjunction, and
word-order gaps. The current beam-relative score does not calibrate correctness:
raising its threshold reduces coverage without reaching production-grade
sentence precision. A 19-feature morphological ranker and four local-LLM
profiles were screened and rejected as production defaults.

The engineering result is therefore a real, reproducible research engine and
integration-ready edit contract—not a claim of complete Czech correction.
System-wide automatic correction remains gated on a trained edit-validity and
semantic-equivalence model plus frozen held-out evaluation.

## 1. Problem and research questions

For observed Czech text `x`, GEC searches for a corrected text `y`:

```text
y* = argmax_y log P(y | x)
```

This formulation is insufficient on its own. Many Czech forms are valid in one
sentence and wrong in another, multiple corrections may be acceptable, and a
fluent candidate may alter meaning. CzechCore therefore evaluates five questions:

1. **Correction value:** Which Czech error families does the compact model
   correct reliably enough to expose as suggestions?
2. **False-change risk:** How often does the pipeline alter already-correct text?
3. **Selection:** Can model confidence or cheap morphology features identify a
   safe automatic subset?
4. **Semantic reconstruction:** Can a small local LLM repair disordered text
   without changing facts or intent?
5. **Deployment:** Can one correction contract serve a CLI, Windows text service,
   and Android text services without duplicating linguistic policy?

## 2. Evidence base

### 2.1 Normative and linguistic scope

The machine-readable taxonomy is validated against:

- all 22 chapters and 202 general explanations in the official
  [Internetová jazyková příručka](https://prirucka.ujc.cas.cz/pda);
- all 65 Czech ERRANT error types observed in the selected GECCC archive;
- 39 provenance records covering primary papers, corpora, repositories, model
  cards, evaluators, and the official rule collection.

The resulting taxonomy contains 13 families and 101 correction phenomena.
Taxonomy coverage means a phenomenon is defined, sourced, and assigned an
evaluation path. It does not assert that the runtime solves it.

### 2.2 Corpora

| Corpus | Use | Size / split | License |
| --- | --- | ---: | --- |
| GECCC `11234/1-4861` | Main Czech GEC research and evaluation | 83,058 sentences; 66,673 / 8,478 / 7,907 train/dev/test | CC BY-SA 4.0 |
| AKCES-GEC `11234/1-3057` | Learner-domain and alternate taxonomy research | Train/dev/test variants | CC BY-NC-SA 4.0 |
| Focused acceptance suite | Repository regression and protected-text checks | 65 cases | Project-authored |
| Rewrite acceptance suite | Meaning and invariant screen | 12 cases | Project-authored |

GECCC contains 57,122 sentences with edits and 228,805 annotated edits across
native formal, native informal web, Romani, and second-language domains.
Raw licensed corpora stay outside Git. Their handles, hashes, derived aggregate
metadata, and evaluator revisions are recorded in the repository.

### 2.3 Models and linguistic resources

| Component | Role | Relevant property |
| --- | --- | --- |
| UFAL compact Transformer | Default sentence GEC | 60.8M parameters, 6+6 layers, 32k WordPiece vocabulary |
| Czech UDPipe 1 | Sentence/token boundaries and exact ranges | Pinned model hash |
| MorphoDiTa / MorfFlex | Experimental morphology and generation evidence | Full dictionary about 3.9 MB; context tagger about 26 MB |
| Local instruction LLM | Explicit semantic rewrite candidate | Caller-supplied; no approved default |

The default Transformer and UDPipe assets are CC BY-NC-SA 4.0. They are
downloaded separately and are not part of the MIT source wheel.

## 3. Implemented system

### 3.1 Proofread path

```text
original text
  -> UDPipe sentence spans and exact token ranges
  -> exact adjacent-repeat correction
  -> WordPiece encoding
  -> four deterministic Transformer beams
  -> unchanged-sentence candidate
  -> relative candidate scoring
  -> protected-literal and changed-ratio gates
  -> Unicode alignment
  -> structured suggestions / optional atomic output
```

The engine rejects over-length input rather than truncating it. It preserves URLs,
email addresses, Windows paths, semantic versions, dates, phone numbers,
all-capital abbreviations, code-like tokens, and Czech quotation boundaries.
Candidate safety is rechecked for the complete document after sentence assembly.

### 3.2 Edit contract

Each `TextEdit` contains:

- half-open source offsets `[start, end)` in Unicode code points;
- exact source and replacement strings;
- a mechanical edit category;
- relative model confidence;
- whether the edit contributes to `output_text`.

Edits are ordered, non-overlapping, source-validated, and applied right-to-left.
Platform adapters must convert these offsets to UTF-16 and test non-BMP text such
as emoji.

### 3.3 Rewrite path

`HybridRewriter` supplies the source, conservative proofread, and a separately
masked high-recall GEC candidate to a loopback-only local chat endpoint. It then
checks protected literals, number/sign sequences, line structure, and unexpected
special tokens. An invariant failure falls back to proofread/source.

Rewrite output always has `requires_review=True`. The current implementation
does not claim that its invariants prove semantic equivalence.

## 4. Evaluation method

### 4.1 Frozen runtime inputs

- Transformer revision
  `86338eff14fd318c3e8875c911f0778563b4b3b7`;
- hash-pinned Czech UDPipe model;
- four-beam CPU inference;
- unchanged sentence included;
- suggestion floor `0.25`;
- maximum changed-character ratio `0.35`;
- batch size 16 for the reported GECCC run;
- MATE M2Scorer revision
  `ebd05e6a1cdd15e96b05d30aa5379d623052a9ea`;
- Czech ERRANT revision
  `fcbe82b582aa2f9c64dc943a7659cd4400b07a52`.

Batch size is pinned because batch 32 changed 5 of 8,478 close predictions due to
numerical padding effects.

### 4.2 Metrics

The report keeps three distinct evidence layers:

1. sentence-exact focused acceptance for regression;
2. M2Scorer and Czech ERRANT edit precision/recall/F0.5;
3. safety metrics for correct-text false changes, wrong alternatives, warnings,
   protected literals, offsets, and runtime.

M2 and ERRANT use different alignments and are not interchangeable. A single
reference can also mark a linguistically valid alternative as wrong, so automatic
metrics require human semantic review before deployment thresholds are frozen.

## 5. Results

### 5.1 Complete GECCC development run

| Metric | Current safety pipeline |
| --- | ---: |
| Sentences | 8,478 |
| Exact sentence outputs | 4,152 |
| Correct source sentences | 3,288 |
| Correct sources changed | 558 |
| Erroneous sentences corrected exactly | 1,378 |
| Erroneous sentences left unchanged | 1,908 |
| Wrong alternative rewrites | 1,904 |
| M2 precision / recall / F0.5 | 0.7884 / 0.3551 / 0.6337 |
| Initial Czech ERRANT precision / recall / F0.5 | 0.7172 / 0.3473 / 0.5912 |
| Elapsed / mean latency | 1,939.09 s / 228.72 ms |

Phone, date, abbreviation, and quotation invariants rejected 153 previous
candidates. They removed 47 false changes and 95 wrong rewrites at the cost of
three exact corrections and 98 additional unchanged errors. This is the intended
precision/recall trade: deterministic damage prevention can abstain, but it
cannot repair the neural model's semantic ranking.

### 5.2 Focused acceptance

| Metric | Result |
| --- | ---: |
| Exact outputs | 60 / 65 |
| Erroneous inputs corrected exactly | 34 / 38 |
| Correct inputs changed | 1 / 27 |
| Wrong alternative rewrites | 0 |
| Warm batch-16 latency | 72.79 ms/sentence |

The gap between 60/65 focused acceptance and the complete GECCC result
demonstrates why a polished demo set is not a production accuracy estimate.

### 5.3 Selected error-family findings

| Czech ERRANT category | F0.5 | Finding |
| --- | ---: | --- |
| `DIACR` | 0.7580 | Strongest high-volume family |
| `NUM:INFL` | 0.6818 | High precision, limited recall |
| `PRON:INFL` | 0.6649 | Useful pronoun inflection signal |
| `ADJ:INFL` | 0.6604 | Useful agreement/inflection signal |
| `PUNCT` | 0.6108 | Material value; recall remains limited |
| `MORPH` | 0.5694 | Moderate broad morphology |
| `WO` | 0.4240 | Weak word order |
| `VERB` | 0.2964 | Weak broad verb correction |
| `CCONJ` | 0.1274 | Major coordination gap |

The model is useful for local surface and inflectional repair. It is materially
weaker on broad syntax, coordination, lexical choice, and reordered clauses.

## 6. Confidence and automatic application

For normalized candidate scores `s_i`, the current API reports:

```text
q_i = exp(s_i - max(s)) / sum_j exp(s_j - max(s))
```

`q_i` is relative mass among a small beam set, not the probability that an edit
is correct.

| Threshold | Coverage | Strict sentence change precision | M2 F0.5 |
| ---: | ---: | ---: | ---: |
| 0.25 | 45.29% | 37.03% | 0.6337 |
| 0.30 | 25.03% | 45.62% | 0.4289 |
| 0.35 | 14.53% | 48.30% | 0.2735 |
| 0.40 | 8.78% | 49.73% | 0.1648 |
| 0.995 | 0% | No accepted changes | Not meaningful |

No current threshold supports useful production autocorrection. The public
threshold remains an experimental research control; user-facing automatic mode
must wait for a separately calibrated accept/reject model with confidence
intervals and non-zero held-out coverage.

## 7. Morphology and semantic selection experiments

### 7.1 MorphoDiTa screen

Local dictionary probes correctly distinguish, for example:

- `přijdeš` (lemma `přijít`) from `přijedeš` (lemma `přijet`);
- `přišly` and `přišli` as same-lemma gender/animacy alternatives;
- unknown `vyděli` from dictionary-known `viděli`;
- case analyses for `mě` and `mně`.

A document-grouped 19-feature logistic ranker used 2,764 training, 705
calibration, and 371 validation candidates. No threshold met the target of 90%
precision with at least 20 accepts. Its best five calibration examples became
5/6 (83.3%) on validation; with at least 20 validation accepts it reached 19/28
(67.9%). The artifact was rejected and not committed.

### 7.2 Local rewrite screen

| Model | Weight size | Result |
| --- | ---: | --- |
| Qwen3 0.6B Q4_0 | 409 MB | Lost protected content and damaged Czech |
| Qwen3 4B Q4_K_M | 2.33 GiB | Altered `pip` and the source claim |
| Qwen3.5 4B Q4_K_M | 2.55 GiB | Altered `pip` and misread `širší` |
| Aya Expanse 8B Q4_K_M | 4.71 GiB | Best screen; 4/12 exact, still failed the user example |

All four models failed the default gate. Aya is retained only as a potential
teacher. The evidence supports task-specific Czech fine-tuning/distillation and a
semantic-equivalence verifier, not more prompt decoration.

## 8. Deployment decision

One correction policy must serve every platform. The approved direction is:

- a portable local runtime with a narrow versioned contract;
- Android `SpellCheckerService` for supported underlines and an optional IME for
  true live suggestions/automatic application;
- a Windows TSF text service with a single per-user engine process;
- `off / underline / confirm / automatic` modes controlled by the user;
- revision IDs, cancellation, debounce, sensitive-field exclusion, exact UTF-16
  conversion, and one-step undo;
- explicit selection-based rewrite only.

The current Python runtime is the reference, not the final Android package.
ONNX export, tokenizer parity, generation parity, quantization, device memory,
latency, and thermal measurements are still required. See
[PLATFORM_INTEGRATION.md](PLATFORM_INTEGRATION.md).

## 9. Validity limits

- Only the GECCC development split has been used for policy exploration; the
  final test split must remain untouched until policy freeze.
- GECCC references are not exhaustive lists of all valid Czech alternatives.
- The focused suite is deliberately small and can overestimate quality.
- Current measurements are CPU measurements on one Windows machine, not Android
  device results.
- The sentence model does not use full document discourse.
- The rewrite suite has 12 cases and cannot establish general semantic safety.
- Non-commercial model/data licenses block a commercial default distribution.
- No present result supports the phrase “always correct.”

## 10. Release verdict

`v0.2.0` is suitable for:

- offline Czech GEC research and reproducible experiments;
- CLI proofread and structured suggestion integration;
- building underline/confirmation prototypes;
- corpus, taxonomy, safety, and local-model evaluation work.

It is not yet suitable for:

- silent system-wide autocorrection;
- an unreviewed whole-sentence rewrite feature;
- commercial redistribution of the default model stack;
- claims of complete Czech grammar coverage;
- Android/Windows production installation.

The next production gate requires a trained selector with a frozen
precision/coverage target, human labels for valid alternatives and semantic
drift, untouched GECCC test evaluation, adversarial correct-text suites, and real
Windows/Android runtime measurements.

## 11. Reproducibility

```powershell
.venv\Scripts\python -m tools.research.validate_sources --schema-only
.venv\Scripts\python -m tools.research.validate_taxonomy
.venv\Scripts\python -m tools.research.build_coverage --check
.venv\Scripts\python -m tools.research.validate_rewrite_cases
.venv\Scripts\python -m pytest
.venv\Scripts\czechcore-benchmark benchmarks\cases.jsonl
```

Machine-readable published results:

- `research/evaluations/geccc-dev-2026-08-18.json`;
- `research/evaluations/ranker-screen-2026-08-18.json`;
- `research/evaluations/rewrite-model-screen-2026-08-18.json`;
- `research/coverage.json`;
- `research/sources.json`;
- `research/taxonomy.json`.

## References

1. Náplava, J. et al. (2022). [Czech Grammar Error Correction with a Large and
   Diverse Corpus](https://aclanthology.org/2022.tacl-1.26/). *Transactions of
   the Association for Computational Linguistics*, 10, 452–467.
2. Pechman, P., Straka, M., Straková, J., and Náplava, J. (2026).
   [Refining Czech GEC: Insights from a Multi-Experiment
   Approach](https://doi.org/10.1007/978-3-032-02551-7_7). *Text, Speech, and
   Dialogue*, 64–76.
3. Náplava, J. and Straka, M. (2019). [Grammatical Error Correction in Low-Resource
   Scenarios](https://aclanthology.org/W19-4429/).
4. Bryant, C., Felice, M., and Briscoe, T. (2017).
   [Automatic Annotation and Evaluation of Error Types for Grammatical Error
   Correction](https://aclanthology.org/P17-1074/).
5. Ústav pro jazyk český AV ČR.
   [Internetová jazyková příručka](https://prirucka.ujc.cas.cz/).
6. Straka, M. and Straková, J. (2017).
   [Tokenizing, POS Tagging, Lemmatizing and Parsing UD 2.0 with
   UDPipe](https://ufal.mff.cuni.cz/biblio/attachments/2017-straka-m1614289952260637039.pdf).
