# Hybrid local semantic rewrite architecture

## Required behavior

CzechCore has two distinct local modes:

| Mode | Output | Default interaction |
| --- | --- | --- |
| `proofread` | Minimal spelling, morphology, syntax, punctuation, and typography edits | Underlines and optional confidence-gated autocorrect |
| `rewrite` | Clear, grammatical Czech that may reorder or replace whole phrases while preserving meaning | Whole-sentence alternative requiring explicit acceptance |

The modes must not share one silent application policy. A broad rewrite cannot be
reliably decomposed into independently safe autocorrections.

## User acceptance example

Input:

```text
jako jo je to prakticky nejpouzivanejsi nastroj na sirsi obsah nez co ma pip a hodne na ai zamereny
```

Accepted rewrite:

```text
Jako jo, je to prakticky nejpoužívanější nástroj, má širší záběr než pip a je hodně zaměřený na AI.
```

This requires diacritics, punctuation, clause reconstruction, removal of an
ungrammatical comparison, and preserved claims about adoption, scope, `pip`, and
AI orientation. The compact GEC model alone is not designed for this edit scale.

## Candidate pipeline

```text
source text
  -> Unicode/sentence/paragraph analysis
  -> conservative proofread candidate for fallback
  -> high-recall Czech GEC candidate used only as LLM context
  -> local instruction LLM rewrite candidates
  -> protected-literal and structural invariants
  -> local semantic-equivalence scorer
  -> Czech morphology/syntax/GEC post-check
  -> mode-aware ranker with unchanged fallback
  -> structured proofread edits + optional whole-sentence rewrite
```

The local LLM supplies semantic reconstruction. It does not bypass the specialized
Czech model. The GEC model supplies high-precision Czech corrections and post-checks;
UDPipe/MorphoDiTa supply token, lemma, morphology, dependency, and entity-adjacent
evidence. A semantic scorer rejects meaning drift. Every stage runs on-device after
explicit asset provisioning.

Explicit caller-protected names are masked with synthetic URL tokens during the
high-recall GEC pass, then restored before LLM inference. If the marker is changed,
the context falls back to the conservative proofread. The aggressive context is
never itself returned as a fallback.

## Rewrite invariants

Automatic checks reject or downgrade candidates that unexpectedly change:

- URLs, email, paths, versions, code, identifiers, phone numbers, dates, amounts,
  units, and quoted literals;
- named entities and product/tool names;
- numbers, polarity/negation, modality, conditionals, uncertainty, tense, person,
  or grammatical gender where they carry meaning;
- list cardinality or causal/temporal relations;
- unresolved referents by inventing a specific interpretation.

Embedding similarity alone is insufficient: antonyms and negation can remain close
in embedding space. The semantic gate therefore combines exact invariants,
token/morphology evidence, multilingual NLI or a trained equivalence classifier,
and human-reviewed threshold calibration.

## Candidate selection

The ranker always compares at least:

1. unchanged source;
2. compact GEC proofread candidate;
3. one or more deterministic local-LLM rewrites;
4. GEC-postchecked versions of accepted rewrites.

`proofread` penalizes edit distance strongly and never selects a broad rewrite.
`rewrite` permits broad edits but requires semantic equivalence and explicit user
acceptance. Generation is deterministic for evaluation (`temperature=0`, fixed
model/runtime revision, bounded output). Invalid format, empty output, commentary,
or repeated prompt text is rejected.

## Local model profiles to evaluate

| Profile | Initial candidates | Purpose |
| --- | --- | --- |
| Mobile | Qwen3 0.6B Q4; Qwen3.5 0.8B Q4 | Feasibility floor around 0.4-0.7GB weights |
| Balanced | Qwen3 1.7B/4B; Qwen3.5 2B/4B Q4 | Windows and capable Android quality/runtime trade-off |
| Teacher | Aya Expanse 8B; larger Qwen/Gemma comparison | Offline reference and distillation only |

Qwen candidates are Apache-2.0. Aya explicitly supports Czech but is CC-BY-NC and
therefore cannot silently become a commercial default. Gemma requires acceptance
of separate usage terms. Model-card multilingual claims are only eligibility
signals; the Czech rewrite benchmark decides selection. BenCzechMark
(`paper-benczechmark-2024`) supports evaluating open-weight models on native Czech
tasks, but it does not contain an open-ended rewrite task and therefore cannot
replace this project's meaning-preservation suite.

## Training direction

If prompting is insufficient, create a Czech rewrite student with:

- licensed noisy/colloquial Czech sources;
- multiple human rewrites preserving facts and register;
- hard negatives that alter negation, entities, numbers, modality, or referents;
- teacher candidates filtered and human adjudicated;
- joint objectives for rewrite generation, semantic equivalence, and abstention;
- GEC and already-correct examples mixed in to suppress gratuitous rewriting;
- held-out authors/domains and deduplication against all test material.

Distillation is accepted only when the student matches or improves the approved
quality/safety/runtime Pareto point. Synthetic volume is not a substitute for
human semantic labels.

## Evaluation gates

- exact/multiple-reference acceptance where references exist;
- Czech grammaticality and readability human scores;
- meaning preservation, necessity, and register labels;
- protected invariant pass rate;
- negation/entity/number/modality adversarial accuracy;
- false rewrite rate on already-clear Czech;
- deterministic repeatability;
- latency, peak RAM, model size, and battery/device thermals;
- separate Windows CPU and real Android arm64 measurements.

No rewrite model is production-ready until it passes all safety slices. A fluent
sentence with changed meaning is a failure, even when a generic LLM judge prefers
its style.

## First local screen: 2026-08-18

Pinned llama.cpp `b10486` ran deterministic CPU inference on the user acceptance
example. Both Apache-2.0 Qwen3 GGUF candidates failed:

| Candidate | Weight file | Verdict |
| --- | ---: | --- |
| Qwen3 0.6B Q4_0 | 409 MB | Lost `pip`, inconsistent diacritics, ungrammatical meaning damage |
| Qwen3 4B Q4_K_M | 2.33 GiB | Changed `pip` to `PIP`, invented `SIRS`, changed the adoption claim |
| Qwen3.5 4B Q4_K_M | 2.55 GiB | Changed `pip`, misread `širší`, changed the adoption claim |
| Aya Expanse 8B Q4_K_M | 4.71 GiB | Best Czech output; 4/12 exact, 2 invariant fallbacks, user example still failed |

The hybrid API's explicit `pip` invariant rejects both raw outputs instead of
applying them. Exact outputs, hashes, runtime revision, and rejection reasons are
recorded in `research/evaluations/rewrite-model-screen-2026-08-18.json`. The next
Aya is retained only as the strongest screened teacher candidate. No model passes
the default gate; the next step is task-specific fine-tuning/distillation with
human semantic labels and multiple valid references.
