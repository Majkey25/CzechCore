# ADR-0004: Separate minimal proofread from semantic rewrite

## Status

Accepted

## Date

2026-08-18

## Context

Minimal grammatical correction and meaning-preserving sentence reconstruction are
different tasks. The compact Czech GEC model is strong at localized edits but does
not reliably reconstruct colloquial or disordered sentences. A general local LLM
can reconstruct them, but may silently change facts, negation, names, numbers, or
intent.

## Decision

- Keep `CzechCore.correct` as the minimal `proofread` path with structured edits.
- Add a separate `HybridRewriter` path combining proofread, a loopback-only local
  LLM, mechanical invariants, and Czech post-checking.
- Return rewrite as a whole-sentence suggestion with `requires_review=True`.
- Never apply a broad rewrite through autocorrect.
- Fall back to proofread/source when protected literals, numbers, or structure
  fail validation.
- Accept no default rewrite model until Czech semantic and device gates pass.

## Alternatives considered

### Replace the Czech GEC model with one general LLM

Rejected. Initial 0.6B and 4B screens damaged Czech and meaning; general models
also cost more memory/latency for simple spelling and punctuation edits.

### Feed LLM output directly to autocorrect

Rejected. Fluency does not prove semantic equivalence or necessity.

### Keep rewrite outside the engine

Rejected. It would duplicate protection, post-check, privacy, and result contracts
in Windows and Android adapters.

## Consequences

- Device profiles may provision two models or a future distilled multitask model.
- Rewrite latency and memory are higher than proofread.
- The local model server receives user text and must be trusted; remote endpoints
  and redirects are prohibited.
- Whole-sentence rewrite needs separate evaluation, UI, and acceptance controls.
- A future semantic-equivalence model can strengthen the gate without changing
  the public separation between modes.
