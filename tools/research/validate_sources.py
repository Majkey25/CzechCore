from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Literal, NotRequired, TypedDict, cast

SourceKind = Literal["collection", "dataset", "file", "git", "model_card", "pdf"]
KINDS: set[str] = {"collection", "dataset", "file", "git", "model_card", "pdf"}
SHA256 = re.compile(r"^[0-9a-f]{64}$")
REVISION = re.compile(r"^[0-9a-f]{40}$")
IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._-]+$")


class Source(TypedDict):
    id: str
    kind: SourceKind
    title: str
    url: str
    local_path: str
    license: str
    redistribution: str
    purpose: str
    sha256: NotRequired[str]
    revision: NotRequired[str]
    count: NotRequired[int]
    manifest_path: NotRequired[str]
    manifest_sha256: NotRequired[str]


def load_manifest(path: Path) -> dict[str, object]:
    loaded: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("research manifest must be a JSON object")
    return cast(dict[str, object], loaded)


def _required_string(item: Mapping[str, object], field: str, source_id: str) -> str:
    value = item.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{source_id}: {field} must be a non-empty string")
    return value


def validate_manifest(manifest: Mapping[str, object]) -> tuple[Source, ...]:
    if manifest.get("schema_version") != 1:
        raise ValueError("research manifest schema_version must be 1")
    raw_sources = manifest.get("sources")
    if not isinstance(raw_sources, list):
        raise ValueError("research manifest sources must be a list")

    sources: list[Source] = []
    identifiers: set[str] = set()
    for index, raw_source in enumerate(cast(list[object], raw_sources)):
        if not isinstance(raw_source, dict):
            raise ValueError(f"source {index} must be an object")
        item = cast(dict[str, object], raw_source)
        source_id = _required_string(item, "id", f"source {index}")
        if not IDENTIFIER.fullmatch(source_id):
            raise ValueError(f"{source_id}: invalid source id")
        if source_id in identifiers:
            raise ValueError(f"{source_id}: duplicate source id")
        identifiers.add(source_id)

        kind_text = _required_string(item, "kind", source_id)
        if kind_text not in KINDS:
            raise ValueError(f"{source_id}: unsupported kind {kind_text}")
        kind = cast(SourceKind, kind_text)
        source: Source = {
            "id": source_id,
            "kind": kind,
            "title": _required_string(item, "title", source_id),
            "url": _required_string(item, "url", source_id),
            "local_path": _required_string(item, "local_path", source_id),
            "license": _required_string(item, "license", source_id),
            "redistribution": _required_string(item, "redistribution", source_id),
            "purpose": _required_string(item, "purpose", source_id),
        }
        if not source["url"].startswith("https://"):
            raise ValueError(f"{source_id}: source URL must use HTTPS")

        if kind in {"dataset", "file", "pdf"}:
            checksum = _required_string(item, "sha256", source_id).lower()
            if not SHA256.fullmatch(checksum):
                raise ValueError(f"{source_id}: invalid SHA-256")
            source["sha256"] = checksum
        elif kind in {"git", "model_card"}:
            revision = _required_string(item, "revision", source_id).lower()
            if not REVISION.fullmatch(revision):
                raise ValueError(f"{source_id}: invalid revision")
            source["revision"] = revision
        else:
            checksum = _required_string(item, "sha256", source_id).lower()
            manifest_path = _required_string(item, "manifest_path", source_id)
            manifest_checksum = _required_string(item, "manifest_sha256", source_id).lower()
            count = item.get("count")
            if not SHA256.fullmatch(checksum) or not SHA256.fullmatch(manifest_checksum):
                raise ValueError(f"{source_id}: invalid collection SHA-256")
            if not isinstance(count, int) or count <= 0:
                raise ValueError(f"{source_id}: collection count must be positive")
            source["sha256"] = checksum
            source["manifest_path"] = manifest_path
            source["manifest_sha256"] = manifest_checksum
            source["count"] = count
        sources.append(source)
    return tuple(sources)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def validate_cache(sources: Sequence[Source], cache_root: Path) -> None:
    model_manifest_path = cache_root / "model-cards-manifest.json"
    model_entries: dict[str, str] = {}
    if model_manifest_path.is_file():
        loaded: object = json.loads(model_manifest_path.read_text(encoding="utf-8"))
        if isinstance(loaded, list):
            for raw_entry in cast(list[object], loaded):
                if isinstance(raw_entry, dict):
                    entry = cast(dict[str, object], raw_entry)
                    model_id, revision = entry.get("model_id"), entry.get("revision")
                    if isinstance(model_id, str) and isinstance(revision, str):
                        model_entries[model_id] = revision

    for source in sources:
        path = cache_root / source["local_path"]
        kind = source["kind"]
        if kind in {"dataset", "file", "pdf"}:
            checksum = source.get("sha256")
            if checksum is None or not path.is_file() or _sha256(path) != checksum:
                raise ValueError(f"{source['id']}: missing or mismatched file {path}")
        elif kind == "git":
            revision = source.get("revision")
            if revision is None:
                raise ValueError(f"{source['id']}: missing Git revision")
            completed = subprocess.run(
                ["git", "-C", str(path), "rev-parse", "HEAD"],
                check=False,
                capture_output=True,
                text=True,
            )
            if completed.returncode or completed.stdout.strip() != revision:
                raise ValueError(f"{source['id']}: Git revision mismatch")
        elif kind == "model_card":
            revision = source.get("revision")
            if revision is None:
                raise ValueError(f"{source['id']}: missing model-card revision")
            model_id = source["url"].removeprefix("https://huggingface.co/")
            if not path.is_dir() or model_entries.get(model_id) != revision:
                raise ValueError(f"{source['id']}: model-card revision mismatch")
        else:
            manifest_relative = source.get("manifest_path")
            checksum = source.get("sha256")
            manifest_checksum = source.get("manifest_sha256")
            count = source.get("count")
            if (
                manifest_relative is None
                or checksum is None
                or manifest_checksum is None
                or count is None
            ):
                raise ValueError(f"{source['id']}: incomplete collection metadata")
            manifest_path = cache_root / manifest_relative
            if not path.is_file() or _sha256(path) != checksum:
                raise ValueError(f"{source['id']}: collection index mismatch")
            if not manifest_path.is_file() or _sha256(manifest_path) != manifest_checksum:
                raise ValueError(f"{source['id']}: collection manifest mismatch")
            loaded_collection: object = json.loads(manifest_path.read_text(encoding="utf-8"))
            if (
                not isinstance(loaded_collection, list)
                or len(cast(list[object], loaded_collection)) != count
            ):
                raise ValueError(f"{source['id']}: collection count mismatch")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="validate-research-sources")
    parser.add_argument("--manifest", type=Path, default=Path("research/sources.json"))
    parser.add_argument("--cache", type=Path, default=Path(".reference/research"))
    parser.add_argument("--schema-only", action="store_true")
    arguments = parser.parse_args(argv)
    manifest = cast(Path, arguments.manifest)
    cache = cast(Path, arguments.cache)
    sources = validate_manifest(load_manifest(manifest))
    if not cast(bool, arguments.schema_only):
        validate_cache(sources, cache)
    print(f"research_sources={len(sources)}")
    print(f"cache_verified={not cast(bool, arguments.schema_only)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
