# ADR-0003: Keep model assets outside the MIT-licensed wheel

## Status

Accepted

## Date

2026-08-18

## Context

CzechCore code can be permissively licensed, but the selected Transformer and
UDPipe model assets are CC BY-NC-SA 4.0. Bundling them would blur license scope,
increase wheel size, and complicate replacement.

## Decision

- License CzechCore source under MIT.
- Distribute code-only wheels.
- Download pinned assets only through an explicit command.
- Record asset sources, revisions, hashes, and licenses in `NOTICE.md`.
- Keep inference local-only after provisioning.

## Alternatives considered

### Bundle assets in the repository or wheel

Rejected because of size, provenance, and license-boundary ambiguity.

### Download assets silently on first correction

Rejected because it breaks the explicit offline/privacy contract and hides a
large network operation inside inference.

### Claim the whole product is MIT

Rejected. The runtime code and default linguistic assets have different licenses.

## Consequences

- Installation requires a separate `czechcore download` step.
- Default assets are non-commercial even though the code is MIT.
- Commercial use requires separately licensed or replacement data/model assets.
- Device packages must preserve attribution and license separation.
