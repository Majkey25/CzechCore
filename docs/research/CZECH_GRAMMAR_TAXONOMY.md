# Czech grammar and correction taxonomy

## Purpose

This document defines the correction problem CzechCore intends to measure. It is
not a claim that every listed phenomenon is already solved.

The machine-readable source of truth is [`research/taxonomy.json`](../../research/taxonomy.json).
It is validated against:

- all 22 chapters and 202 general explanations in the official
  [Internetová jazyková příručka](https://prirucka.ujc.cas.cz/pda);
- all 65 Czech ERRANT types observed in GECCC handle `11234/1-4861`;
- source provenance in [`research/sources.json`](../../research/sources.json).

Validation command:

```powershell
.venv\Scripts\python -m tools.research.validate_taxonomy
```

Current invariant:

```json
{"families":13,"geccc_error_types":65,"ijc_rules":202,"ijc_sections":22,"phenomena":101}
```

## Evidence systems

### IJP

The IJP explains normative and variant Czech orthography, morphology, syntax,
punctuation, names, numbers, and document typography. CzechCore downloaded and
hash-manifested all 202 general explanations as research references. Metadata is
committed in [`research/ijc-outline.json`](../../research/ijc-outline.json); page
bodies remain outside Git.

### GECCC / Czech ERRANT

GECCC provides real annotated corrections rather than only normative chapters.
Czech ERRANT labels each edit with an operation and category:

- `R:` replacement;
- `M:` missing material in the source;
- `U:` unnecessary material in the source.

The committed aggregate contains 83,058 sentences, 57,122 sentences with edits,
228,805 edits, four domains, and all 65 observed types. See
[`research/geccc-error-types.json`](../../research/geccc-error-types.json).

The most frequent types are:

| Type | Edits | Interpretation |
| --- | ---: | --- |
| `R:DIACR` | 48,337 | Diacritics replacement |
| `M:PUNCT` | 36,114 | Missing punctuation |
| `R:SPELL` | 26,193 | Spelling replacement |
| `R:OTHER` | 24,298 | Replacement not classified more narrowly |
| `R:ORTH:CASING` | 11,815 | Casing replacement |
| `U:PUNCT` | 7,856 | Unnecessary punctuation |
| `R:MORPH` | 7,722 | Derivational/other morphology |
| `R:VERB` | 7,421 | Verb replacement |
| `R:NOUN:INFL` | 5,660 | Noun inflection |
| `R:WO` | 4,358 | Word order |

Frequency is not difficulty and not product priority by itself. Low-frequency
errors can be severe, while high-frequency diacritics may be easier.

## Taxonomy families

| Family | IJP chapters | GECCC types | Phenomena | Current baseline |
| --- | ---: | ---: | ---: | --- |
| Orthography | 3 | 3 | 14 | Partial |
| Punctuation | 1 | 5 | 16 | Partial |
| Capitalization | 1 | 1 | 8 | Partial |
| Word formation | 3 | 1 | 7 | Unmeasured |
| Nouns/proper names | 5 | 8 | 9 | Partial |
| Adjectives/adverbs | 1 | 8 | 5 | Partial |
| Pronouns/determiners | 1 | 7 | 5 | Partial |
| Numerals | 2 | 4 | 7 | Partial/guarded |
| Verbs/auxiliaries | 1 | 8 | 8 | Partial |
| Syntax/government | 1 | 14 | 10 | Partial |
| Particles/interjections | 0 | 6 | 3 | Unmeasured |
| Documents/typography | 1 | 0 | 7 | Guarded |
| Normative framework | 2 | 0 | 2 | Reference only |

Every correction family requires positive, negative, and ambiguity evidence.
Reference-only material records how correctness decisions are justified.

## 1. Orthography

In scope:

- sound/grapheme relations and pronunciation-driven confusions;
- `i/í` versus `y/ý`, listed words, and forms derived from *být/bít*;
- `ě`, `ú/ů`, `n/nn`, `s-/z-`, and `s/z` prepositions;
- Czech adaptation of loanwords and foreign proper names;
- fused/split expressions and compound adjectives;
- voicing assimilation and omitted/inserted sounds;
- Cyrillic transcription/transliteration.

Primary IJP IDs include `100`, `101`, `103`, `110`, `111`, `120`-`127`,
`130`, `140`, `149`, `901`, `907`-`912`, and `920`-`926`.

Required ambiguity guards include valid homographs (`Bili psa.` / `Byli doma.`),
names, loanwords, technical terms, and style variants. Line-end hyphenation is
classified but remains outside the sentence engine.

## 2. Punctuation

In scope:

- complex- and simple-sentence commas;
- infinitive constructions;
- conjunction-specific comma behavior (`a/i/ani`, `jako/než`, `nebo/či`,
  explanatory conjunctions);
- sentence-final period, question mark, and exclamation mark;
- colon, semicolon, quotation marks, brackets, hyphen, dash, ellipsis, slash,
  apostrophe, and spacing.

IJP IDs `150`-`173` define the authoritative surface. Missing punctuation is the
second most frequent GECCC error family, but false comma insertion is a major
trust risk. Tests must include structurally similar sentences where a comma is
correct and where it is not.

## 3. Capitalization

The family covers sentence casing plus proper-name classes:

- people, beings, titles, and derived adjectives;
- astronomical and geographical names;
- settlements, streets, structures, and stops;
- organizations and organizational units;
- documents, works, events, holidays, competitions;
- products, varieties, breeds, awards, and substitute names.

IJP IDs `180`-`196` show why capitalization cannot be reduced to “first token of
sentence”: the same lexical item can be common or proper by meaning and use.

## 4. Morphematics and word formation

The family covers morpheme boundaries, sound alternations in derivation,
demonyms, family-name forms, adjective suffixes, variant suffixes, preposition
vocalization, and feminization of surnames/common nouns.

GECCC `R:MORPH` has 7,722 edits, but its label is intentionally broad. Research
must distinguish derivation from inflection and lexical substitution before
producing user explanations.

## 5. Nouns and proper names

In scope:

- gender, animacy, grammatical number;
- common-noun case and paradigm selection;
- vocative;
- declension of personal, geographic, institution, and company names;
- multiword and plural proper names;
- appositional constructions such as *ve městě Olomouc*.

This family maps noun/proper-noun replacement, inflection, insertion, and deletion
types. A valid correction often depends on case government from another word, so
isolated dictionary validity is insufficient.

## 6. Adjectives and adverbs

In scope: possessive forms, comparison, nominal/compound adjective competition,
inflection/agreement, and lexical adjective/adverb choice. Agreement must be
tested across gender, animacy, number, and case, including correct alternatives.

## 7. Pronouns and determiners

In scope:

- `mě/mně` and other forms of *já*;
- possessive pronoun competition;
- reflexive forms;
- pronoun case/inflection;
- missing, unnecessary, or substituted pronouns/determiners.

The same pronounced form can require different spelling by case. This is a
sentence-level morphology/government problem, not a character substitution rule.

## 8. Numerals and structured numbers

In scope: forms of *dva/oba/tři/čtyři*, numeral-government of counted nouns,
grouping and decimals, numeric compounds, Roman numerals, decades/centuries,
currency, and symbols.

Dates, versions, currency, phone numbers, and code-like numeric strings need
protection-first negative tests before any neural normalization.

## 9. Verbs and auxiliaries

In scope:

- conjugation paradigms and variants;
- active/passive participles;
- imperative and conditional (`byste`, `abyste`, `kdybyste`, `jako by`);
- reflexive/non-reflexive verbs;
- transgressives;
- tense, person, number;
- missing/unnecessary auxiliaries.

The category overlaps syntax through agreement and valency. Taxonomy ownership is
by changed head token; evaluation reports both family and contextual dependencies.

## 10. Syntax, agreement, and government

In scope:

- simple, coordinated, and complex subject-predicate agreement;
- postposed-attribute agreement;
- nominative/instrumental competition in nominal predicates;
- verb/noun valency and case government;
- preposition choice;
- coordination and subordination;
- word order and clitic placement;
- broad `OTHER` replacements/insertions/deletions requiring manual analysis.

The current acceptance miss `Petr a Jana šla domů.` belongs to coordinated
agreement (IJP `601`). It remains an explicit training/evaluation gap, not a
name-specific code rule.

## 11. Particles and interjections

GECCC distinguishes replacement, insertion, and deletion for both parts of
speech. Their correctness often depends on discourse/pragmatics beyond one
sentence. The baseline is unmeasured and should abstain aggressively.

## 12. Documents and typography

In scope/reference: addresses, dates, time, phone numbers, letter structure,
salutations, signatures, lists, line breaks, bibliography, and sorting.

These surfaces are frequently structured data rather than ordinary prose. The
baseline treats them as guarded and avoids destructive normalization. Some tasks,
such as bibliography formatting and alphabetical sorting, are explicitly outside
sentence correction.

## 13. Normative framework

IJP chapters `890` and `990` describe codification, norm, usage, reference works,
terminology, and literature. They do not define runtime correction categories;
they govern how examples and judgments are justified.

## Coverage states

- `supported`: verified across positive, negative, ambiguity, and regression data;
- `partial`: observed successful behavior but incomplete family evidence;
- `guarded`: protected/abstained rather than corrected;
- `unmeasured`: researched but not sufficiently evaluated;
- `out_of_scope`: recorded to prevent accidental claims.

No family graduates to `supported` from a single example or aggregate score.
