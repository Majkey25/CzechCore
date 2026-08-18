# Per-device setup documentation design

## Status

Reviewed with an added requirement: every claimed operating-system integration
must pass in a clean virtual environment or emulator with real correction, not
only import/version checks.

## Goal

Give a new user one reliable path from a clean machine to a verified CzechCore
correction, with a separate guide for Windows, macOS, Linux, and Android.
Commands must match the released package and be tested where the platform is
currently supported. Unsupported platform binaries must be stated plainly.

## Chosen structure

```text
README.md
  -> docs/GETTING_STARTED.md
       -> docs/setup/WINDOWS.md
       -> docs/setup/MACOS.md
       -> docs/setup/LINUX.md
       -> docs/setup/ANDROID.md
```

The root README keeps a five-minute quick start and links to the device chooser.
`GETTING_STARTED.md` explains which guide to choose, what is implemented, model
size/licensing, and the common verification result. Each device guide owns its
platform-specific commands and troubleshooting.

## Delivery decomposition

The requirement spans three dependent deliverables:

1. **Desktop distribution and documentation:** clean Windows, macOS, and Linux
   environments install the package, provision real assets, and run correction.
2. **Portable inference runtime:** export and verify the model/tokenizer/generation
   stack needed outside desktop Python.
3. **Android application:** package the portable runtime behind Android text
   services, then install and test the APK in an emulator.

The documentation work may be published after desktop verification, but the
overall Windows/macOS/Linux/Android functionality requirement is not complete
until all three deliverables pass. Android cannot be made green by testing a
placeholder UI or a desktop-hosted backend.

## Alternatives considered

### Put every platform in the root README

Rejected. The README would become a long installation manual and obscure the
product, measurements, and architecture.

### Keep setup fragments in API and development documents

Rejected. Users would need to reconstruct one workflow from several files.

### One master guide plus one file per device

Selected. It provides a single entry point, avoids duplicated device commands,
and keeps unsupported Android status explicit.

## Common guide contract

Every supported desktop guide contains:

1. current support status and tested architecture;
2. prerequisites with official installation links;
3. release-wheel installation in a virtual environment;
4. optional source/developer installation;
5. wheel SHA-256 verification;
6. explicit model download and cache locations;
7. version, suggestion, JSON, automatic, and Python API smoke commands;
8. expected output for a stable sentence;
9. benchmark and full test commands where the source checkout is required;
10. offline-use verification;
11. update, rollback, and uninstall steps;
12. troubleshooting for missing Python, missing assets, memory/disk, locale,
    certificate/network download, and shell path problems;
13. a statement of which steps were tested and which remain CI-only.

Commands use the released `v0.2.0` wheel URL and its published SHA-256:

```text
8d1aab92dce9d854e15f18107f3f987edf7d49806efa24759994717396412621
```

No guide labels beam-relative confidence as correctness probability.

## Windows guide

- Reference shell: PowerShell.
- Reference Python: `py -3.12`.
- Virtual environment: `.venv\Scripts\...`.
- Checksum: `Get-FileHash -Algorithm SHA256`.
- UDPipe cache: `%LOCALAPPDATA%\CzechCore`.
- Hugging Face cache: the library-reported path from `czechcore download`.
- Verification includes the current physical Windows machine, public release
  wheel, full dependency installation, asset reuse, CLI/API/model scenarios,
  benchmark, and quality gates.

## macOS guide

- Reference shell: `zsh`.
- Support both Apple Silicon and Intel only where dependency installation proves
  it; unverified architectures are labeled.
- Virtual environment: `.venv/bin/...`.
- Checksum: `shasum -a 256`.
- Default project cache: `~/.cache/czechcore` unless `XDG_CACHE_HOME` is set.
- Commands are checked on a GitHub-hosted macOS runner with Python 3.12.

## Linux guide

- Reference shell: POSIX-compatible `bash`.
- Primary verified distribution: the GitHub Actions Ubuntu image with Python
  3.12.
- Virtual environment: `.venv/bin/...`.
- Checksum: `sha256sum`.
- Default project cache: `$XDG_CACHE_HOME/czechcore` or
  `~/.cache/czechcore`.
