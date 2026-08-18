# CzechCore documentation

This directory is the maintained source of truth for behavior, evidence, and
decisions. The root README is the quick start, not the complete specification.

## Documents

| Document | Maintains |
| --- | --- |
| [Scientific basis](SCIENTIFIC_BASIS.md) | Linguistic scope, model theory, published evidence |
| [Evaluation](EVALUATION.md) | Metrics, benchmark protocol, current measurements |
| [API](API.md) | Python and CLI contracts |
| [Architecture](ARCHITECTURE.md) | Runtime flow, modules, assets, trust boundaries |
| [Development](DEVELOPMENT.md) | Local setup, quality gates, release procedure |
| [Roadmap](ROADMAP.md) | Evidence-gated future work |
| [Research program](research/README.md) | Full Czech taxonomy, literature, data, models, training, evaluation |
| [Decisions](decisions/README.md) | Accepted ADRs and their consequences |

## Evidence labels

Every quantitative or capability claim belongs to one of these classes:

- **Published:** reported by an external paper, model card, dataset paper, or
  authoritative language reference. It must include a direct citation.
- **Measured:** produced by a committed command on named hardware and dated.
  It must state the dataset and must not be generalized beyond it.
- **Planned:** not implemented. It belongs in the roadmap, never in feature or
  performance lists.

## Update policy

| Change | Documentation that must change |
| --- | --- |
| Public Python/CLI behavior | `API.md`, README example, tests, changelog |
| Model, tokenizer, scoring, or safety policy | `SCIENTIFIC_BASIS.md`, `ARCHITECTURE.md`, ADR, benchmark |
| Benchmark cases or metric definitions | `EVALUATION.md`, measured README summary |
| Dependency or asset license | `NOTICE.md`, README license section, relevant ADR |
| Release | `CHANGELOG.md`, `CITATION.cff`, package version, tag, GitHub release |
| Roadmap completion | Move the item into changelog/docs only after verification |

Documentation changes are reviewed by the same correctness standard as code.
Stale measured numbers are bugs.
