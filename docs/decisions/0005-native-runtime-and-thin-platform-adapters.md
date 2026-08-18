# ADR-0005: Use one portable runtime and thin platform adapters

## Status

Accepted

## Date

2026-08-18

## Context

CzechCore must support underlines, explicit suggestions, optional automatic
application, and whole-sentence rewrite on Windows and Android. Reimplementing
tokenization, correction policy, invariants, and edit alignment in each adapter
would create divergent Czech behavior. Embedding the current Python/PyTorch stack
inside every target process would increase package size, startup time, memory,
and host crash impact.

Android text services and Windows TSF also have different lifecycle and offset
contracts. Both commonly expose UTF-16 positions while the current engine returns
Unicode-code-point offsets.

## Decision

- Keep Python as the reference/training/evaluation implementation.
- Export a portable native inference runtime only after reference parity.
- Define one versioned UTF-8 request/response contract with explicit
  Unicode-scalar offsets and a model manifest ID.
- Keep correction policy, protected-literal checks, and edit alignment inside the
  shared runtime.
- Make Android services/IME and the Windows TSF service thin scheduling,
  offset-conversion, privacy, and UI adapters.
- Use one per-user out-of-process engine on Windows; the TSF DLL must not load a
  model in every host.
- Use one native runtime instance in the Android service/IME process.
- Discard stale results by document revision before displaying or applying them.
- Keep rewrite explicit and review-only on every platform.

## Alternatives considered

### Keep Python as the production cross-platform runtime

Rejected. It is suitable for research and a Windows prototype, but mobile
packaging and process startup would be unnecessarily heavy and would not create a
clean shared Android/Windows deployment contract.

### Implement separate Kotlin and C++ engines

Rejected. Linguistic policy, safety fixes, and offsets would drift.

### Load the native model directly into every Windows application

Rejected. TSF code runs in host processes. Per-host model loading duplicates
memory and broadens the failure surface.

### Run all correction through a generic GGUF instruction model

Rejected. The screened 0.6B–8B local models were slower/larger than the compact
GEC model and changed protected content or meaning. A local LLM remains useful
only for explicit rewrite or as a teacher.

### Use Android accessibility and a Windows global keyboard hook

Rejected. Both are overly privileged, expose weak text-range semantics, and
cannot reliably provide native underlines or safe atomic edits.

## Consequences

- Portable model export, tokenizer parity, decoder generation, quantization, and
  native error handling become explicit deployment work.
- Platform UI can evolve without changing Czech correction behavior.
- All offset conversions need shared adversarial Unicode fixtures.
- Windows gains a broker process and authenticated local IPC.
- Android automatic application requires an IME; `SpellCheckerService` alone is
  not universal.
- A mature offline keyboard should be extended instead of implementing one from
  scratch, with its license kept in a separate application distribution.
- No platform binary ships until real application/device, latency, memory,
  privacy, and rollback gates pass.
