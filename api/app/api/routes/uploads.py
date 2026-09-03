"""Uploading a photo, and reading one back.

Public files are the shop window. Private ones are identity documents, and the
only people who ever read one are its owner and an admin — which is a rule the
route enforces, not a convention the folder name implies.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, File, Form, Response, UploadFile
from sqlalchemy import select

from app.core.enums import Role
from app.core.errors import DomainError, ErrorCode
from app.deps import CurrentUser, DbSession, StorageDep
from app.models.conversation import Conversation, Message
from app.schemas.common import ApiModel
from app.services.storage import MAX_BYTES, Bucket

router = APIRouter(tags=["uploads"])

CONTENT_TYPES = {
    "jpg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
    "pdf": "application/pdf",
}


class UploadPurpose(StrEnum):
    AVATAR = "avatar"
    ID_CARD = "id_card"
    PORTFOLIO = "portfolio"
    REQUEST_PHOTO = "request_photo"
    RECEIPT = "receipt"
    CHAT_FILE = "chat_file"


#: Who may upload what. Stated as a table rather than as a chain of `if`s,
#: because the next purpose added is the one somebody forgets to guard.
ALLOWED_ROLES: dict[UploadPurpose, frozenset[Role] | None] = {
    UploadPurpose.AVATAR: None,  # anybody with an account
    UploadPurpose.ID_CARD: frozenset({Role.PROVIDER}),
    UploadPurpose.PORTFOLIO: frozenset({Role.PROVIDER}),
    UploadPurpose.REQUEST_PHOTO: frozenset({Role.CLIENT}),
    UploadPurpose.RECEIPT: frozenset({Role.PROVIDER}),
    # Both sides of a chat send photos and documents.
    UploadPurpose.CHAT_FILE: frozenset({Role.CLIENT, Role.PROVIDER}),
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

    # A bank receipt carries an account number, exactly like an ID card does.
    private = {UploadPurpose.ID_CARD, UploadPurpose.RECEIPT, UploadPurpose.CHAT_FILE}
    bucket = Bucket.PRIVATE if purpose in private else Bucket.PUBLIC
    folder = {
        UploadPurpose.AVATAR: "avatars",
        UploadPurpose.ID_CARD: "id-cards",
        UploadPurpose.PORTFOLIO: "portfolio",
        UploadPurpose.REQUEST_PHOTO: "requests",
        UploadPurpose.RECEIPT: "receipts",
        UploadPurpose.CHAT_FILE: "chat",
    }[purpose]

    path = storage.save(data, bucket=bucket, folder=f"{folder}/{user.id}")
    url = None if bucket == Bucket.PRIVATE else f"/api/v1/uploads/{path}"
    return UploadOut(path=path, url=url)


@router.get("/uploads/public/{rest:path}")
def read_public(rest: str, storage: StorageDep) -> Response:
    return _serve(storage.read(f"{Bucket.PUBLIC}/{rest}"), rest, cacheable=True)


@router.get("/uploads/private/{rest:path}")
def read_private(
    rest: str, user: CurrentUser, storage: StorageDep, db: DbSession
) -> Response:
    """A private file. Who may read one depends on what it is.

    Not "forbidden" when they may not: whether a file exists is itself private,
    so the answer is the same 404 a wrong path gets.
    """
    if rest.startswith("chat/"):
        # A photo or a document somebody put in a chat. Its uploader, and the
        # one other person in that conversation. Membership is asked of the
        # database rather than inferred from the path: the folder is named
        # after whoever uploaded it, which says nothing about who may read it.
        if not _in_conversation(db, user, f"{Bucket.PRIVATE}/{rest}"):
            raise DomainError(ErrorCode.NOT_FOUND)
        return _serve(storage.read(f"{Bucket.PRIVATE}/{rest}"), rest, cacheable=False)

    # An identity document or a bank receipt. Its owner, or an admin.
    owned = rest.startswith(f"id-cards/{user.id}/")
    if not owned and user.role is not Role.ADMIN:
        raise DomainError(ErrorCode.NOT_FOUND)

    return _serve(storage.read(f"{Bucket.PRIVATE}/{rest}"), rest, cacheable=False)


def _in_conversation(db: DbSession, user: CurrentUser, path: str) -> bool:
    message = db.execute(
        select(Message).where(Message.attachment_path == path)
    ).scalar_one_or_none()
    if message is None:
        return False

    conversation = db.get(Conversation, message.conversation_id)
    if conversation is None:  # pragma: no cover — the FK forbids it
        return False

    if conversation.client_id == user.id:
        return True
    profile = user.provider_profile
    return profile is not None and profile.id == conversation.provider_id


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
