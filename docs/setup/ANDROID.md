# CzechCore on Android

> [!CAUTION]
> No APK is available in v0.2.0. The desktop Python/PyTorch wheel cannot be
> installed as an Android keyboard or spell checker. Termux is not supported.

## Current status

Android is not installable from the v0.2.0 release. Main now contains a
source-only debug runtime probe with package `cz.czechcore.app`, Java
WordPiece, JNI, and local CTranslate2 inference. There is still no published APK,
Play Store listing, bundled model, SpellCheckerService, or IME.

Reproducible source build and emulator commands:
[`android/README.md`](../../android/README.md).

The Android target remains part of CzechCore, but it is blocked by the portable
inference runtime described below.

## Why the desktop instructions do not apply

The released wheel depends on desktop CPython, PyTorch, Transformers, and native
ufal.udpipe bindings. Android applications run in the Android runtime and require
Android-compatible native libraries for the selected ABI.

Termux does not turn a Python CLI into:

- Android SpellCheckerService integration;
- an InputMethodService keyboard;
- native underlines or candidate UI;
- safe InputConnection edit application;
- a signed installable APK.

Termux is therefore not a supported product path or emulator substitute.

## Intended user experience

The Android application has four explicit modes:

| Mode | Behavior |
| --- | --- |
| Off | No text is sent to inference |
| Underline | Show corrections without changing text |
| Confirm | Apply only after the user taps a candidate |
| Automatic | Apply only edits classified by a future calibrated policy as auto-safe |

Whole-sentence rewrite remains an explicit selected-text action with before/after
review. It is never silently applied while typing.

## Planned Android surfaces

### SpellCheckerService

Provides Czech suggestions to editors that consume Android's text-services
framework. Application coverage is not universal.

Official API:
[SpellCheckerService](https://developer.android.com/reference/android/service/textservice/SpellCheckerService).

### ACTION_PROCESS_TEXT

Provides an explicit "Correct with CzechCore" action for selected text. This is
the smallest practical integration and does not replace the user's keyboard.

### InputMethodService

Required for live candidates and optional automatic application across compatible
editors. Rather than writing an entire keyboard from zero, the approved direction
is to integrate CzechCore into a maintained offline AOSP-derived keyboard
distribution.

Official guide:
[Create an input method](https://developer.android.com/develop/ui/views/touch-and-input/creating-input-method).

## Required local runtime

The APK must perform inference on the Android device. It may not call a model
server running on the development PC.

The portable runtime must reproduce:

- WordPiece normalization and tokenization;
- UDPipe sentence and exact token ranges;
- encoder graph;
- first decoder step;
- decoder-with-past and KV cache;
- four-beam search, EOS, length scoring, and deduplication;
- unchanged-candidate scoring;
- protected-literal and changed-ratio gates;
- Unicode edit alignment and UTF-16 conversion.

CTranslate2 4.8.1 is now the leading measured candidate. FP32 conversion matched
66/66 acceptance sentence-span top outputs and its C++ runtime compiled as a
stripped 3.9 MB Android arm64-v8a shared library. INT8 changed one required
punctuation result and is rejected as the default. Product scoring, WordPiece,
UDPipe, JNI, APK, and emulator gates remain.

Measured details:
[Portable runtime research](../research/PORTABLE_RUNTIME_RESEARCH.md).

An x86_64 source debug APK has run the FP32 model locally inside an Android 35
emulator through JNI. Missing-comma and agreement corrections passed, correct
text stayed unchanged, and a damaged email/version candidate was rejected with
exact source fallback. The caution remains because no APK/model is published and
Android text-service integration is still missing.

## Model installation policy

The final application must:

- download assets only after explicit user action;
- verify hashes and a signed/versioned manifest;
- activate new assets atomically;
- retain the previous compatible manifest for rollback;
- perform correction without network access;
- display model license and non-commercial limitations;
- expose storage usage and a safe model-removal action.

The v0.2.0 desktop wheel SHA-256 is:

~~~text
8d1aab92dce9d854e15f18107f3f987edf7d49806efa24759994717396412621
~~~

This hash documents the desktop release only. It is not an APK checksum.

## Privacy requirements

Before text crosses the Android adapter boundary:

- reject password, PIN, payment, and other sensitive input types;
- honor IME_FLAG_NO_PERSONALIZED_LEARNING;
- disable raw-text logging;
- keep diagnostics free of user content;
- bound and expire any opt-in user dictionary/feedback;
- clear editor context on field/application changes.

The APK must not request accessibility-service privileges for text correction.

## Required emulator test

Android is considered functional only after all steps pass in a pinned emulator:

1. Build a release-like debug APK from a clean checkout.
2. Create/select a pinned Android API and arm64/x86_64 system image.
3. Install with adb install.
4. Verify package/version/signing metadata.
5. Enable CzechCore SpellCheckerService.
6. Enable/select the CzechCore IME for live-mode tests.
7. Type Czech text into a standard EditText and browser/editor surface.
8. Verify missing comma, agreement, diacritics, correct-negative, and protected
   technical text.
9. Verify emoji/non-BMP UTF-16 offsets before, inside, and after edits.
10. Verify multiline text, selection movement, stale-result cancellation, long
    input, undo, and process restart.
11. Prove password and no-learning fields never reach inference.
12. Capture UI hierarchy/screenshots and inspect logcat for crashes or raw text.
13. Measure cold/warm latency, peak memory, APK/model size, and emulator ABI.
14. Disconnect emulator networking and repeat correction locally.

A placeholder UI, mocked response, or desktop-hosted model does not pass.

## Required physical-device test

Emulator success is necessary but not sufficient. Before public Android release,
repeat the core matrix on low/mid/high arm64 devices and record:

- p50/p95 latency;
- peak memory;
- battery usage;
- sustained thermal throttling;
- keyboard/editor compatibility;
- install/update/rollback behavior.

## Release gate

The caution at the top may be replaced with installation commands only when:

- portable runtime parity passes;
- quantized quality/false-change deltas are approved;
- an APK exists and is reproducibly built;
- emulator and physical-device matrices pass;
- package name, signing, minimum Android version, ABI list, model URL/hash, and
  exact settings screens are known;
- the APK and model licenses/notices are published.

Until then, use CzechCore on
[Windows](WINDOWS.md), [macOS](MACOS.md), or [Linux](LINUX.md).

Detailed architecture:
[Windows and Android live-text integration](../PLATFORM_INTEGRATION.md).
