# CzechCore documentation

This directory is the maintained source of truth for behavior, evidence, and
decisions. The root README is the quick start, not the complete specification.

## Documents

| Document | Maintains |
| --- | --- |
| [Install by device](GETTING_STARTED.md) | Release install, model provisioning, verification, update, removal, and device routing |
| [Windows setup](setup/WINDOWS.md) | PowerShell/venv installation and physical/hosted Windows verification |
| [macOS setup](setup/MACOS.md) | Apple Silicon/Intel installation and hosted macOS evidence |
| [Linux setup](setup/LINUX.md) | Ubuntu/general Linux installation and hosted Linux evidence |
| [Android status](setup/ANDROID.md) | Missing APK/runtime boundary and required emulator/device gate |
| [Android source probe](../android/README.md) | Reproducible CTranslate2 conversion, NDK build, APK, ADB provisioning, and emulator flow |
| [Research report](RESEARCH_REPORT.md) | Executive scientific result, methods, measurements, interpretation, release verdict |
| [Scientific basis](SCIENTIFIC_BASIS.md) | Linguistic scope, model theory, published evidence |
| [Evaluation](EVALUATION.md) | Metrics, benchmark protocol, current measurements |
| [API](API.md) | Python and CLI contracts |
| [Architecture](ARCHITECTURE.md) | Runtime flow, modules, assets, trust boundaries |
| [Platform integration](PLATFORM_INTEGRATION.md) | Windows/Android UX, runtime boundary, privacy, performance, acceptance gates |
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
| Release | `CHANGELOG.md`, `CITATION.cff`, research report, package version, tag, GitHub release |
| Roadmap completion | Move the item into changelog/docs only after verification |

Documentation changes are reviewed by the same correctness standard as code.
Stale measured numbers are bugs.
