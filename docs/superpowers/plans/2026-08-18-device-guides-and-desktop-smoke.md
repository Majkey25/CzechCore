# Device Guides and Desktop Model Smoke Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox syntax.

**Goal:** Publish one complete setup guide per requested operating system and
prove the released engine with real model inference in clean Windows, macOS, and
Linux virtual environments.

**Architecture:** A device chooser routes users to one platform-owned Markdown
file. A repository test enforces version, checksum, status, and link invariants.
A GitHub Actions matrix creates a fresh venv on each desktop OS, installs the
public v0.2.0 wheel, downloads pinned assets, and runs real-model tests. Android
remains a documented hard gate until a native APK exists.

**Tech Stack:** Markdown, Python 3.12, pytest, GitHub Actions, PowerShell,
POSIX shell, PyTorch, Transformers, and UDPipe.

---

### Task 1: Lock the documentation contract

**Files:**
- Modify: tests/test_repository.py
- Create: docs/GETTING_STARTED.md
- Create: docs/setup/WINDOWS.md
- Create: docs/setup/MACOS.md
- Create: docs/setup/LINUX.md
- Create: docs/setup/ANDROID.md

- [ ] **Step 1: Add a failing repository test**

Add a test that loads the version from pyproject.toml, defines the published
wheel SHA-256
8d1aab92dce9d854e15f18107f3f987edf7d49806efa24759994717396412621,
requires all five files, requires version/hash in every desktop guide, and
requires the exact Android phrases "No APK is available" and
"Termux is not supported".

- [ ] **Step 2: Run the test to verify RED**

Run:

~~~powershell
.venv\Scripts\python -m pytest tests\test_repository.py::test_device_setup_guides_are_versioned_and_linked -q
~~~

Expected: FAIL because the setup documents do not exist.

- [ ] **Step 3: Create title-only files and rerun RED**

Expected: FAIL on missing version/hash/status content. This proves the test checks
the contract, not only file existence.

### Task 2: Implement chooser and Windows guide

**Files:**
- Create: docs/GETTING_STARTED.md
- Create: docs/setup/WINDOWS.md

- [ ] **Step 1: Write the chooser**

Include the support matrix, Python 3.12 recommendation, wheel URL/hash, explicit
asset download, stable expected correction, all device links, Android unavailable
status, and links to API/evaluation/platform/license documents.

- [ ] **Step 2: Write the Windows release flow**

Use these commands and document each expected result:

~~~powershell
$wheel = "czechcore-0.2.0-py3-none-any.whl"
Invoke-WebRequest -Uri "https://github.com/Majkey25/CzechCore/releases/download/v0.2.0/$wheel" -OutFile $wheel
(Get-FileHash -Algorithm SHA256 $wheel).Hash.ToLowerInvariant()
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install .\czechcore-0.2.0-py3-none-any.whl
.venv\Scripts\python -m pip check
.venv\Scripts\czechcore --version
.venv\Scripts\czechcore download
.venv\Scripts\czechcore check "Když přišel domů šel spát."
~~~

Also document source install, CLI/JSON/mechanical automatic/Python API,
benchmark/tests, offline behavior, cache locations, update, rollback, uninstall,
and Windows troubleshooting.

- [ ] **Step 3: Keep confidence wording exact**

State that automatic mode exists, but current beam confidence is not correctness
probability. Use only the exact repeated-word repair as the applied smoke example.

### Task 3: Implement macOS, Linux, and Android guides

**Files:**
- Create: docs/setup/MACOS.md
- Create: docs/setup/LINUX.md
- Create: docs/setup/ANDROID.md

- [ ] **Step 1: Write the macOS guide**

Use curl, shasum -a 256, python3.12, .venv/bin, the public wheel, pip check,
asset download, and real correction. Document Apple Silicon/Intel evidence,
cache, PATH, update/uninstall, and source tests.

- [ ] **Step 2: Write the Linux guide**

Use curl, sha256sum, python3.12, .venv/bin, the public wheel, pip check, asset
download, and real correction. Limit package-manager commands to named
distributions. Document XDG cache and missing venv/native-wheel errors.

- [ ] **Step 3: Write the Android guide**

Start with a caution containing:

~~~text
No APK is available in v0.2.0.
Termux is not supported.
~~~

Document SpellCheckerService, ACTION_PROCESS_TEXT, optional IME, local portable
runtime, modes, privacy, emulator gate, and the exact conditions for future APK
installation instructions. Do not invent package IDs, APK URLs, screenshots, or
Gradle commands.

