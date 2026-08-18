# ADR-0002: Default to suggestions and conservative abstention

## Status

Accepted

## Date

2026-08-18

## Context

False automatic corrections damage user trust and can change meaning. Neural GEC
scores rank hypotheses but do not prove grammatical correctness. The requested
product needs both underlines and an optional autocorrect mode.

## Decision

- Return structured suggestions by default without changing `output_text`.
- Keep autocorrect opt-in.
- Include the unchanged sentence in the candidate set.
- Reject low-confidence, over-broad, over-length, or protected-content-changing
  candidates.
- Apply all accepted edits from one sentence atomically.

## Alternatives considered

### Always apply the top beam

Rejected. Beam rank alone does not prevent false changes or semantic rewrites.

### Never support autocorrect

Rejected. High-confidence automatic application is a required optional feature.

### Per-edit application inside one generated sentence

Rejected. Edit confidences are inherited from one sentence hypothesis; applying
only a subset can create text the model never scored.

## Consequences

- Precision is preferred over recall.
- Protected technical text can cause a whole sentence to remain unchanged.
- Default autocorrect may apply very few neural corrections until calibration.
- Platform UI must distinguish suggestion from applied output.
- Confidence documentation must say “relative beam confidence,” never empirical
  probability of correctness.
