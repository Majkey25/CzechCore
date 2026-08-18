from pathlib import Path

def snapshot_download(
    repo_id: str,
    *,
    revision: str | None = ...,
    allow_patterns: list[str] | str | None = ...,
    cache_dir: str | Path | None = ...,
    local_files_only: bool = ...,
) -> str: ...
