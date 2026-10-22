# Install CzechCore by device

This is the supported path from a clean machine to a verified Czech correction.
Choose your operating system:

- [Windows](setup/WINDOWS.md)
- [macOS](setup/MACOS.md)
- [Linux](setup/LINUX.md)
- [Android](setup/ANDROID.md)

## Support matrix

| Platform | v0.3.1 status | Installation | Verification |
| --- | --- | --- | --- |
| Windows x64 | Supported research runtime | Python wheel in a venv | Physical Windows + hosted VM |
| macOS Apple Silicon | Supported when the dependency wheels install | Python wheel in a venv | Hosted arm64 macOS VM |
| macOS Intel | Expected dependency support, not yet a required matrix target | Python wheel in a venv | Not claimed until a run exists |
| Linux x64 | Supported research runtime | Python wheel in a venv | Hosted Ubuntu x64 VM |
| Android arm64 | Source debug probe only | No published APK is available | x86_64 emulator flow + arm64 build; text services remain blocked |

Windows, macOS, and Linux run the same Python reference engine. Android is a
different deployment target and cannot run the desktop wheel as a keyboard or
spell checker.

## What you need

- 64-bit Python 3.12. Python 3.13 and 3.14 are also package-tested, but 3.12 is
  the reference release environment.
- Internet access once for the wheel, Python dependencies, and pinned model
  assets.
- Approximately 300 MB for CzechCore model assets. PyTorch and its dependencies
  require additional storage.
- CPU inference. A GPU is not required.

Use the official [Python downloads](https://www.python.org/downloads/) and verify:

~~~text
python --version
Python 3.12.x
~~~

The exact command is platform-specific and shown in each guide.

## Release artifact

Release: [CzechCore v0.3.1](https://github.com/Majkey25/CzechCore/releases/tag/v0.3.1)

Wheel:

~~~text
czechcore-0.3.1-py3-none-any.whl
~~~

Expected SHA-256:

~~~text
fe4ad6fd089f85d58d3c092dcae839fef9052ca545cc96e7ff6ea9d44863eb4e
~~~

Do not install a wheel with a different hash unless a different published release
documents that hash.

## Common verification result

After installation and czechcore download, run:

~~~text
czechcore check "Když přišel domů šel spát."
~~~

Expected:

~~~text
Když přišel domů, šel spát.
~~~

Suggestion mode prints the proposed correction. The structured API keeps the
original output unchanged unless the caller explicitly requests application.

## First-run downloads and offline use

czechcore download installs:

- the pinned 60.8M-parameter Czech Transformer, about 244 MB of weights;
- the hash-verified Czech UDPipe tokenizer model;
- tokenizer/configuration files pinned by model revision.

The command prints the exact cache paths. After it succeeds, correction uses
local files only. Missing assets fail explicitly instead of downloading during a
correction request.

To verify the offline boundary:

1. Run czechcore download while connected.
2. Run the stable correction once.
3. Disconnect the network.
4. Run the same correction again.

The second correction must produce the same result without a download.

## Modes

| Mode | Command/API | Safety status |
| --- | --- | --- |
| Suggestion | czechcore check | Default; never mutates another application |
| Structured JSON | czechcore check --json | Exact edit ranges and warnings |
| Experimental apply | --autocorrect --min-confidence VALUE | Explicit research control, not calibrated correctness |
| Rewrite | czechcore rewrite | Requires a separately configured local server and human review |

The current scalar confidence cannot support production-grade silent
autocorrection. See [confidence evidence](research/CONFIDENCE_AND_ABSTENTION.md).

## User installation versus development

Use the release wheel if you want to run CzechCore.

Clone the repository and install the development extras only if you want tests,
benchmarks, research tools, or code changes:

~~~text
git clone https://github.com/Majkey25/CzechCore.git
cd CzechCore
python -m venv .venv
<venv-python> -m pip install -e ".[dev]"
~~~

Replace <venv-python> with the exact path in your device guide.

## Where to continue

- [Complete API and CLI reference](API.md)
- [Scientific report](RESEARCH_REPORT.md)
- [Evaluation and measured quality](EVALUATION.md)
- [Windows/Android platform architecture](PLATFORM_INTEGRATION.md)
- [Licenses and model boundary](../NOTICE.md)
- [Security and local endpoint rules](../SECURITY.md)
