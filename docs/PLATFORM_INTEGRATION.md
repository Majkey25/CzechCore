# Windows and Android live-text integration

## Status

Architecture accepted for implementation. No Windows or Android binary is part of
`v0.3.0`. This document defines the smallest practical product that preserves
the measured engine contract and does not pretend platform coverage exists before
real device tests.

## Product contract

The user chooses one mode globally and may override it per application:

| Mode | Inference | UI | Text mutation |
| --- | --- | --- | --- |
| `off` | None | None | Never |
| `underline` | Current sentence after debounce | Underline plus alternatives | Never |
| `confirm` | Current sentence after debounce | Underline/candidate bar | Only after tap, click, or shortcut |
| `automatic` | Current sentence after debounce | Applied edit plus visible undo | Only calibrated `auto_safe` edits |

Whole-sentence `rewrite` is not a fifth typing mode. It is an explicit action on
a selected sentence or paragraph and always shows a before/after preview.

Current beam-relative confidence is not sufficient to mark an edit
`auto_safe`. Until a separate calibrated selector passes the production gate,
`automatic` must behave like `confirm` for neural edits. Exact deterministic
repairs may be enabled only when their own correct-text suite passes.

## Interaction model

```text
key event
  -> update editor revision
  -> identify bounded Czech sentence/context
  -> cancel older request
  -> debounce
  -> run local proofread off the UI thread
  -> reject result if revision/caret/range changed
  -> convert Unicode-scalar offsets to UTF-16
  -> render underline/candidates
  -> apply only after user action or auto_safe policy
```

### Timing rules

- Analyze immediately at a sentence terminator or explicit command.
- Otherwise debounce for an initial target of 250 ms.
- Never queue more than one pending request per editor.
- Cancel work when the editor revision changes; if inference cannot be cancelled,
  discard its stale result.
- Do not re-analyze text produced by CzechCore until the editor reports a new user
  revision.
- Apply a sentence atomically and retain one-step undo metadata.

The values are starting budgets, not published performance. Device measurements
must decide whether they change.

## Shared runtime boundary

Python remains the quality/reference implementation. Production adapters consume
one versioned native contract rather than reimplementing Czech policy.

```text
correct(request) -> response

request:
  protocol_version
  request_id
  document_revision
  locale
  mode
  text
  selection
  protected_ranges

response:
  protocol_version
  request_id
  document_revision
  original_text
  suggested_text
  edits[]
  warnings[]
  model_manifest_id
```

Every edit contains `start`, `end`, `source`, `replacement`, `kind`,
`confidence_kind`, `confidence`, and `application_class`. Offset units are
explicitly `unicode_scalar` at the runtime boundary. Adapters convert to UTF-16
only after validating the exact source slice.

The contract is UTF-8, deterministic for a pinned manifest, bounded to 16 KiB per
request, and rejects unknown protocol/options instead of guessing.

## Portable inference plan

The existing model is encoder-decoder, so a valid export must include:

- encoder graph;
- first decoder step;
- decoder-with-past steps and KV cache;
- identical beam search, EOS, length normalization, and candidate deduplication;
- WordPiece normalization/tokenization parity;
- UDPipe sentence/token range parity;
- unchanged-candidate scoring and safety policy;
- exact detokenization and edit alignment.

CTranslate2 4.8.1 is the leading measured runtime: it supports BART and beam
search, matched 66/66 acceptance-span FP32 top outputs, and compiled with the
Android NDK for arm64-v8a/API 26. Its INT8 model changed one required punctuation
result and is rejected as the default. ONNX Runtime Mobile remains an alternative,
but generic BART generation would require additional orchestration.

A separate x86_64/API 26 build ran the FP32 model locally in an Android 35
emulator and returned the required missing-comma correction. It proves native
inference only; it does not replace the APK/JNI/text-service acceptance gates.

A source debug APK subsequently added Java WordPiece, JNI, app-specific external
model loading, background inference, protected-literal fallback, and a real
`InputMethodService`. Cross-app candidate/apply, underline, undo, automatic
duplicate removal, and Chrome URL privacy flows passed in Android 35. Signed
distribution, model lifecycle, physical devices, and SpellCheckerService remain.
The source engine now keeps one running plus one latest pending request, rejects
empty or oversized model assets, and exposes only a generic UI error. The final
x86_64 emulator run measured 365,814 KiB PSS / 439,824 KiB RSS after inference;
no physical-device latency, battery, or thermal claim is made.

The runtime ships only after:

1. FP32 reference parity on the frozen candidate suite;
2. INT8/other quantization deltas for M2, false changes, confidence, and output
   identity are measured;
3. cold/warm latency, peak RAM, package size, and thermal behavior are measured;
4. model/tokenizer/runtime hashes and licenses are in one manifest;
5. native failures return explicit errors and never corrupt editor text.

No custom Transformer kernels or hand-written beam-search fork is justified while
a verified runtime path remains available.

