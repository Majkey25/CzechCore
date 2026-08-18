# Training and synthetic-error research

## Why synthetic data is central

Manual Czech GEC data is substantial but still small relative to neural model
capacity and the combinatorial space of Czech morphology/syntax. The 2019 Czech
work and MATE both use synthetic corruption before supervised fine-tuning.

Synthetic data must approximate plausible writer errors without teaching the
model arbitrary noise or leaking test text.

## Evidence from Czech work

### Low-resource 2019

The AKCES work demonstrates that Transformer pretraining on synthetic parallel
data materially improves non-English GEC. Synthetic/manual mixing was used to
avoid overfitting scarce supervision.

### MATE 2025

The MATE pipeline introduces errors online during training:

1. language-independent character/token operations;
2. candidate substitutions proposed by Aspell or MorphoDiTa;
3. typical Czech errors mined/defined from annotated data.

Reported typical Czech families include `mě/mně`, capitalization, punctuation,
`i/y`, `s-/z-`, `ú/ů`, `bysme/bychom`, and `dvouma/dvěma`.

Published experimental conclusions:

- combined MATE generators outperform each component alone;
- source corpus cleanliness/size matters; SYN-v4 was best among reported bases;
- careful GECCC domain oversampling improves aggregate performance;
- in the reported best setting, adding synthetic errors during final fine-tuning
  did not help versus manual-only fine-tuning;
- byte-level models outperform corresponding subword models;
- more manual data continues to improve results.

## CzechCore error-generation taxonomy

Generation must map to `research/taxonomy.json`. Minimum generator families:

### Characters and orthography

- insert/delete/substitute/transpose characters;
- keyboard-neighbor substitutions;
- add/remove/move diacritics;
- `i/y`, `ú/ů`, `ě/je`, `mě/mně`, `s/z/vz`, doubled consonants;
- capitalization changes;
- split/join/compound changes.

### Morphology

- same-lemma alternative gender/number/case forms;
- adjective/noun agreement mismatches;
- pronoun/numeral inflection;
- person/number/tense/mood/participle alternatives;
- reflexive/auxiliary insertion/deletion;
- subject-predicate agreement with simple/coordinated subjects.

MorphoDiTa generation should supply valid forms; dependency/context constraints
should determine where a generated form creates the target error family.

### Syntax

- missing/unnecessary/substituted prepositions and conjunctions;
- constrained word-order/clitic perturbation;
- missing/repeated function words;
- punctuation conditioned on clause structure.

### Protected/negative data

- URLs, email, paths, versions, code, dates, currency, names;
- already-correct formal/informal Czech;
- legitimate variants;
- sentences where a tempting correction changes meaning.

Negative data is necessary to learn abstention and reduce false changes.

## Data pipeline requirements

```text
licensed source manifest
    -> normalize encoding only
    -> language/domain/noise inspection
    -> exact deduplication + near-duplicate search
    -> remove/fence dev and test contamination
    -> sentence/token/morphology analysis
    -> seeded online synthetic generator
    -> source/gold/error-family trace
    -> training shards + immutable manifest
```

Each example must retain:

- clean-source corpus/snapshot/document ID;
- generator and parameters;
- random seed/epoch;
- expected taxonomy family;
- original clean target and corrupted input;
- tokenizer/model versions;
- license/provenance ID.

## Curriculum proposal

1. Pretrain compact and teacher candidates on balanced language-independent plus
   Czech-specific synthetic data.
2. Evaluate dev slices after every fixed update interval.
3. Fine-tune on GECCC training only, with domain sampling selected on GECCC dev.
4. Run separate AKCES-domain fine-tuning/profile experiments.
5. Calibrate selective confidence on development predictions.
6. Freeze model, tokenizer, thresholds, and configs.
7. Evaluate once on held-out tests plus correct/adversarial suites.

## Teacher and distillation program

ByT5-large can generate teacher hypotheses/logits for training a smaller runtime,
subject to license and compute constraints. Distillation experiments should test:

- sequence-level teacher targets;
- n-best/reranking distillation;
- token probability/KL distillation;
- error-family balanced sampling;
- preserving unchanged/copy behavior;
- per-edit/selective confidence heads;
- semantic drift and false-change regressions.

A distilled student is acceptable only if its precision/coverage/runtime Pareto
point is better than the current baseline.

## Leakage controls

- Hash and deduplicate all training text against GECCC/AKCES dev/test.
- Treat public benchmark exposure in pretrained LLMs as unknown unless training
  data provenance proves otherwise.
- Never select hyperparameters from test performance.
- Keep model-card published scores separate from local evaluation.
- Record every corpus and transform in the model manifest.

## Reproducibility contract

Training is not reproducible unless the release records:

- code commit and dirty-state check;
- complete config and random seeds;
- data/source hashes and split IDs;
- tokenizer/model initialization revision;
- package/CUDA/hardware versions;
- checkpoint and final artifact hashes;
- dev selection criterion;
- full test and safety report;
- applicable licenses/notices.
