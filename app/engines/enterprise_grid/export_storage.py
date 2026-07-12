"""FINAL-L5-05S — Private export file storage.

A purpose-built, private-by-default storage helper for generated export
files. Deliberately NOT reusing `app/engines/media/storage.py`
(`MediaStorageService`), whose local driver writes into `uploads/` (a
directory mounted as public static files via FastAPI StaticFiles) and is
designed around a `public_url`/`is_public` model -- the opposite of this
mission's "files must be private, storage paths must not be returned
directly" requirement. Export files are written to a directory that is
never mounted as static files and are only ever reachable through the
authorized download endpoint in `router.py`.

Local filesystem only this sprint (no S3/Cloudflare R2 credentials are
configured in this environment -- confirmed via `get_settings()`).
`upload_private`/`exists`/`get_metadata`/`delete` form the interface a
future S3-backed implementation would need to satisfy; swapping drivers
later does not require call-site changes.
"""
from __future__ import annotations

import hashlib
import pathlib
import re
import secrets
import uuid
from dataclasses import dataclass

# Never inside a StaticFiles-mounted directory (uploads/, static/, public/).
EXPORTS_DIR = pathlib.Path("var") / "exports"

_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]")


def sanitize_filename(name: str) -> str:
    """Strip anything that isn't alnum/dot/dash/underscore and collapse
    path separators -- prevents path traversal and unsafe characters
    regardless of what a caller (or a resource label) supplies."""
    base = pathlib.Path(name).name  # drop any directory components
    cleaned = _SAFE_FILENAME_RE.sub("_", base)
    return cleaned or "export"


@dataclass
class StoredExportFile:
    storage_key: str
    filename: str
    content_type: str
    file_size: int
    checksum: str


class ExportStorageService:
    """upload_private / exists / get_metadata / delete -- the interface a
    future S3/R2-backed implementation must satisfy."""

    def __init__(self) -> None:
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    def _key_to_path(self, storage_key: str) -> pathlib.Path:
        # storage_key is always server-generated (see upload_private) --
        # still defensively reject traversal if ever called with an
        # untrusted value.
        if ".." in storage_key or storage_key.startswith("/") or storage_key.startswith("\\"):
            raise ValueError("invalid storage_key")
        return EXPORTS_DIR / storage_key

    def upload_private(
        self, job_id: uuid.UUID, tenant_scope: uuid.UUID | None,
        filename: str, content: bytes, content_type: str,
    ) -> StoredExportFile:
        safe_name = sanitize_filename(filename)
        tenant_segment = str(tenant_scope) if tenant_scope else "platform"
        # exports/{tenant_scope}/{job_id}/{opaque_token}-{safe_filename}
        # -- the job_id is part of the path (rule: "Job ID is included"),
        # an opaque random token additionally prevents key-guessing even
        # if a caller somehow learned the job_id and tenant, and the
        # tenant segment is NOT relied upon as the sole authorization
        # boundary (the download endpoint independently re-checks scope).
        token = secrets.token_hex(16)
        rel_dir = pathlib.Path(tenant_segment) / str(job_id)
        storage_key = str(rel_dir / f"{token}-{safe_name}")
        abs_path = self._key_to_path(storage_key)
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_bytes(content)
        checksum = hashlib.sha256(content).hexdigest()
        return StoredExportFile(
            storage_key=storage_key, filename=safe_name,
            content_type=content_type, file_size=len(content), checksum=checksum,
        )

    def exists(self, storage_key: str) -> bool:
        try:
            return self._key_to_path(storage_key).is_file()
        except ValueError:
            return False

    def get_metadata(self, storage_key: str) -> dict | None:
        path = self._key_to_path(storage_key)
        if not path.is_file():
            return None
        stat = path.stat()
        return {"file_size": stat.st_size}

    def read_bytes(self, storage_key: str) -> bytes:
        return self._key_to_path(storage_key).read_bytes()

    def delete(self, storage_key: str) -> bool:
        try:
            path = self._key_to_path(storage_key)
        except ValueError:
            return False
        if path.is_file():
            path.unlink()
            # Clean up now-empty parent dirs (job dir, then tenant dir) --
            # best-effort, never raises.
            try:
                path.parent.rmdir()
                path.parent.parent.rmdir()
            except OSError:
                pass
            return True
        return False
