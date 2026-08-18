# CzechCore research program

## Outcome

CzechCore becomes a long-term research and engineering project for offline Czech
grammatical error correction, not a thin model wrapper. The repository will
contain:

- an authoritative, versioned taxonomy of Czech correction phenomena;
- a locally reproducible corpus of primary papers, model cards, language rules,
  corpus documentation, and evaluation tools;
- scientific Markdown syntheses that distinguish published, measured, and
  planned claims;
- a machine-readable coverage matrix linking every phenomenon to sources,
  datasets, runtime support, positive tests, negative tests, and measured gaps;
- reproducible standard-corpus and adversarial evaluation;
- model/data/training improvements selected from evidence;
- portable runtime and platform integrations only after engine quality gates.

No finite system can prove that it corrects every possible Czech sentence. In
this project, “complete” means every in-scope phenomenon is explicitly researched,
classified, evaluated, and either supported or recorded as an open measured gap.

## Actors

- Czech writers receiving underlines, explanations, and optional corrections.
- Engine developers improving inference, safety, and structured edits.
- Linguists reviewing taxonomy, examples, and expected corrections.
- ML researchers evaluating corpora, training strategies, and calibration.
- Windows/Android adapter developers consuming the stable correction API.
- Future agents needing durable evidence instead of rediscovering decisions.

## Must-have behavior

### Research corpus

- Primary sources are downloaded to `.reference/research/`.
- Every local source has URL, title, authors/owner, publication date, license or
  access note, SHA-256, local path, and research purpose.
- Copyrighted papers/data are never committed unless redistribution is verified.
- Committed Markdown contains synthesis and short compliant quotations only.

### Czech taxonomy

The taxonomy covers at minimum:

1. Unicode, normalization, characters, and diacritics.
2. Tokenization, word boundaries, hyphenation, compounds, abbreviations, URLs,
   email, code, numbers, dates, currency, and typography.
3. Lexical spelling, `i/y`, listed words, `ú/ů`, `ě`, `mě/mně`, `s/z/vz`,
   consonant length, assimilation, doubled consonants, and loanwords.
4. Inflectional morphology: gender, animacy, number, case, person, tense, mood,
   participles, declension, conjugation, pronouns, numerals, adjectives, and
   possessives.
5. Agreement: subject-predicate, coordinated subjects, adjective-noun, pronoun,
   numeral, participle, and predicative complement.
6. Government and valency: prepositions, cases, verb arguments, reflexives,
   auxiliary and clitic forms.
7. Syntax and word order: clause structure, coordination, subordination, clitic
   placement, negation, repeated/missing words, and split/join errors.
8. Punctuation: simple sentence, complex sentence, conjunction-specific commas,
   parentheticals, direct speech, quotations, colon, semicolon, dash, ellipsis,
   brackets, and sentence-final marks.
9. Capitalization, proper names, abbreviations, titles, addresses, and foreign
   expressions.
10. Style/register risks and semantic ambiguity where automatic correction should
    abstain.

### Evaluation

- Each phenomenon has positive, negative, ambiguity, and regression evidence when
  linguistically meaningful.
- Correct Czech has first-class false-positive coverage.
- Standard metrics include edit precision, recall, F0.5, sentence exact match,
  false-change rate, wrong-rewrite rate, latency, memory, and startup.
- Confidence thresholds are calibrated on development data and frozen before test
  evaluation.
- Results are sliced by domain and error category.

### Engineering

- No benchmark sentence is hardcoded in production.
- Semantic correction remains model/data driven.
- Mechanical deterministic logic is allowed only when its boundary is explicit
  and backed by negative tests.
- The unchanged sentence remains a candidate.
- Suggestions are default; autocorrect remains explicit and precision-first.
- User text remains local.

## Non-goals

- Redistributing papers/corpora without verified permission.
- Calling a small curated suite a complete Czech evaluation.
- Claiming 100% correctness or calibrated probability without evidence.
- Adding hundreds of fragile regex grammar rules.
- Starting Windows/Android UI work before the engine evaluation and portable
  runtime gates are met.
- Treating non-commercial model assets as commercially usable.

## Constraints