- Distribution package-manager examples are limited to named distributions and
  are not presented as universal Linux commands.

## Android guide

The Python/PyTorch wheel is not an Android application and no APK exists in
`v0.2.0`. The Android guide therefore contains:

- a prominent “not installable yet” status;
- why Termux/Python is not a supported substitute;
- the approved `SpellCheckerService`, `ACTION_PROCESS_TEXT`, and optional IME
  architecture;
- intended `off / underline / confirm / automatic` settings;
- sensitive-field and offline guarantees;
- the exact implementation/build/test gates required before an APK guide can be
  activated;
- links to the platform integration specification and official Android APIs.

It contains no fake Gradle commands, package name, APK URL, screenshots, or Play
Store claim.

## Cross-platform verification

Extend GitHub Actions with a full desktop model-smoke matrix:

| OS | Python | Required smoke |
| --- | --- | --- |
| Windows latest | 3.12 | clean venv, install, `pip check`, asset download, real correction, model tests |
| macOS latest | 3.12 | clean venv, install, `pip check`, asset download, real correction, model tests |
| Ubuntu latest | 3.12 | clean venv, install, `pip check`, asset download, real correction, model tests |

The existing Ubuntu 3.12/3.13/3.14 quality matrix remains authoritative for
lint/type/research validation. Hosted model assets are cached by pinned
model/revision and UDPipe hash; cache reuse must never bypass runtime hash and
tokenizer checks.

Release-wheel installation is additionally re-tested on Windows from the public
asset URL. Documentation snippets are compared against actual `--help` output
and live commands.

## Android emulator verification

No Android pass is possible until the portable runtime and APK exist. The eventual
emulator gate must:

1. build a release-like debug APK from a clean checkout;
2. create or select a pinned Android API/ABI virtual device;
3. install through `adb install`;
4. activate CzechCore as `SpellCheckerService` and, for live application, as
   the selected IME;
5. type Czech text into at least a standard `EditText` and a browser/editor;
6. verify underline-only, confirmation, automatic fallback, undo, and explicit
   rewrite behavior;
7. verify correct text, punctuation, agreement, diacritics, protected literals,
   emoji/UTF-16 offsets, multiline text, stale revisions, and long input;
8. prove password and no-personalized-learning fields do not reach inference;
9. capture UI hierarchy/screenshots and inspect `logcat` for crashes or leaked
   text;
10. record cold/warm latency, memory, APK/model size, and emulator architecture.

The emulator must run inference locally inside the Android app. Calling a model
server on the development PC does not satisfy the offline-device requirement.

## Documentation changes

- Add the five setup documents.
- Add setup links near the top of `README.md` and in its documentation table.
- Add the chooser to `docs/README.md`.
- Update `CHANGELOG.md` under `Unreleased`.
- Update the public `v0.2.0` release body with a link to the main-branch setup
  chooser after publication; do not retag or replace the immutable wheel.

## Error handling and honesty

- Missing assets -> show the exact `czechcore download` recovery.
- Unsupported Python -> show the supported range and Python 3.12 recommendation.
- Download failure -> preserve partial-download safety and explain retry/proxy/
  certificate diagnosis without disabling TLS verification.
- Out-of-memory or slow inference -> state the compact model still has a large
  PyTorch runtime; no invented minimum RAM value without measurement.
- Android -> stop at the missing binary boundary.
- macOS/Linux -> distinguish CI verification from physical-device testing.

## Done criteria

- All five documents exist and are linked from the README/docs index.
- No duplicated command disagrees with CLI help or package metadata.
- Windows public-wheel install and live correction pass.
- Windows, macOS, and Ubuntu clean-environment real-model jobs pass on the exact
  commit.
- Existing 88 tests, Ruff, format, Pyright, research validators, benchmark, and
  real-model scenarios remain green.
- GitHub renders README and all setup documents.
- `main`, `origin/main`, and the public content SHAs match.
- A separate portable-runtime/Android implementation plan exists before Android
  coding starts.
- Android remains explicitly blocked until an APK runs local inference and the
  emulator matrix above passes.
- No Android/Windows system-adapter binary is claimed until it exists and passes.