- [ ] **Step 4: Run the documentation contract test**

Expected: PASS.

### Task 4: Add real cross-platform release verification

**Files:**
- Create: .github/workflows/platform-smoke.yml
- Modify: tests/test_repository.py

- [ ] **Step 1: Add a failing workflow contract test**

Require windows-latest, macos-latest, ubuntu-latest, python -m venv,
czechcore download, and -m model in the workflow text.

- [ ] **Step 2: Run RED**

Expected: FAIL because platform-smoke.yml does not exist.

- [ ] **Step 3: Create the workflow**

The workflow triggers on workflow_dispatch and relevant push paths. A
three-entry include matrix supplies each OS, venv Python path, and installed CLI
path. Every job:

1. checks out the repository;
2. sets Python 3.12;
3. creates .platform-venv;
4. installs the public wheel URL and pytest;
5. runs pip check;
6. runs the installed czechcore download;
7. runs the existing model-marked backend/tokenizer tests;
8. runs suggestion, JSON, protected-text, and repeated-word automatic commands.

Use contents: read and explicit per-OS shell/path values. Do not use a desktop
host service or mock model.

- [ ] **Step 4: Run GREEN**

Expected: workflow contract test passes.

### Task 5: Publish and cross-link

**Files:**
- Modify: README.md
- Modify: docs/README.md
- Modify: CHANGELOG.md

- [ ] **Step 1: Add Install by device to README navigation**

Make release installation the user path and source installation the contributor
path. Link Windows, macOS, Linux, and Android guides.

- [ ] **Step 2: Update documentation index and changelog**

Index the chooser and device guides. Under Unreleased/Added, record device setup
guides and clean desktop real-model verification.

- [ ] **Step 3: Render changed Markdown**

For README, chooser, and all device guides run:

~~~powershell
gh api -X POST markdown -F text=@PATH -f mode=gfm -f context=Majkey25/CzechCore
~~~

Expected: exit 0 with rendered HTML.

### Task 6: Verify locally and publicly

**Files:**
- No production changes unless a gate reveals a root cause.

- [ ] **Step 1: Run local gates**

~~~powershell
.venv\Scripts\python -m pytest
.venv\Scripts\python -m ruff check . --no-cache
.venv\Scripts\python -m ruff format --check .
.venv\Scripts\python -m pyright --pythonpath .venv\Scripts\python.exe
.venv\Scripts\python -m pip check
~~~

Expected: all tests pass, zero Ruff/Pyright errors, no broken requirements.

- [ ] **Step 2: Test the public wheel in a new Windows venv**

Download it from GitHub, verify SHA-256, install dependencies, run pip check,
download/reuse assets, and verify:

~~~text
Když přišel domů šel spát. -> Když přišel domů, šel spát.
Byli doma. -> Byli doma.
Kontakt majkey25@example.cz, verze v1.2.3. -> unchanged
To je je vážný problém. -> To je vážný problém. in explicit automatic mode
~~~

- [ ] **Step 3: Run the acceptance benchmark**

~~~powershell
.venv\Scripts\czechcore-benchmark benchmarks\cases.jsonl --batch-size 16
~~~

Expected: 60/65 exact, 34/38 erroneous corrected, 1/27 correct changed, zero
wrong alternative rewrites. Latency is measured but not fixed.

- [ ] **Step 4: Commit and push focused changes**

Commit documentation/tests separately from workflow changes. Push main. Wait for
both CI and platform smoke on exact HEAD. Inspect failed logs before fixing.

- [ ] **Step 5: Verify public state**

Confirm main equals origin/main, workflow conclusions are success, remote blob
SHAs equal local, every guide renders, the release body links to the chooser,
and Android remains explicitly not released.

### Task 7: Preserve the Android gate

**Files:**
- No placeholder Android application in this plan.

- [ ] **Step 1: Keep the overall all-OS goal open**

Desktop documentation and VM tests may complete. The overall goal remains open
until a portable runtime and Android APK perform local inference and the approved
ADB/emulator matrix passes.

- [ ] **Step 2: Start the separate portable-runtime design from measured evidence**

Measure encoder/decoder export, decoder-with-past, WordPiece, UDPipe range,
beam-search, quantization, output parity, latency, and memory before Android
scaffolding. Reject any path that misses the frozen quality/parity gates.
