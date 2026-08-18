# ADR-0001: Use the compact UFAL Transformer as the default baseline

## Status

Accepted

## Date

2026-08-18

## Context

CzechCore needs sentence-level Czech GEC, offline inference, and a credible path
to Windows and Android. Hand-written rules do not provide broad contextual
coverage. Published UFAL models offer several accuracy/size points.

## Decision

Use pinned `ufal/transformer-base-geccc-mate` as the default Python baseline and
load its WordPiece tokenizer explicitly.

## Alternatives considered

### Build a rule engine first

Rejected. Czech agreement, punctuation, lexical ambiguity, and morphology interact
across the sentence. A rule DSL would be large before matching the available
learned baseline and would create a second linguistic source of truth.

### ByT5-small

Rejected as default. The model card reports 300M parameters and GECCC F0.5 72.56,
versus approximately 60.8M and 73.73 for the selected Transformer.

### ByT5-base or ByT5-large

Deferred to teacher or quality-profile experiments. Their published score is
higher, but 582M/1.275B parameters are poor defaults for target devices.

### General-purpose local LLM

Rejected for the first baseline. It increases size, latency, nondeterminism, and
semantic rewrite risk without a Czech GEC evaluation advantage established here.

## Consequences

- Runtime uses Python/PyTorch today; portable export remains required for devices.
- Input must match the model's UDPipe tokenization.
- The tokenizer metadata mismatch is guarded by a runtime WordPiece assertion.
- Quality inherits the model/data domain and non-commercial asset license.
- Larger or distilled models can replace the backend without changing public edit
  types.
