"""Where uploaded files go.

Two buckets, and the difference between them is the point:

- **public** holds avatars and portfolio photos. They are the shop window; a
  client loads a dozen at a time.
- **private** holds identity documents. Nobody but the owner and an admin ever
  reads one, and it is never served from a public path.

One bucket was the earlier temptation and does not survive contact with what
goes in it. A bucket is public or it is not.

`LocalDiskStorage` is what development uses. Production swaps in S3 or R2 by
implementing the same protocol, and no route changes.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Protocol

from app.core.errors import DomainError, ErrorCode

#: What a browser may upload, and what each one starts with on disk. The
#: declared content type is a hint from the client, so the bytes are checked
#: instead: renaming shell.php to shell.jpg changes nothing about its first
#: four bytes.
SIGNATURES: dict[str, tuple[bytes, ...]] = {
    "jpg": (b"\xff\xd8\xff",),
    "png": (b"\x89PNG\r\n\x1a\n",),
    "webp": (b"RIFF",),
    # The chat carries documents as well as photos — a quote, a plan, a
    # warranty. Nothing executable: the list is the allowlist.
    "pdf": (b"%PDF-",),
}

MAX_BYTES = 5 * 1024 * 1024


class Bucket:
    PUBLIC = "public"
    PRIVATE = "private"


def detect_extension(data: bytes) -> str:
    """The file's real type, from its bytes, or `validation_failed`."""
    for extension, signatures in SIGNATURES.items():
        if any(data.startswith(signature) for signature in signatures):
            # WEBP starts with RIFF like a WAV does; the format is at byte 8.
            if extension == "webp" and data[8:12] != b"WEBP":
                continue
            return extension
    raise DomainError(ErrorCode.VALIDATION_FAILED, reason="unsupported_image")


class StorageProvider(Protocol):
    def save(self, data: bytes, *, bucket: str, folder: str) -> str:
        """Store the bytes and return the path they can be read back by."""
        ...

    def delete(self, path: str) -> None: ...

    def read(self, path: str) -> bytes: ...


class LocalDiskStorage:
    """Files under a directory, one folder per bucket."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    def save(self, data: bytes, *, bucket: str, folder: str) -> str:
        if not data:
            raise DomainError(ErrorCode.VALIDATION_FAILED, reason="empty_file")
        if len(data) > MAX_BYTES:
            raise DomainError(
                ErrorCode.VALIDATION_FAILED, reason="file_too_large", max_bytes=MAX_BYTES
            )

        extension = detect_extension(data)
        # A generated name, never the client's: an uploaded filename is
        # attacker-controlled and has no business deciding a path.
        name = f"{uuid.uuid4().hex}.{extension}"
        relative = f"{bucket}/{folder}/{name}"

        destination = self._absolute(relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        return relative

    def delete(self, path: str) -> None:
        self._absolute(path).unlink(missing_ok=True)

    def read(self, path: str) -> bytes:
        target = self._absolute(path)
        if not target.is_file():
            raise DomainError(ErrorCode.NOT_FOUND)
        return target.read_bytes()

    def _absolute(self, relative: str) -> Path:
        """Resolve inside the root, or refuse.

        `../` in a stored path would otherwise reach anywhere on the disk, and
        paths reach this from the database, which is not the same as trusted.
        """
        candidate = (self.root / relative).resolve()
        root = self.root.resolve()
        if not candidate.is_relative_to(root):
            raise DomainError(ErrorCode.VALIDATION_FAILED, reason="path_escape")
        return candidate
