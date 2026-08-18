# Install CzechCore on Linux

## Verified status

CzechCore v0.2.0 is tested in a clean GitHub-hosted Ubuntu x64 virtual machine
with Python 3.12, the public wheel, pinned assets, and real model inference.
Other distributions are supported only when the same Python/native dependency
wheels install successfully.

This installs the Python research engine and CLI. It is not a desktop-wide input
service.

## 1. Install prerequisites

Ubuntu 24.04:

~~~bash
sudo apt-get update
sudo apt-get install -y python3.12 python3.12-venv curl git
python3.12 --version
~~~

Expected:

~~~text
Python 3.12.x
~~~

For another distribution, install a 64-bit CPython 3.12 interpreter and venv
support from the distribution or [python.org](https://www.python.org/downloads/).
Do not translate the Ubuntu package names blindly.

## 2. Download and verify v0.2.0

~~~bash
mkdir -p CzechCoreRuntime
cd CzechCoreRuntime
curl -fL -o czechcore-0.2.0-py3-none-any.whl \
  https://github.com/Majkey25/CzechCore/releases/download/v0.2.0/czechcore-0.2.0-py3-none-any.whl
sha256sum czechcore-0.2.0-py3-none-any.whl
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

Never install CzechCore into the distribution-managed system environment.

## 4. Download pinned assets

~~~bash
.venv/bin/czechcore download
~~~

With no XDG override, the paths are normally:

~~~text
~/.cache/czechcore/czech-pdt-ud-2.5-191206.udpipe
~/.cache/huggingface/hub/models--ufal--transformer-base-geccc-mate/...
~~~

If XDG_CACHE_HOME is set, the UDPipe path is
$XDG_CACHE_HOME/czechcore. The command output is authoritative.

## 5. Real correction smoke

~~~bash
.venv/bin/czechcore check "Když přišel domů šel spát."
.venv/bin/czechcore check "Muži přišly domů. Ženy šli ven."
.venv/bin/czechcore check "Byli doma."
.venv/bin/czechcore check "Kontakt majkey25@example.cz, verze v1.2.3."
~~~

Expected:

~~~text
Když přišel domů, šel spát.
Muži přišli domů. Ženy šly ven.
Byli doma.
Kontakt majkey25@example.cz, verze v1.2.3.
~~~

JSON:

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

Neural automatic use is not production-approved; confidence is beam-relative.

## 6. Python API

Create example.py:

~~~python
from czechcore import CzechCore

result = CzechCore().correct("Když přišel domů šel spát.")
assert result.suggested_text == "Když přišel domů, šel spát."
assert result.output_text == result.original_text
print(result.suggested_text)
~~~

~~~bash
.venv/bin/python ./example.py
~~~

## 7. Source checkout, benchmark, and tests

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

After downloading assets, run a correction, disable network access, and repeat
it. Correction must work from caches. No command should be run as root.

## 9. Update, rollback, and uninstall

Use a new directory and venv for each release. Keep the previous directory until
the new version passes the hash, asset, and model-smoke steps.

~~~bash
.venv/bin/python -m pip uninstall czechcore
~~~

Package removal preserves model caches. Remove them manually only after checking
that no environment uses them:

~~~text
$XDG_CACHE_HOME/czechcore or ~/.cache/czechcore
~/.cache/huggingface/hub/models--ufal--transformer-base-geccc-mate
~~~

## Troubleshooting

### ensurepip or venv is unavailable

Install the distribution's Python 3.12 venv package. On Ubuntu 24.04 it is
python3.12-venv.

### No compatible ufal.udpipe or torch wheel

Record:

~~~bash
uname -a
uname -m
python3.12 --version
ldd --version
~~~

The required hosted matrix is Ubuntu x64. Other architectures remain unverified
until their own successful runs exist.

### HTTPS/certificate/proxy failure

Repair the system CA store or configured HTTPS proxy. Never add a flag that
disables certificate verification.

### Process is killed during model load

Check kernel logs and available memory. The 244 MB model weights plus PyTorch and
working buffers require more memory than the weight size alone. No unsupported
swap or minimum-RAM claim is prescribed.

## Verification evidence

The current commit must pass the
[platform smoke workflow](../../.github/workflows/platform-smoke.yml) on
ubuntu-latest with a fresh venv, public wheel, pip check, real assets, six model
tests, and live CLI scenarios.
