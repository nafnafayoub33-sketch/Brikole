"""The chat, as the two people in it read it (C9 and M12)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.enums import MessageKind, OfferStatus
from app.core.negotiation import TERMS_MAX
from app.core.offer import MAX_MESSAGE
from app.schemas.common import ApiModel


class ChatPartyOut(ApiModel):
    """The other person in the thread.

    **No phone number.** That is the whole reason this screen exists: it
    appears on the job and on nothing that comes before one.
    """

    #: The tradesman's **profile** id when the reader is the client, so C9 can
    #: link to P3; the client's **user** id the other way round. Never compare
    #: it with a message's `sender_id` — that is what `viewer_id` is for.
    id: int
    full_name: str
    avatar_url: str | None = None
    #: Only for a tradesman — a client has no rating.
    rating_avg: float | None = None
    rating_count: int | None = None
    jobs_done: int | None = None


class MessageOut(ApiModel):
    id: int
    kind: MessageKind
    #: Already redacted. For a system line this is a key and its arguments,
    #: which the web app renders in the reader's own language.
    body: str
    #: How many contacts were struck out. The bubble says so when it is not
    #: zero, so the rule is visible the first time it fires.
    redacted_count: int
    sender_id: int | None
    #: The storage path, not a URL. It lives in the private bucket, so the
    #: web app fetches it with its token like it does an identity document.
    attachment_path: str | None = None
    attachment_name: str | None = None
    attachment_bytes: int | None = None
    created_at: datetime


class ConversationOut(ApiModel):
    """The thread and the deal on the table."""

    id: int
    offer_id: int
    request_id: int
    request_title: str
    offer_status: OfferStatus

    other: ChatPartyOut
    #: True when the reader is the client. The two sides get the same payload
    #: and render different cards from it.
    viewer_is_client: bool
    #: The reader's own user id. Which bubbles are his is answered with this
    #: and nothing else: `other.id` is a profile id on one side of the thread
    #: and a user id on the other, and comparing against it is a bug waiting.
    viewer_id: int

    price_centimes: int
    terms: str
    #: What a signature is against. Sending back a stale one is refused rather
    #: than silently upgraded.
    version: int
    client_agreed: bool
    provider_agreed: bool
    #: Set the moment both signed the same version — the job exists from here.
    sealed_at: datetime | None = None
    job_id: int | None = None

    last_message_at: datetime | None = None


class ThreadOut(BaseModel):
    conversation: ConversationOut
    messages: list[MessageOut]


class UnreadOut(BaseModel):
    """How many threads have something in them he has not seen."""

    count: int


class NewMessageIn(BaseModel):
    body: str = Field(default="", max_length=MAX_MESSAGE)
    #: The `path` an upload returned. Never a URL the client made up.
    attachment_path: str | None = Field(default=None, max_length=500)
    attachment_name: str | None = Field(default=None, max_length=255)
    attachment_bytes: int | None = Field(default=None, ge=0)


class ProposeIn(BaseModel):
    price_centimes: int = Field(gt=0)
    terms: str = Field(default="", max_length=TERMS_MAX)


class AgreeIn(BaseModel):
    """The version being signed, so a price that moved is never signed blind."""

    version: int = Field(ge=1)
