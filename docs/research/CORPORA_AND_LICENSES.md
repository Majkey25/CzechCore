# Corpora, models, and license boundaries

## Policy

Research availability does not imply redistribution or commercial permission.
CzechCore keeps downloaded material in `.reference/research/`, records hashes and
terms in `research/sources.json`, and commits only aggregate statistics and
original synthesis.

## GECCC

| Property | Value |
| --- | --- |
| Primary handle | `11234/1-4639` |
| Model-linked handle | `11234/1-4861` |
| License | CC BY-SA 4.0 |
| Sentences | 83,058 |
| Train / dev / test | 66,673 / 8,478 / 7,907 |
| Domains | Natives Formal, Natives Web Informal, Romani, Second Learners |
| Formats | sentence/paragraph input, gold, M2, metadata |

The `1-4861` archive is linked from the released MATE model cards and differs in
hash/size from the original `1-4639` archive. CzechCore stores both and uses the
model-linked version for aggregate error-type research.

Committed aggregate:

- 57,122 sentences with at least one edit;
- 228,805 edits;
- 65 Czech ERRANT types;
- domain counts: 36,416 Second Learners; 27,338 Romani; 11,608 Natives Web
  Informal; 7,696 Natives Formal.

## AKCES-GEC

| Property | Value |
| --- | --- |
| Handle | `11234/1-3057` |
| License | CC BY-NC-SA 4.0 |
| Formats | M2 train/dev/test with subcorpus variants |
| Purpose | Czech learner GEC, low-resource and AKCES-domain evaluation |

The archive includes original error labels such as agreement, dependency,
incorrect base/inflection, lexical, reflexive, and word-order-related categories.
Its annotation taxonomy is useful but not identical to Czech ERRANT.

## MorphoDiTa / MorfFlex / PDT-C

The locally cached `250909` archive contains:

- full 25.0MB Czech tagger;
- 10.1MB POS-only tagger;
- no-diacritics full/POS variants;
- full, POS-only, and no-diacritics dictionaries supporting analysis/generation.

License: CC BY-NC-SA 4.0 for the model/data archive. MorphoDiTa source is
MPL-2.0. The model archive is a practical candidate for candidate validation,
lemma/tag evidence, inflection generation, and error generation, but it keeps the
default runtime non-commercial unless replaced/licensed.

## MATE model family

All five official model-card snapshots are pinned locally by revision:

| Model | Published parameters | GECCC F0.5 | Runtime role |
| --- | ---: | ---: | --- |
| Transformer-base GECCC | 60.8M | 73.73 | Current compact baseline |
| ByT5-small GECCC | 300M | 72.56 | Dominated by compact baseline in published score/size |
| ByT5-base GECCC | 582M | 75.15 | Quality experiment |
| ByT5-large GECCC | 1.275B | 77.01 | Teacher/high-quality profile |
| ByT5-large AKCES | 1.275B | AKCES 84.40 | AKCES teacher/domain profile |

License: CC BY-NC-SA 4.0. Model repositories contain several framework weight
formats; summed repository bytes are not runtime memory requirements.

## IJP

The official IJP general index currently exposes 22 chapters and 202 general
explanations. CzechCore caches their HTML for research and commits title/ID/URL
metadata only. The project does not assume permission to redistribute page
bodies.

## Training corpora mentioned by MATE

The MATE paper investigates Czech monolingual sources including SYN-v4, News
2019, Wikipedia, and Common Crawl/CoNLL shared-task text. Before any CzechCore
training run, each exact snapshot requires:

- acquisition URL and immutable version;
- license/terms review for training and derived models;
- file and split hashes;
- deduplication against GECCC/AKCES dev/test;
- personal-data and domain review;
- language/noise quality report.

No training source enters the pipeline from a vague label such as “Wikipedia” or
“web corpus.”

## Redistributability matrix

| Resource | Local research | Commit raw data | Commercial default runtime |
| --- | --- | --- | --- |
| ACL/UFAL papers | Yes | No | Not runtime material |
| IJP snapshots | Yes | No | Not runtime material |
| GECCC CC BY-SA | Yes | No in this repo | Training use requires attribution/share-alike review |
| AKCES CC BY-NC-SA | Yes | No | No |
| MorfFlex/PDT-C models CC BY-NC-SA | Yes | No | No |
| MATE weights CC BY-NC-SA | Yes | No | No |
| MIT/MPL/BSD source repos | Yes | No vendoring by default | License-compatible subject to notices |

Commercial support requires a separate data/model decision; changing only the
MIT CzechCore code license is insufficient.
