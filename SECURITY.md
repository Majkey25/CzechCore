# Security policy

## Supported versions

| Version | Supported |
| --- | --- |
| `0.3.x` | Yes |
| `0.2.x` | Security fixes only |
| Older or untagged snapshots | No guarantee |

## Reporting

Do not open a public issue for a suspected vulnerability. Use a
[private GitHub security advisory](https://github.com/Majkey25/CzechCore/security/advisories/new)
and include:

- affected version and operating system;
- minimal reproduction;
- expected and observed behavior;
- whether user text, model assets, or filesystem paths are exposed;
- any proposed mitigation.

## Security and privacy boundaries

- Text correction runs locally. User text is not sent to UFAL, Hugging Face,
  GitHub, or CzechCore services.
- Remote network access occurs only through explicit asset provisioning.
- Experimental rewrite calls accept only loopback HTTP (`127.0.0.1` or `::1`)
  and refuse redirects. The operator must trust the local model
  server process because it receives the source text.
- The Transformer snapshot is pinned to a Git revision and loaded with
  `local_files_only=True`; remote model code is not executed.
- The UDPipe model is downloaded over HTTPS and accepted only after SHA-256
  verification.
- Model and tokenizer files are untrusted external inputs until those checks pass.
- The Android IME requests no network permission, skips password/private/URI/email
  fields, bounds model assets and pending inference work, and never logs raw text.
- The Windows broker pipe is local-only, restricted to the current user and
  `SYSTEM`, limited to 16 KiB, bounded by 5-second I/O timeouts, and checked
  against the configured broker process image before text is sent.
- The Windows broker accepts one instance per user, preloads once, and exits after
  10 minutes without a client. It records operation errors only, never raw text.
- CodeQL security-extended scans C/C++, Java, and Python on pushes, pull requests,
  and a weekly schedule.
- CLI arguments can be visible to the local operating system process list. Do not
  pass secrets as correction text.

## Out of scope

- Errors in the linguistic quality of a suggestion are correctness bugs, not
  security vulnerabilities, unless they enable data loss or unauthorized action.
- Vulnerabilities in upstream model data or third-party packages should also be
  reported to their maintainers.
- The default CC BY-NC-SA model license is a licensing constraint, not a security
  mechanism.
- A process already running as the same operating-system user remains inside the
  local trust boundary. Native setup/APK artifacts are not production releases
  until code signing and model-update verification are complete.
