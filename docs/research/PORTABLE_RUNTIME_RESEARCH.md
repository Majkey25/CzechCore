# Portable runtime research

## Goal

Run the same correction contract locally on Windows and Android without
reimplementing Czech logic, uploading user text, or silently reducing quality.

## Current Python baseline

- BART-style encoder-decoder, approximately 60.8M parameters;
- WordPiece tokenizer and UDPipe sentence segmentation;
- four-beam autoregressive generation;
- Python/PyTorch orchestration;
- structured Unicode code-point edits;
- non-commercial default assets.

The Python runtime is the quality/reference implementation, not the final mobile
packaging format.

## Export complexity

Encoder-decoder generation requires more than exporting one static forward pass:

- encoder graph;
- decoder first step;
- decoder-with-past steps and KV cache;
- beam search, EOS, length/scoring behavior;
- tokenizer parity;
- maximum positions and dynamic sequence axes;
- exact text decoding/detokenization.

An exported runtime must match reference hypotheses/scores under a parity suite.

## Candidate runtime paths

### ONNX Runtime

Potentially suitable for Windows and Android arm64. Research must verify supported
operators, encoder/decoder cache, quantization, package size, and mobile APIs for
the exact pinned Transformers architecture.

### Native C++ inference

Could provide a stable C ABI and direct Windows integration, but would require
implementing/embedding tokenizer and generation logic or using a mature runtime.
Do not hand-roll Transformer kernels or beam search without measured necessity.

### Edit-tagger student

A Czech encoder-only tagger may dramatically simplify export and latency. It must
prove coverage for rich inflection, punctuation, split/join, and multi-token
edits. MorphoDiTa generation could reduce transformation vocabulary size.

### Quantized seq2seq student

Distill the large quality teacher into a smaller encoder-decoder, then quantize.
This preserves open-ended generation but retains autoregressive complexity.

## Quantization experiments

For each FP16/INT8/INT4/dynamic option, report:

- artifact size and peak memory;
- cold/warm latency;
- output parity rate;
- GECCC F0.5 and per-family deltas;
- correct-text false-change delta;
- confidence/calibration drift;
- unsupported operators/fallbacks.

No quantized artifact ships from a successful load test alone.

## Stable native boundary

Future adapters should consume a narrow versioned contract equivalent to:

```text
correct(text, options) -> result {
  original_text,
  suggested_text,
  output_text,
  edits[start,end,replacement,kind,confidence,applied],
  warnings,
  model_manifest_id
}
```

The runtime boundary should use UTF-8 and explicit offset units. Platform adapters
convert to UTF-16 where required.

## Windows

Target sequence after portable parity:

1. Windows Spell Checking API provider for platform underlines/suggestions;
2. optional TSF work only for grammar surfaces not covered by the provider;
3. model lifecycle/cache/settings application;
4. code-point/UTF-16 conversion;
5. background inference and cancellation;
6. per-application compatibility tests.

## Android

Target sequence after portable parity:

1. `SpellCheckerService` suggestion integration;
2. Kotlin/Java thin adapter to native/runtime library;
3. explicit asset install/update/verification;
4. process/memory/thermal benchmarks;
5. optional keyboard integration only if automatic correction requires it;
6. never process password/sensitive input fields.

## Model packaging and licensing

Every package needs:

- code/model/tokenizer/calibrator versions;
- hashes and sizes;
- license/attribution;
- supported architectures;
- benchmark report;
- minimum RAM/storage;
- update/rollback compatibility.

The current CC BY-NC-SA model stack cannot become a commercial device product by
changing runtime format. Licensing/data replacement is a separate gate.

## Portable runtime done criteria

- reference parity on frozen corpus and adversarial Unicode/offset suites;
- approved accuracy and false-change deltas;
- measured memory/startup/p95 latency on target devices;
- deterministic/offline operation;
- verified native crash/error handling;
- stable ABI/API and model-manifest compatibility;
- license review and notices;
- real Windows/Android application flows.
