# CzechCore Android IME and local runtime

This directory builds the source-only CzechCore keyboard used by the Android
emulator evidence. It is a real `InputMethodService`, but not yet a signed public
APK or Play Store release.

## Verified configuration

| Component | Version |
| --- | --- |
| Android Gradle Plugin | 9.2.0 |
| Gradle wrapper | 9.7.0 |
| Java | 17 |
| compile / target SDK | 36 / 36 |
| minimum SDK | 26 |
| NDK | 28.2.13676358 |
| app CMake | 3.22.1 |
| CTranslate2 | 4.8.1 at 0d8bcd362ac75ef860ef161d6f0efad0ae439ff0 |
| package | cz.czechcore.app |

The repository intentionally excludes converted model files and compiled
CTranslate2 libraries.

## 1. Prepare Python tools and the reference model

From the repository root on Windows:

~~~powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -e ".[portable]"
.venv\Scripts\czechcore download
~~~

Copy the Transformer path printed by download, then convert it:

~~~powershell
.venv\Scripts\python -m tools.portable.convert_model --model "<printed-transformer-snapshot>" --output ".reference\tmp\ct2-fp32" --quantization float32
~~~

INT8 is not the default: it changed the required Kdy přijdeš? result in the
measured screen.

## 2. Get the pinned CTranslate2 source

Use a short local path on Windows to avoid third-party filename limits. CUDA
submodules are not needed:

~~~powershell
git clone --branch v4.8.1 --depth 1 --no-recurse-submodules https://github.com/OpenNMT/CTranslate2.git C:\czechcore-ct2
git -C C:\czechcore-ct2 submodule update --init --recursive third_party/spdlog third_party/ruy third_party/cpu_features
git -C C:\czechcore-ct2 apply "<czechcore-repo>\android\patches\ctranslate2-4.8.1-android-affinity.patch"
~~~

The patch only prevents an unsupported Android call to
pthread_setaffinity_np; default affinity remains disabled.

## 3. Build the Android runtime

Create one build directory per ABI. x86_64 is used by the current emulator:

~~~powershell
.venv\Scripts\cmake -S C:\czechcore-ct2 -B .reference\tmp\ct2-android-x86_64 -G Ninja -DCMAKE_MAKE_PROGRAM=<czechcore-repo>\.venv\Scripts\ninja.exe -DCMAKE_TOOLCHAIN_FILE=<android-sdk>\ndk\28.2.13676358\build\cmake\android.toolchain.cmake -DANDROID_ABI=x86_64 -DANDROID_PLATFORM=android-26 -DWITH_MKL=OFF -DWITH_DNNL=OFF -DWITH_OPENBLAS=OFF -DWITH_ACCELERATE=OFF -DWITH_RUY=ON -DWITH_CUDA=OFF -DOPENMP_RUNTIME=NONE -DBUILD_SHARED_LIBS=ON -DBUILD_CLI=OFF -DBUILD_TESTS=OFF -DENABLE_CPU_DISPATCH=ON
.venv\Scripts\cmake --build .reference\tmp\ct2-android-x86_64 --parallel
~~~

Repeat with ANDROID_ABI=arm64-v8a and a separate
.reference\tmp\ct2-android-arm64 build directory for physical devices.

Strip and copy each library:

~~~powershell
New-Item -ItemType Directory -Force android\local-libs\x86_64
<ndk-llvm-strip> -o android\local-libs\x86_64\libctranslate2.so .reference\tmp\ct2-android-x86_64\libctranslate2.so
~~~

Use android\local-libs\arm64-v8a for the arm64 library. These directories are
ignored by Git.

## 4. Configure and build the app

Create ignored android\local.properties:

~~~text
sdk.dir=C:/path/to/Android/Sdk
~~~

Install SDK Platform 36, NDK 28.2.13676358, and CMake 3.22.1, then run:

~~~powershell
android\gradlew.bat -p android :app:testDebugUnitTest :app:assembleDebug -Pct2IncludeDir=C:/czechcore-ct2/include
~~~

The APK is:

~~~text
android/app/build/outputs/apk/debug/app-debug.apk
~~~

## 5. Install and provision the local model

~~~powershell
adb -s <emulator> install -r android\app\build\outputs\apk\debug\app-debug.apk
adb -s <emulator> shell am start -n cz.czechcore.app/.MainActivity
adb -s <emulator> shell mkdir -p /sdcard/Android/data/cz.czechcore.app/files/model
adb -s <emulator> push .reference\tmp\ct2-fp32\config.json /sdcard/Android/data/cz.czechcore.app/files/model/
adb -s <emulator> push .reference\tmp\ct2-fp32\shared_vocabulary.json /sdcard/Android/data/cz.czechcore.app/files/model/
adb -s <emulator> push .reference\tmp\ct2-fp32\model.bin /sdcard/Android/data/cz.czechcore.app/files/model/
~~~

Enable and select the keyboard:

~~~powershell
adb -s <emulator> shell ime enable cz.czechcore.app/.CzechCoreImeService
adb -s <emulator> shell ime set cz.czechcore.app/.CzechCoreImeService
~~~

Without adb, open the CzechCore launcher and use the two system-settings buttons.
The launcher also changes `off / underline / confirm / automatic` mode.

The model is external only for source/debug provisioning. It stays in the app's
scoped external directory; the APK has no network permission and does not
download assets. Files are still treated as untrusted: config is capped at 64
KiB, vocabulary at 8 MiB, model weights at 512 MiB, and empty files are rejected.

## 6. Run the verified app probe

~~~powershell
adb -s <emulator> shell am force-stop cz.czechcore.app
adb -s <emulator> shell am start -n cz.czechcore.app/.MainActivity --ez run true
~~~

Expected UI:

~~~text
input:  Když přišel domů šel spát.
status: Correction complete.
output: Když přišel domů, šel spát.
~~~

Unit tests cover WordPiece behavior and protected literal rejection. The emulator
matrix also verified agreement, a correct negative, and exact fallback when the
raw model damaged an email/version.

## 7. Run the verified keyboard flow

1. Focus a normal text field in any app.
2. Type a sentence or press space after existing text.
3. CzechCore analyzes only the bounded sentence around the caret.
4. Tap the candidate to apply it; tap **Zpět** to restore the exact source.

Verified on Android 35:

- missing comma candidate, visible underline, apply, and undo;
- automatic adjacent-duplicate removal;
- cross-app correction inside Android Settings search;
- Chrome URL field reported `Soukromé pole – korekce vypnuta`;
- no final crash-buffer entry and no raw-text application logging.

The engine keeps one running inference plus at most one latest pending request;
rapid typing cannot grow an unbounded queue. After FP32 inference, the Android 35
x86_64 emulator measured 365,814 KiB PSS / 439,824 KiB RSS. This validates the
bound but remains too large for a production phone claim without physical arm64
profiling or a quality-approved smaller model.

## Remaining product work

- exact UDPipe sentence/token ranges;
- complete tokenizer parity and emoji/UTF-16 edit offsets;
- structured edits rather than whole-sentence display;
- signed model download/update/rollback;
- ACTION_PROCESS_TEXT and SpellCheckerService compatibility surfaces;
- signed/bundled or user-importable model delivery without adb;
- migration from the functional validation layout to a maintained mature keyboard;
- release signing, physical-device performance, battery, and thermal tests.

See [the measured portable runtime report](../docs/research/PORTABLE_RUNTIME_RESEARCH.md).
