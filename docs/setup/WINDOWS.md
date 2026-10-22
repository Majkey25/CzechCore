# Install CzechCore on Windows

## Verified status

CzechCore v0.3.2 supports 64-bit Windows with Python 3.12. The public wheel,
all declared dependencies, pinned model assets, CLI, Python API, real model tests,
and the 65-case benchmark are covered by the release process.

The public v0.3.2 wheel below installs the research engine and CLI. The release
source also contains a native x64/x86 TSF typing service, shared CTranslate2
broker, settings GUI, and UAC-aware source installer payload. Unsigned native
binaries are not distributed as production artifacts. Reproducible instructions:
[`windows/README.md`](../../windows/README.md).

## 1. Install Python

Install 64-bit Python 3.12 from the official
[Python Windows downloads](https://www.python.org/downloads/windows/).
The Python Install Manager or the regular 64-bit installer is suitable.

Open a new PowerShell window:

~~~powershell
py -3.12 --version
~~~

Expected:

~~~text
Python 3.12.x
~~~

If the py command is missing, reopen the terminal after installation. Do not use
the Windows embeddable package; it is not a normal package-management
environment.

## 2. Create an empty installation directory

~~~powershell
New-Item -ItemType Directory -Force -Path CzechCoreRuntime
Set-Location CzechCoreRuntime
~~~

The directory owns the virtual environment and downloaded wheel. It can be
removed later without changing system Python.

## 3. Download and verify the release wheel

~~~powershell
$wheel = "czechcore-0.3.2-py3-none-any.whl"
$url = "https://github.com/Majkey25/CzechCore/releases/download/v0.3.2/$wheel"
Invoke-WebRequest -Uri $url -OutFile $wheel
(Get-FileHash -Algorithm SHA256 $wheel).Hash.ToLowerInvariant()
~~~

Required output:

~~~text
c96f86e2471992b75872c66de5ddbb526f7cc5dcb4cd428f7813c5bab1ff902d
~~~

Stop if the hash differs.

## 4. Create the virtual environment and install

~~~powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install .\czechcore-0.3.2-py3-none-any.whl
.venv\Scripts\python -m pip check
.venv\Scripts\czechcore --version
~~~

Expected final lines:

~~~text
No broken requirements found.
czechcore 0.3.2
~~~

Always call the executable inside .venv. Activation is optional. If preferred:

~~~powershell
.venv\Scripts\Activate.ps1
czechcore --version
~~~

If PowerShell blocks Activate.ps1, do not weaken the machine execution policy;
continue using the explicit .venv\Scripts paths.

## 5. Download pinned Czech models

~~~powershell
.venv\Scripts\czechcore download
~~~

The command prints two paths. A normal Windows result resembles:

~~~text
UDPipe: C:\Users\<user>\AppData\Local\CzechCore\czech-pdt-ud-2.5-191206.udpipe
Transformer: C:\Users\<user>\.cache\huggingface\hub\models--ufal--transformer-base-geccc-mate\snapshots\86338eff14fd318c3e8875c911f0778563b4b3b7
~~~

UDPipe is SHA-256 verified. Transformer files are pinned to the printed revision.
Running download again reuses valid cached files.

## 6. Verify real correction

### Missing comma

~~~powershell
.venv\Scripts\czechcore check "Když přišel domů šel spát."
~~~

Expected:

~~~text
Když přišel domů, šel spát.
~~~

### Agreement

~~~powershell
.venv\Scripts\czechcore check "Muži přišly domů. Ženy šli ven."
~~~

Expected:

~~~text
Muži přišli domů. Ženy šly ven.
~~~

### Correct-text negative

~~~powershell
.venv\Scripts\czechcore check "Byli doma."
~~~

Expected unchanged:

~~~text
Byli doma.
~~~

### Protected technical text

~~~powershell
.venv\Scripts\czechcore check "Kontakt majkey25@example.cz, verze v1.2.3."
~~~

Expected unchanged:

~~~text
Kontakt majkey25@example.cz, verze v1.2.3.
~~~

## 7. Structured JSON for integrations

~~~powershell
.venv\Scripts\czechcore check --json "Když přišel domů šel spát."
~~~

The JSON must contain:

- original_text with the exact input;
- suggested_text with the comma;
- output_text unchanged in suggestion mode;
- one punctuation edit at source offset 16;
- an empty warnings list.

Offsets are Unicode code points. Windows adapters must convert them to UTF-16.

## 8. Experimental automatic application

Use the deterministic adjacent-repeat repair as the smoke case:

~~~powershell
.venv\Scripts\czechcore check --autocorrect --min-confidence 0.90 "To je je vážný problém."
~~~

Expected:

~~~text
To je vážný problém.
~~~

Do not interpret min-confidence as a percentage probability. Neural automatic
application is not approved for silent production use.

## 9. Python API

Create example.py:

~~~python
from czechcore import CzechCore

engine = CzechCore()
result = engine.correct("Když přišel domů šel spát.")

assert result.suggested_text == "Když přišel domů, šel spát."
assert result.output_text == result.original_text
print(result.suggested_text)
~~~

Run:

~~~powershell
.venv\Scripts\python .\example.py
~~~

## 10. Source checkout, benchmark, and tests

For development:

~~~powershell
git clone https://github.com/Majkey25/CzechCore.git
Set-Location CzechCore
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\czechcore download
.venv\Scripts\python -m pytest
.venv\Scripts\czechcore-benchmark benchmarks\cases.jsonl --batch-size 16
~~~

The v0.2.0 acceptance reference is 60/65 exact, 34/38 erroneous inputs corrected,
1/27 correct inputs changed, and zero wrong alternatives. Runtime depends on the
machine.

## 11. Offline verification

After czechcore download succeeds:

1. Run one correction.
2. Disconnect Windows from the network.
3. Run the same command again.

Correction must succeed without a network request. The rewrite command is a
separate feature and requires a local loopback model server.

## 12. Update, rollback, and uninstall

### Update

Create a new venv for a new release instead of modifying the known-good one.
Verify the new release hash, install, download/reuse pinned assets, and run the
four smoke cases above.

### Rollback

Keep the old installation directory until the new version passes. Switch back by
calling the old .venv\Scripts\czechcore executable.

### Uninstall package

~~~powershell
.venv\Scripts\python -m pip uninstall czechcore
~~~

Model caches are intentionally not deleted automatically. Remove them only after
confirming no CzechCore environment needs them:

~~~text
%LOCALAPPDATA%\CzechCore
%USERPROFILE%\.cache\huggingface\hub\models--ufal--transformer-base-geccc-mate
~~~

## Troubleshooting

### AssetMissingError

Run:

~~~powershell
.venv\Scripts\czechcore download
~~~

Do not copy an arbitrary UDPipe/model file into the cache.

### Download fails

- Retry czechcore download.
- Confirm GitHub/Hugging Face HTTPS works in the same account.
- Check proxy and corporate certificate configuration.
- Do not disable TLS certificate verification.

Temporary UDPipe files are not activated unless the expected hash matches.

### Out of memory or slow first run

Model loading and PyTorch use more memory than the 244 MB weight file. Close
memory-heavy applications and retest. No minimum RAM is published until it is
measured across target profiles.

### Czech characters print incorrectly

Use Windows Terminal or current PowerShell. CzechCore configures CLI stdout as
UTF-8. Redirected tools must also preserve UTF-8.

### Wrong Python is used

~~~powershell
py -0p
py -3.12 --version
.venv\Scripts\python --version
~~~

All three must resolve to the intended 64-bit Python 3.12 environment.

## Verification evidence

- Physical Windows v0.2.0 public-wheel install: passed.
- Full dependency pip check: passed.
- Six real-model tests: passed.
- Live suggestion, correct negative, protected text, multi-sentence agreement,
  long-input abstention, and repeated-word automatic scenarios: passed.
- The automated Windows hosted-VM result is linked from the
  [platform smoke workflow](../../.github/workflows/platform-smoke.yml) after it
  completes on the current commit.