- Production code: Python 3.12-3.14, Ruff, strict Pyright, pytest.
- Runtime inference: offline after explicit asset provisioning.
- Default code license: MIT; model/data licenses remain separate.
- Research cache: `.reference/research/`, ignored by Git.
- Committed research: `docs/research/` plus machine-readable metadata under
  `research/`.
- Primary technical evidence: papers, official model/dataset cards, official
  documentation, and authoritative Czech language sources.
- No cloud LLM is required at runtime.

## Risks

| Risk | Control |
| --- | --- |
| Czech has legitimate variants and ambiguous corrections | Multiple references, abstention, ambiguity labels, human review |
| Corpus/domain bias | Domain-sliced evaluation and correct-text guards |
| Data leakage between training and testing | Dataset provenance and split manifest |
| Confidence overclaim | Calibration protocol and reliability reporting |
| License contamination | Separate cache, manifest, NOTICE/ADR updates |
| Large teacher models are unusable on devices | Distillation/quantization evaluated against quality and memory |
| Taxonomy becomes prose only | Machine-readable coverage matrix and CI validation |
| Research context goes stale | Source versions, hashes, update dates, and changelog |
| “Fix every rule” becomes endless scope | Explicit coverage states and evidence-based done gates |

## Execution slices

### Slice 1: Research corpus and manifest

- Surface: `.reference/research/`, `research/sources.json`, research tooling.
- Validation: source exists, MIME/format matches, SHA-256 matches manifest, URL and
  license/access fields are non-empty.
- Completion: primary source set is locally reproducible and license-safe.

### Slice 2: Czech grammar/error taxonomy

- Surface: `research/taxonomy.json`, `docs/research/CZECH_GRAMMAR_TAXONOMY.md`.
- Validation: stable IDs, parent relationships, authoritative citations, no
  duplicate IDs, every leaf has evaluation requirements.
- Completion: all in-scope families are enumerated and reviewable.

### Slice 3: GEC/model/data/evaluation synthesis

- Surface: scientific Markdown documents and ADRs.
- Validation: every quantitative claim cites a primary source or a reproducible
  local command; published and measured results are separated.
- Completion: architecture/training/evaluation decisions are evidence-backed.

### Slice 4: Coverage matrix and benchmark expansion

- Surface: `research/coverage.json`, benchmark JSONL files, validators.
- Validation: every taxonomy leaf maps to tests or an explicit measured gap;
  positive and negative examples validate schema and references.
- Completion: coverage is machine queryable and CI-enforced.

### Slice 5: Standard evaluation

- Surface: dataset adapters, evaluation commands, reports.
- Validation: frozen splits, hashes, versioned configuration, deterministic
  inference, edit and sentence metrics.
- Completion: CzechCore has a standard corpus baseline, not only acceptance cases.

### Slice 6: Model/data improvement

- Surface: training/error generation/distillation pipeline and model manifests.
- Validation: held-out improvement, no false-positive regression, reproducible
  artifact hashes, license review.
- Completion: a candidate replaces the baseline only when defined gates pass.

### Slice 7: Portable runtime and adapters

- Surface: exported model, quantization, C/C++/mobile runtime, Windows/Android
  adapters.
- Validation: output parity, device latency/memory, UTF-16 offsets, real app flows.
- Completion: system integrations consume the same tested correction contract.

## Done criteria

- [x] Research source manifest verifies every downloaded primary source.
- [x] Taxonomy has stable IDs and no unclassified in-scope family.
- [x] Every taxonomy leaf has support status and evaluation mapping.
- [x] Coverage matrix reports evidence and gaps for all 101 taxonomy leaves.
- [x] Scientific documents cover grammar, GEC literature, corpora, models,
  training, confidence, evaluation, licensing, and deployment.
- [ ] Standard Czech corpus evaluation is reproducible.
- [ ] Correct-text false-positive and adversarial suites are versioned.
- [ ] Autocorrect threshold is empirically calibrated for a stated precision goal.
- [ ] Remaining failures are categorized and linked to research/training work.
- [ ] Improved model/runtime passes accuracy, safety, latency, memory, and license
  gates.
- [ ] Public documentation and release evidence match the exact shipped commit.