## Android

### Why two Android surfaces are required

Android exposes different capabilities:

- [`SpellCheckerService`](https://developer.android.com/reference/android/service/textservice/SpellCheckerService)
  supplies suggestions to applications that use the platform text-services
  framework;
- [`InputMethodService`](https://developer.android.com/develop/ui/views/touch-and-input/creating-input-method)
  and `InputConnection` are required for a keyboard to read bounded context,
  show candidates, and commit edits while the user types;
- `ACTION_PROCESS_TEXT` provides a simple explicit “Correct with CzechCore”
  action for selected text.

`SpellCheckerService` cannot guarantee underlines in every application and
cannot provide universal automatic application. An IME can, but the user must
choose it as the active keyboard. Accessibility-service or global screen-scraping
approaches are rejected.

### Android delivery sequence

#### 1. Text-service application

The first installable app contains:

- `SpellCheckerService` for Czech `cs-CZ`;
- `ACTION_PROCESS_TEXT` proofread/rewrite preview;
- settings and model management;
- the native runtime through JNI;
- no internet permission in the correction process.

This works with the user's existing keyboard where applications consume Android
text services. It is the smallest honest Android integration.

#### 2. Live keyboard

For immediate candidates and optional auto-apply, do not build a complete
keyboard from scratch. Integrate the same runtime into a maintained offline AOSP
keyboard codebase such as
[HeliBoard](https://github.com/HeliBorg/HeliBoard) in a separate GPL-3.0
distribution. CzechCore's MIT runtime can be consumed there, while the keyboard
application and modifications remain GPL-compliant.

The IME:

- requests a bounded range around the caret through `InputConnection`;
- owns a monotonically increasing editor revision;
- sends no password, PIN, email-password, payment, or
  `IME_FLAG_NO_PERSONALIZED_LEARNING` field to inference/persistence;
- shows proofread alternatives in the candidate strip;
- applies edits only when the original UTF-16 range still matches;
- restores the exact previous range on undo;
- clears context and personalization when the editor changes.

### Android process and model policy

- One model instance per IME/text-service process.
- Memory-mapped read-only weights where supported.
- Arm64-v8a is the first native target; other ABIs require separate measurement.
- Models are installed explicitly with hash verification and atomic activation.
- Keep the previous compatible model until the new manifest passes startup.
- User dictionaries and feedback stay bounded, local, erasable, and disabled by
  default.

### Android acceptance matrix

At minimum test:

- AOSP `EditText`, Chrome/Chromium, messaging editor, office editor, and a
  custom `InputConnection`;
- Czech diacritics, surrogate-pair emoji before/inside/after an edit, combining
  marks, multiline text, selection changes, and rapid typing;
- password/sensitive fields and incognito/no-learning flags;
- underline, confirm, automatic fallback, undo, stale result, process death, and
  model rollback;
- cold start, warm p50/p95 latency, peak proportional set size, battery, and
  thermal throttling on low/mid/high Android arm64 profiles.

## Windows

### Chosen Windows surface

Use the [Text Services Framework
(TSF)](https://learn.microsoft.com/en-us/windows/win32/api/_tsf/) as the primary
live integration:

- TSF display attributes can render spelling-style underlines;
- candidate UI elements can expose alternatives;
- read/write edit sessions can apply a validated range;
- input scopes allow sensitive fields to be excluded.

The TSF DLL is deliberately thin. Loading the neural model inside every host
application would multiply memory and increase crash impact.

```text
TSF in-process COM text service
  <-> authenticated per-user named pipe
  <-> single CzechCore engine process
  <-> portable model runtime and manifest

Settings/tray application
  <-> same engine control endpoint
```

TSF activation preloads one mutex-protected engine process. It exits after ten
minutes without a client, so the 244 MB model is not repeatedly reloaded during
active use but its measured 306.82 MiB working set is eventually released. The
pipe accepts only the current user SID and `SYSTEM`, rejects remote clients, uses
length-prefixed messages plus an acknowledgement, enforces a 16 KiB size limit
and five-second I/O timeout, verifies the broker process image, and never logs
raw text.

The source implementation now builds this topology with a static x64 CTranslate2
broker, x64/x86 TSF DLLs, native mode settings, and a UAC-aware setup payload.
Native broker outputs and `ITfThreadMgr`/`ITfContext` automatic/confirm flows
passed, including a cold broker start. Ten warm local requests measured 159.92 ms
median and 170.96 ms p95 end-to-end. Elevated profile installation and the
real-application matrix remain release gates. The current TSF source still waits
for warm inference on the host thread at sentence end/manual check; marshaling
that request off-thread remains required before a signed stable adapter release.

### TSF behavior

- Subscribe to text/layout/selection changes for the active context.
- Read only the bounded sentence window in a TSF read session.
- Perform inference outside TSF edit sessions and outside the host UI thread.
- Re-enter a read session to verify the original range before rendering.
- Apply display attributes through `ITfDisplayAttributeProvider`.
- Use a read/write edit session only after acceptance and exact range validation.
- Remove attributes when text, selection, locale, mode, or model revision changes.
- Never intercept raw keyboard events when a text-change notification suffices.

### Secondary Windows provider

A later `ISpellCheckProvider` can expose CzechCore to applications that consume
the Windows Spell Checking API. Microsoft documents external providers and
restricted out-of-process hosting. It is secondary because provider coverage and
sentence-level grammar behavior must be measured; it must not duplicate the
engine or policy.

### Windows acceptance matrix

At minimum test:

- Notepad, Word/Office, Chromium editor, Windows text controls, and a TSF sample
  host;
- x64 and Arm64 where supported; x86 only if a target application requires it;
- UTF-16 surrogate pairs, combining marks, IME composition, multiline selection,
  undo/redo, stale revisions, document switches, protected literals, and long
  sentences;
- password/input scopes, elevated-vs-standard processes, Fast User Switching,
  session lock, engine crash/restart, and installer rollback;
- cold/warm p50/p95 latency, working set, model sharing, and host responsiveness.

Code signing and installer reputation are release requirements. Unsigned local
development builds are not a production distribution.

## Settings

The settings schema is small and shared semantically across platforms:

| Setting | Default | Notes |
| --- | --- | --- |
| Mode | `underline` | Never silently enable automatic mode |
| Language | `cs-CZ` | Skip unsupported locale/input |
| Debounce | 250 ms | Bounded configuration; device-tuned |
| Rewrite | Disabled | Explicit action only |
| User dictionary | Disabled | Local, bounded, deletable |
| Per-app override | None | User-controlled allow/deny/mode |
| Diagnostics | Off | Never contain raw text by default |

Settings changes invalidate pending work. Platform adapters do not invent their
own correction thresholds; thresholds belong to the signed model/policy manifest.

## Privacy and security

- No cloud inference, telemetry, account, or mandatory network connection.
- The model downloader is a separate explicit action; correction processes run
  without network access where platform packaging permits.
- Password/sensitive fields are skipped before text crosses the adapter boundary.
- Raw text is not logged, persisted, or used for learning by default.
- Personalization is opt-in, bounded, expires, and has a one-action erase control.
- Model packages are hash-verified, versioned, atomically activated, and
  rollback-compatible.
- Named entities, numbers, code, URLs, and caller-protected ranges remain hard
  candidate invariants.

## Release gates

### Shared runtime

- Reference output parity on frozen proofread and Unicode suites.
- Approved accuracy delta after quantization.
- Deterministic model manifest and explicit runtime errors.
- No model/text network access during inference.

### Suggestions

- Frozen GECCC test and adversarial correct-text results.
- Per-domain/error metrics and false-change confidence intervals.
- No offset/protected-literal regressions.

### Automatic mode

- Separately calibrated per-edit/sentence selector.
- Lower confidence bound at the approved precision target.
- Non-zero held-out coverage.
- One-step undo and stale-edit rejection proven in real applications.
- Broad rewrites permanently excluded.

### Platform release

- Real Windows and Android application matrix passes.
- p95 latency, memory, startup, battery/thermal budgets pass.
- Signed installers/packages and rollback tested.
- License/notice/model-download flow reviewed.

## Rejected shortcuts

| Shortcut | Why rejected |
| --- | --- |
| Accessibility service on Android | Excessive privilege, brittle text access, poor trust |
| Global keyboard hook on Windows | No reliable semantic ranges/underlines; privacy and compatibility risk |
| Full custom Android keyboard from zero | Reimplements years of layout, gesture, language, and accessibility work |
| Model inside every Windows host | Duplicated memory and larger crash surface |
| Python runtime embedded in mobile app | Package/startup complexity and no shared native deployment path |
| One generic local LLM for every edit | Higher latency and measured meaning damage on screened models |
| Confidence threshold marketed as accuracy | Contradicted by the complete GECCC calibration curve |

## Authoritative platform references

- Android:
  [Create an input method](https://developer.android.com/develop/ui/views/touch-and-input/creating-input-method),
  [`InputConnection`](https://developer.android.com/reference/android/view/inputmethod/InputConnection),
  [`SpellCheckerService`](https://developer.android.com/reference/android/service/textservice/SpellCheckerService).
- Windows:
  [Text Services Framework](https://learn.microsoft.com/en-us/windows/win32/api/_tsf/),
  [Providing display attributes](https://learn.microsoft.com/en-us/windows/win32/tsf/providing-display-attributes),
  [Spell Checking API](https://learn.microsoft.com/en-us/windows/win32/intl/about-the-spell-checker-api).
- Runtime:
  [ONNX Runtime Mobile](https://onnxruntime.ai/docs/tutorials/mobile/),
  [Optimum ORT seq2seq models](https://huggingface.co/docs/optimum-onnx/en/onnxruntime/package_reference/modeling_ort).
