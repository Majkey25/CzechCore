# Install CzechCore on macOS

## Verified status

CzechCore v0.2.0 is tested in a clean GitHub-hosted Apple Silicon macOS virtual
machine with Python 3.12, the public release wheel, pinned model assets, and real
model inference. Intel macOS is not claimed until an Intel matrix run exists.

This installs the Python research engine and CLI, not a native menu-bar or
system-wide spelling application.

## 1. Install Python 3.12

Use the official
[Python macOS downloads](https://www.python.org/downloads/macos/). The universal2
installer supports Apple Silicon and Intel.

Open Terminal:

~~~bash
python3.12 --version
~~~

Expected:

~~~text
Python 3.12.x
~~~

Do not use the old Apple-provided system Python.

## 2. Download and verify v0.2.0

~~~bash
mkdir -p CzechCoreRuntime
cd CzechCoreRuntime
curl -fL -o czechcore-0.2.0-py3-none-any.whl \
  https://github.com/Majkey25/CzechCore/releases/download/v0.2.0/czechcore-0.2.0-py3-none-any.whl
shasum -a 256 czechcore-0.2.0-py3-none-any.whl
~~~

Required hash:

~~~text
8d1aab92dce9d854e15f18107f3f987edf7d49806efa24759994717396412621
~~~

Stop if it differs.

## 3. Create a clean venv and install

~~~bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install ./czechcore-0.2.0-py3-none-any.whl
.venv/bin/python -m pip check
.venv/bin/czechcore --version
~~~

Expected:

~~~text
No broken requirements found.
czechcore 0.2.0
~~~

## 4. Download pinned assets

~~~bash
.venv/bin/czechcore download
~~~

The command prints exact locations. Unless XDG_CACHE_HOME overrides them, the
project cache is ~/.cache/czechcore and the Transformer uses the standard
~/.cache/huggingface/hub cache.

Approximately 300 MB of Czech model assets are required. PyTorch dependencies
need additional space.

## 5. Real correction smoke

~~~bash
.venv/bin/czechcore check "Když přišel domů šel spát."
.venv/bin/czechcore check "Muži přišly domů. Ženy šli ven."
.venv/bin/czechcore check "Byli doma."
.venv/bin/czechcore check "Kontakt majkey25@example.cz, verze v1.2.3."
~~~

Expected, in the same order:

~~~text
Když přišel domů, šel spát.
Muži přišli domů. Ženy šly ven.
Byli doma.
Kontakt majkey25@example.cz, verze v1.2.3.
~~~

Structured output:

~~~bash
.venv/bin/czechcore check --json "Když přišel domů šel spát."
~~~

Mechanical automatic smoke:

~~~bash
.venv/bin/czechcore check --autocorrect --min-confidence 0.90 \
  "To je je vážný problém."
~~~

Expected:

~~~text
To je vážný problém.
~~~

The threshold is a research control, not a probability of correctness.

## 6. Python API

Create example.py:

~~~python
from czechcore import CzechCore

result = CzechCore().correct("Když přišel domů šel spát.")
assert result.suggested_text == "Když přišel domů, šel spát."
assert result.output_text == result.original_text
print(result.suggested_text)
~~~

Run:

~~~bash
.venv/bin/python ./example.py
~~~

## 7. Development checkout and complete tests

~~~bash
git clone https://github.com/Majkey25/CzechCore.git
cd CzechCore
python3.12 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/czechcore download
.venv/bin/python -m pytest
.venv/bin/czechcore-benchmark benchmarks/cases.jsonl --batch-size 16
~~~

## 8. Offline verification

After the download completes, run a correction, disable Wi-Fi/network access,
and repeat it. The same correction must work without downloading. The optional
rewrite command still requires a local loopback model server.

## 9. Update, rollback, and uninstall

Install each new release into a new directory/venv, verify its published hash,
then run the model smoke before deleting the old environment.

~~~bash
.venv/bin/python -m pip uninstall czechcore
~~~

Package uninstall does not delete model caches. After confirming no environment
uses them, the relevant directories are:

~~~text
~/.cache/czechcore
~/.cache/huggingface/hub/models--ufal--transformer-base-geccc-mate
~~~

Respect XDG_CACHE_HOME if it was configured.

## Troubleshooting

### python3.12 is missing

Install the official 3.12 universal2 package and open a new Terminal. Verify:

~~~bash
command -v python3.12
python3.12 --version
~~~

### Native dependency has no compatible wheel

Record:

~~~bash
uname -m
sw_vers
python3.12 --version
~~~

Apple Silicon verification uses macos-latest arm64. Intel support is not claimed
without a separate successful run.

### Certificate or proxy error

Fix the system/Python certificate or proxy trust. Do not disable TLS
verification. Retry czechcore download after HTTPS access is repaired.

### Slow first run or memory pressure

The 244 MB model weight file is only part of the runtime; PyTorch and working
buffers add memory. Close heavy applications. No minimum RAM claim is published
until physical-device measurements exist.

## Verification evidence

The current commit must pass the
[platform smoke workflow](../../.github/workflows/platform-smoke.yml) on
macos-latest with:

- a fresh venv;
- public v0.2.0 wheel installation;
- pip check;
- pinned asset download;
- six model tests;
- live CLI scenarios.

This is hosted-VM evidence, not a claim of testing every physical Mac model.
