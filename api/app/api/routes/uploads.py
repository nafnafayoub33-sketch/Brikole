"""Uploading a photo, and reading one back.

Public files are the shop window. Private ones are identity documents, and the
only people who ever read one are its owner and an admin — which is a rule the
route enforces, not a convention the folder name implies.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, File, Form, Response, UploadFile

from app.core.enums import Role
from app.core.errors import DomainError, ErrorCode
from app.deps import CurrentUser, StorageDep
from app.schemas.common import ApiModel
from app.services.storage import MAX_BYTES, Bucket

router = APIRouter(tags=["uploads"])

CONTENT_TYPES = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}


class UploadPurpose(StrEnum):
    AVATAR = "avatar"
    ID_CARD = "id_card"
    PORTFOLIO = "portfolio"
    REQUEST_PHOTO = "request_photo"


#: Who may upload what. Stated as a table rather than as a chain of `if`s,
#: because the next purpose added is the one somebody forgets to guard.
ALLOWED_ROLES: dict[UploadPurpose, frozenset[Role] | None] = {
    UploadPurpose.AVATAR: None,  # anybody with an account
    UploadPurpose.ID_CARD: frozenset({Role.PROVIDER}),
    UploadPurpose.PORTFOLIO: frozenset({Role.PROVIDER}),
    UploadPurpose.REQUEST_PHOTO: frozenset({Role.CLIENT}),
}


class UploadOut(ApiModel):
    #: What to send back when saving the form. Not a URL: a private file has no
    #: public one.
    path: str
    #: Where to display it, when it is displayable at all.
    url: str | None


@router.post("/uploads", response_model=UploadOut, status_code=201)
async def upload(
    user: CurrentUser,
    storage: StorageDep,
    purpose: Annotated[UploadPurpose, Form()],
    file: Annotated[UploadFile, File()],
) -> UploadOut:
    allowed = ALLOWED_ROLES[purpose]
    if allowed is not None and user.role not in allowed:
        raise DomainError(ErrorCode.FORBIDDEN, purpose=purpose.value)

    # Read one byte past the limit rather than the whole thing: a 2 GB upload
    # should cost 5 MB of memory and a refusal.
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, reason="file_too_large", max_bytes=MAX_BYTES
        )

    bucket = Bucket.PRIVATE if purpose is UploadPurpose.ID_CARD else Bucket.PUBLIC
    folder = {
        UploadPurpose.AVATAR: "avatars",
        UploadPurpose.ID_CARD: "id-cards",
        UploadPurpose.PORTFOLIO: "portfolio",
        UploadPurpose.REQUEST_PHOTO: "requests",
    }[purpose]

    path = storage.save(data, bucket=bucket, folder=f"{folder}/{user.id}")
    url = None if bucket == Bucket.PRIVATE else f"/api/v1/uploads/{path}"
    return UploadOut(path=path, url=url)


@router.get("/uploads/public/{rest:path}")
def read_public(rest: str, storage: StorageDep) -> Response:
    return _serve(storage.read(f"{Bucket.PUBLIC}/{rest}"), rest, cacheable=True)


@router.get("/uploads/private/{rest:path}")
def read_private(rest: str, user: CurrentUser, storage: StorageDep) -> Response:
    """An identity document. Its owner, or an admin. Nobody else, ever."""
    owned = rest.startswith(f"id-cards/{user.id}/")
    if not owned and user.role is not Role.ADMIN:
        # Not "forbidden": whether a document exists is itself private.
        raise DomainError(ErrorCode.NOT_FOUND)

    return _serve(storage.read(f"{Bucket.PRIVATE}/{rest}"), rest, cacheable=False)


def _serve(data: bytes, path: str, *, cacheable: bool) -> Response:
    extension = path.rsplit(".", 1)[-1].lower()
    headers = {"Cache-Control": "public, max-age=31536000, immutable"} if cacheable else {
        "Cache-Control": "private, no-store"
    }
    return Response(
        content=data,
        media_type=CONTENT_TYPES.get(extension, "application/octet-stream"),
        headers=headers,
    )
