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

## First measured CTranslate2 screen: 2026-08-18

CTranslate2 4.8.1 is now the leading portable proofread-runtime candidate. It
already implements BART encoder-decoder inference, beam search, scoring,
quantization, a C++ API, and ARM64 CPU kernels.

The exact CzechCore model converted after an explicit compatibility shim:
standard Hugging Face BART is post-norm, while the CTranslate2 4.8.1 converter
still reads the removed `BartConfig.normalize_before` field. The probe supplied
`false`; no model weight or runtime graph was changed.

### Acceptance-suite raw-generation parity

| Runtime/model | Model bytes | Top match | Ordered four beams | Four-beam set | Measured generation time |
| --- | ---: | ---: | ---: | ---: | ---: |
| PyTorch FP32 reference | 243,312,640 source weights | 66/66 | reference | reference | 12.09 s |
| CTranslate2 FP32 | 243,158,208 | 66/66 | 62/66 | 62/66 | 4.99 s |
| CTranslate2 INT8 | 62,287,948 | 65/66 | 32/66 | 46/66 | 2.53 s |

The probe covers all 65 acceptance cases split into 66 real UDPipe sentence
spans, with beam size four and four returned hypotheses on one Windows CPU run.
It measures raw generation, not full GECCC quality or product-level
unchanged-candidate scoring.

INT8 is rejected as the default: for `Kdy přijdeš`, it ranked the unchanged
text above the required `Kdy přijdeš?`. Smaller size and speed do not override
this regression. FP32 advances to product-parity and device testing.

### Android NDK build

CTranslate2 was configured and fully compiled with:

- NDK `28.2.13676358`, Clang `19.0.1`;
- `arm64-v8a`, Android API 26;
- Ruy CPU backend and NEON dispatch;
- CUDA, MKL, DNNL, OpenBLAS, OpenMP, CLI, and tests disabled.

The build required one narrow upstream portability patch. Android Bionic does not
declare Linux `pthread_setaffinity_np`; the default runtime does not request
thread affinity, so the Android build treats affinity setting as unsupported.

Result:

| Artifact | Result |
| --- | --- |
| Unstripped shared library | 55,653,440 bytes |
| Stripped `libctranslate2.so` | 3,911,616 bytes |
| ABI | ELF64 AArch64 shared object |
| Dynamic dependencies | `libdl`, `liblog`, `libm`, `libc` |
| Stripped SHA-256 | `69d4644ef84b9adc3907f74b49b8b3aa275a9be72e29707dc948b6fe6ee7696b` |

The native runtime is buildable for Android. Android is still not a functioning
product: WordPiece/UDPipe parity, unchanged-candidate scoring, JNI, model
lifecycle, text services, and emulator/physical-device tests remain.

### Native emulator inference

The same FP32 model and an x86_64/API 26 build were pushed to an already-running
Android 35 `sdk_gphone64_x86_64` emulator. A native executable loaded
`libctranslate2.so` and the model from `/data/local/tmp`; it did not call a
desktop model server.

Input WordPiece tokens:

```text
[CLS] Když přišel domů šel spát . [SEP]
```

Output:

```text
Když přišel domů , šel spát .
```

The process returned exit 0. Measured whole-process times were 5.19 s and 1.74 s
on consecutive launches; these include loading the 243 MB model each time and
are not an in-app warm-latency result. The x86_64 stripped library is 4,386,568
bytes with SHA-256
`cf5e7377b5abbb9d695550709549f05d504cc31077bbce922021ea6d92c33fbd`.

This standalone-executable stage proved native local BART inference in the
emulator. It did not by itself satisfy the APK gate; the next stage added a
source debug application.

### Source debug APK probe

A Java/NDK debug application now packages arm64-v8a and x86_64 CTranslate2
runtimes, loads the FP32 model from app-specific external storage, performs
WordPiece tokenization in Java, calls beam inference through JNI off the UI
thread, and displays the result. Emulator execution used x86_64.

Verified on the same Android 35 emulator:

| Source | Result |
| --- | --- |
| `Když přišel domů šel spát.` | `Když přišel domů, šel spát.` |
| `Muži přišly domů.` | `Muži přišli domů.` |
| `Byli doma.` | unchanged |
| Email + `v1.2.3` | unsafe raw model candidate rejected; exact source fallback |

The final dual-ABI debug APK is 9,512,479 bytes with SHA-256
`243914109a34efb5ca355dc82c15c7a673da2dbeb1209cfcad5656479816e220`.
Five JVM tokenizer/protection/boundary tests pass. After the final flows, the emulator
crash buffer was empty and app logcat contained no raw input. Measured
post-inference memory was 375,568 KB PSS / 446,404 KB RSS.

This is a source-only runtime probe, not a release APK or keyboard. The model is
not bundled, WordPiece parity is not yet exhaustive, UDPipe is not integrated,
and Android text services remain open.

Machine-readable evidence:
[`portable-runtime-screen-2026-08-18.json`](../../research/evaluations/portable-runtime-screen-2026-08-18.json).
