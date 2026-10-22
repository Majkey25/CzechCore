# CzechCore Windows live-text integration

This directory builds a native Windows typing integration. End users run the
setup executable and settings UI; Python and a terminal are not used at runtime.

## Components

| Component | Purpose |
| --- | --- |
| `czechcore-engine.exe` | One x64 CTranslate2 model process per logon session |
| `CzechCoreTsf.dll` | Thin in-process TSF service; built for x64 and x86 |
| `czechcore-settings.exe` | Native `off / underline / automatic` settings UI |
| `CzechCoreSetup.exe` | Payload shape check, UAC install, TSF registration, Start shortcut |

The TSF DLL never loads the model inside editors. It communicates through
randomly named local pipes, whose ACL allows only the current user and `SYSTEM`.
Discovery, readiness, and the instance mutex live in a Windows private namespace
bounded by the current user and logon SIDs. The broker publishes its pipe name
after creating it and keeps the pipe handle open between requests. Pipes reject
remote clients, cap messages at 16 KiB, and time out stalled I/O after five seconds.
Clients verify the broker process image, user SID, and logon SID before sending text.
TSF activation preloads a single mutex-protected broker; ten idle minutes release
the measured 306.82 MiB working set.

## User behavior

- End a sentence with `.`, `!`, or `?` to schedule a local check.
- `Ctrl+Alt+G` checks the current sentence immediately.
- `Ctrl+Alt+Enter` applies the underlined candidate after exact source validation.
- Automatic mode silently removes only one exact adjacent duplicate. Neural
  punctuation/agreement edits still require confirmation.
- URL, path, email/login, password, private, and PIN input scopes are excluded.

## Build

Requirements: Visual Studio Build Tools with C++, Windows SDK, CMake, the pinned
CTranslate2 4.8.1 checkout, and the converted FP32 model.

Configure/build the x64 broker and TSF service:

~~~powershell
cmake -S windows -B build\windows-x64 -A x64 -DCZECHCORE_BUILD_ENGINE=ON -DCT2_SOURCE_DIR=C:\czechcore-ct2 "-DCMAKE_POLICY_VERSION_MINIMUM=3.5"
cmake --build build\windows-x64 --config Release --target czechcore-engine czechcore-tsf czechcore-settings czechcore-setup
~~~

Build the 32-bit TSF adapter without a second model process:

~~~powershell
cmake -S windows -B build\windows-x86 -A Win32
cmake --build build\windows-x86 --config Release --target czechcore-tsf
~~~

Assemble the setup payload:

~~~text
CzechCoreSetup.exe
czechcore-engine.exe
czechcore-settings.exe
model/config.json
model/model.bin
model/shared_vocabulary.json
x64/CzechCoreTsf.dll
x86/CzechCoreTsf.dll
~~~

`CzechCoreSetup.exe --verify` checks that every required payload file exists and
is non-empty without elevation. It does not authenticate unsigned files; a
production package still requires Authenticode signing. Double-click setup for
installation; Windows displays the normal UAC consent dialog because TSF profile
registration is machine-scoped. After installation, select CzechCore in the
Windows input-language switcher and open **CzechCore nastavení** from Start.

## Verification completed on 2026-08-19

- MSVC C++20 `/W4 /WX` x64 and x86 TSF builds passed.
- Native UTF-8/UTF-16, WordPiece, automatic-repair, and protected-literal tests passed.
- FP32 native broker produced the required comma/agreement results and preserved
  correct/protected text.
- A real `ITfThreadMgr`/`ITfContext` host passed automatic and explicit-confirm
  edit-session flows, including a cold broker start.
- Ten warm local requests measured 159.92 ms median and 170.96 ms p95 end-to-end.
- Rogue pipe ownership, stalled-client recovery, 16 KiB rejection, and protected
  literal security scenarios passed.
- Setup payload verification passed.

The elevated machine-profile install, Notepad/Office/Chromium matrix, Windows
password input-scope flow, code signing, and installer rollback are still release
gates. The current setup is source evidence, not a signed public release.
