# Roadmap

This is an evidence-gated roadmap, not a promise of dates or completed features.

## `v0.1` — engine baseline

- [x] Offline Czech Transformer inference
- [x] Exact source edits and sentence ranges
- [x] Suggestion-first policy and opt-in autocorrect
- [x] Protected technical literals and rewrite-ratio abstention
- [x] CLI, benchmark, tests, strict typing, CI, documentation
- [x] Public wheel release

## Priority 0 — linguistic evidence and confidence

- [x] Establish a hash/revision/license manifest for primary research sources.
- [x] Download and validate 17 primary PDFs, 202 IJP explanations, seven source
  repositories, GECCC/AKCES, MATE model cards, current MorphoDiTa models, and
  pinned local inference artifacts.
- [x] Map all 22 IJP chapters and 65 GECCC error types into a validated
  13-family/101-phenomenon taxonomy.
- [x] Run full GECCC development/M2Scorer/ERRANT evaluation with a licensed,
  reproducible setup.
- [x] Report edit precision, recall, F0.5, domain slices, and error-type slices.
- [ ] Freeze policy and run the untouched GECCC test split.
- [ ] Calibrate autocorrect confidence on development data for a stated precision
  target; freeze before testing.
- [ ] Improve coordinated-subject agreement through training/data or a verified
  morphological generation path, not sentence-specific rules.
- [ ] Add adversarial false-positive suites for correct Czech, names, technical
  prose, and ambiguous homographs.

Exit criterion: a documented evaluation materially stronger than the 65-case
acceptance set, with no regression in correct-sentence false changes.

## Priority 1 — hybrid semantic rewrite

- [x] Specify distinct `proofread` and explicit whole-sentence `rewrite` modes.
- [x] Add the first meaning/invariant rewrite benchmark from real user acceptance.
- [x] Screen Qwen3 0.6B/4B, Qwen3.5 4B, and Czech-explicit Aya Expanse 8B;
  reject all as defaults and retain Aya only as the strongest teacher candidate.
- [ ] Train/distill a Czech rewrite student if prompting does not pass the gates.
- [ ] Add whole-sentence rewrite API only after meaning-preservation validation.

Exit criterion: useful Czech reconstruction with protected facts, negation,
numbers, modality, and ambiguity preserved; unsafe outputs fall back to proofread.

## Priority 2 — portable runtime

- [ ] Export encoder/decoder generation to a verified portable format.
- [ ] Quantize with measured accuracy, latency, startup, and memory deltas.
- [ ] Produce a model manifest with hashes, licenses, tokenizer revision, and
  benchmark results.
- [ ] Test CPU profiles representative of Windows laptops and Android devices.

Exit criterion: a reproducible artifact that matches Python outputs within an
approved tolerance and fits measured device budgets.

## Priority 3 — operating-system adapters

- [ ] Windows Spell Checking API provider for underlines and suggestions.
- [ ] Android `SpellCheckerService` for platform consumers.
- [ ] UTF-16/code-point offset conversion with emoji regression tests.
- [ ] Explicit optional autocorrect UI; never enabled silently.

Exit criterion: real application/device flows preserve text, offsets, privacy,
and engine benchmark behavior.

## Priority 4 — personalization

- [ ] Local user dictionary with bounded storage and expiry policy.
- [ ] Accepted/rejected suggestion feedback without uploading text.
- [ ] Measured personalization benefit and false-positive guardrails.

Exit criterion: opt-in local adaptation with deletion controls and no unbounded
state.

## Explicit non-goals until evidence changes

- Cloud inference or mandatory accounts
- Hardcoded answers for benchmark sentences
- Regex keyword lists for semantic grammar decisions
- Claiming universal or perfect Czech correction
- Commercial use of the default non-commercial assets
