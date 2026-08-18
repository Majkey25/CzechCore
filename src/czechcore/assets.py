from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from pathlib import Path
from urllib.request import urlopen

from huggingface_hub import snapshot_download
from huggingface_hub.errors import LocalEntryNotFoundError

DEFAULT_MODEL_ID = "ufal/transformer-base-geccc-mate"
DEFAULT_MODEL_REVISION = "86338eff14fd318c3e8875c911f0778563b4b3b7"
UDPIPE_FILENAME = "czech-pdt-ud-2.5-191206.udpipe"
UDPIPE_SHA256 = "8ced138bf1c2121cf03d2494f08c663a8b27b5218fb9c322064a7d943ba02266"
UDPIPE_URL = (
    "https://raw.githubusercontent.com/ufal/tsd2025-gec/"
    "9103ac89dfd49a12d71820c301979599cf1a31c0/"
    f"code/src/utils/udpipe_tokenizer/{UDPIPE_FILENAME}"
)
_MODEL_FILES = (
    "README.md",
    "config.json",
    "generation_config.json",
    "model.safetensors",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
)


class AssetMissingError(FileNotFoundError):
    pass


def default_cache_dir() -> Path:
    if local_app_data := os.environ.get("LOCALAPPDATA"):
        return Path(local_app_data) / "CzechCore"
    if xdg_cache_home := os.environ.get("XDG_CACHE_HOME"):
        return Path(xdg_cache_home) / "czechcore"
    return Path.home() / ".cache" / "czechcore"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def local_udpipe_model(cache_dir: Path | None = None) -> Path:
    path = (cache_dir or default_cache_dir()) / UDPIPE_FILENAME
    if not path.is_file() or _sha256(path) != UDPIPE_SHA256:
        raise AssetMissingError("UDPipe model is missing or invalid; run `czechcore download`")
    return path


def download_udpipe_model(cache_dir: Path | None = None) -> Path:
    try:
        return local_udpipe_model(cache_dir)
    except AssetMissingError:
        pass
    destination = (cache_dir or default_cache_dir()) / UDPIPE_FILENAME
    destination.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f"{UDPIPE_FILENAME}.",
        suffix=".tmp",
    )
    os.close(file_descriptor)
    temporary = Path(temporary_name)
    try:
        with urlopen(UDPIPE_URL, timeout=60) as response, temporary.open("wb") as output:
            shutil.copyfileobj(response, output)
        if _sha256(temporary) != UDPIPE_SHA256:
            raise RuntimeError("downloaded UDPipe model failed SHA-256 verification")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def download_transformer_model(cache_dir: Path | None = None) -> Path:
    path = snapshot_download(
        DEFAULT_MODEL_ID,
        revision=DEFAULT_MODEL_REVISION,
        allow_patterns=list(_MODEL_FILES),
        cache_dir=str(cache_dir / "huggingface") if cache_dir else None,
    )
    return Path(path)


def local_transformer_model(cache_dir: Path | None = None) -> Path:
    try:
        path = snapshot_download(
            DEFAULT_MODEL_ID,
            revision=DEFAULT_MODEL_REVISION,
            allow_patterns=list(_MODEL_FILES),
            cache_dir=str(cache_dir / "huggingface") if cache_dir else None,
            local_files_only=True,
        )
    except LocalEntryNotFoundError as error:
        raise AssetMissingError("Transformer model is missing; run `czechcore download`") from error
    return Path(path)


def download_assets(cache_dir: Path | None = None) -> tuple[Path, Path]:
    return download_udpipe_model(cache_dir), download_transformer_model(cache_dir)
