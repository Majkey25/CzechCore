# Security policy

## Supported versions

| Version | Supported |
| --- | --- |
| `0.1.x` | Yes |
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
- CLI arguments can be visible to the local operating system process list. Do not
  pass secrets as correction text.

## Out of scope

- Errors in the linguistic quality of a suggestion are correctness bugs, not
  security vulnerabilities, unless they enable data loss or unauthorized action.
- Vulnerabilities in upstream model data or third-party packages should also be
  reported to their maintainers.
- The default CC BY-NC-SA model license is a licensing constraint, not a security
  mechanism.
