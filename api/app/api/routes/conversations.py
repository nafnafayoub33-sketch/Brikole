"""C9 and M12 — the chat between a client and a tradesman.

One router for both sides. The two screens differ in what they render, not in
what they may do: either can talk, either can move the price, and it takes both
signatures to make a job. A route per role would have been two copies of the
same permission check, and the day they drift is the day one side can do
something the other cannot.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.enums import MessageKind, Role
from app.core.errors import DomainError, ErrorCode
from app.deps import CurrentUser, DbSession, require_roles
from app.models.conversation import Conversation, Message
from app.models.offer import Offer
from app.models.provider import ProviderProfile
from app.models.request import ServiceRequest
from app.models.user import User
from app.schemas.conversation import (
    AgreeIn,
    ChatPartyOut,
    ConversationOut,
    MessageOut,
    NewMessageIn,
    ProposeIn,
    ThreadOut,
    UnreadOut,
)
from app.services import lead_fee
from app.services.conversations import ConversationService

router = APIRouter(tags=["chat"])

#: Staff never appear here. A moderator arbitrating a dispute reads the job and
#: what was filed about it, not two people's private negotiation.
_PARTIES = Depends(require_roles(Role.CLIENT, Role.PROVIDER))


@router.post("/offers/{offer_id}/conversation", response_model=ConversationOut)
def open_conversation(offer_id: int, user: CurrentUser, db: DbSession) -> ConversationOut:
    """C3 → C9. Tapping an offer opens the thread and commits to nothing."""
    if user.role is not Role.CLIENT:
        raise DomainError(ErrorCode.FORBIDDEN)

    service = ConversationService(db)
    return _conversation(service.open_for_offer(user, offer_id), user, db)


@router.get("/conversations/unread", response_model=UnreadOut, dependencies=[_PARTIES])
def unread(user: CurrentUser, db: DbSession) -> UnreadOut:
    """The badge on the nav. Declared before `/conversations/{id}` so the
    literal path wins over the parameter — the other order makes this a
    request for a conversation called "unread"."""
    return UnreadOut(count=ConversationService(db).unread(user))


@router.get(
    "/conversations/{conversation_id}",
    response_model=ThreadOut,
    dependencies=[_PARTIES],
)
def read_thread(
    conversation_id: int,
    user: CurrentUser,
    db: DbSession,
    after_id: Annotated[int | None, Query(ge=0)] = None,
) -> ThreadOut:
    service = ConversationService(db)
    conversation, messages = service.messages(user, conversation_id, after_id=after_id)
    return ThreadOut(
        conversation=_conversation(conversation, user, db),
        messages=[_message(row) for row in messages],
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageOut,
    status_code=201,
    dependencies=[_PARTIES],
)
def send_message(
    conversation_id: int, payload: NewMessageIn, user: CurrentUser, db: DbSession
) -> MessageOut:
    kind = MessageKind.TEXT
    if payload.attachment_path:
        kind = (
            MessageKind.IMAGE
            if payload.attachment_path.rsplit(".", 1)[-1].lower()
            in {"jpg", "jpeg", "png", "webp"}
            else MessageKind.FILE
        )

    message = ConversationService(db).send(
        user,
        conversation_id,
        body=payload.body,
        accept_charge=payload.accept_charge,
        attachment_path=payload.attachment_path,
        attachment_name=payload.attachment_name,
        attachment_bytes=payload.attachment_bytes,
        kind=kind,
    )
    return _message(message)


@router.post(
    "/conversations/{conversation_id}/read",
    response_model=ConversationOut,
    dependencies=[_PARTIES],
)
def mark_read(conversation_id: int, user: CurrentUser, db: DbSession) -> ConversationOut:
    service = ConversationService(db)
    return _conversation(service.mark_read(user, conversation_id), user, db)


@router.post(
    "/conversations/{conversation_id}/propose",
    response_model=ConversationOut,
    dependencies=[_PARTIES],
)
def propose(
    conversation_id: int, payload: ProposeIn, user: CurrentUser, db: DbSession
) -> ConversationOut:
    """Put a price and terms on the table. Clears both signatures."""
    service = ConversationService(db)
    conversation = service.propose(
        user, conversation_id, price_centimes=payload.price_centimes, terms=payload.terms
    )
    return _conversation(conversation, user, db)


@router.post(
    "/conversations/{conversation_id}/agree",
    response_model=ConversationOut,
    dependencies=[_PARTIES],
)
def agree(
    conversation_id: int, payload: AgreeIn, user: CurrentUser, db: DbSession
) -> ConversationOut:
    """Sign. The second signature creates the job and charges the lead fee."""
    service = ConversationService(db)
    conversation = service.agree(user, conversation_id, version=payload.version)
    return _conversation(conversation, user, db)


@router.post(
    "/conversations/{conversation_id}/withdraw",
    response_model=ConversationOut,
    dependencies=[_PARTIES],
)
def withdraw(conversation_id: int, user: CurrentUser, db: DbSession) -> ConversationOut:
    service = ConversationService(db)
    return _conversation(service.withdraw(user, conversation_id), user, db)


# -- rendering --------------------------------------------------------------


def _conversation(
    conversation: Conversation, user: User, db: DbSession
) -> ConversationOut:
    viewer_is_client = conversation.client_id == user.id
    request = db.get(ServiceRequest, conversation.request_id)
    offer = db.get(Offer, conversation.offer_id)
    if request is None or offer is None:  # pragma: no cover — the FKs forbid it
        raise DomainError(ErrorCode.NOT_FOUND)
    job = ConversationService(db).job_for(conversation)

    return ConversationOut(
        id=conversation.id,
        offer_id=conversation.offer_id,
        request_id=conversation.request_id,
        request_title=request.title,
        offer_status=offer.status,
        other=_other(conversation, viewer_is_client=viewer_is_client, db=db),
        viewer_is_client=viewer_is_client,
        viewer_id=user.id,
        price_centimes=conversation.price_centimes,
        terms=conversation.terms,
        version=conversation.version,
        client_agreed=conversation.client_agreed_version == conversation.version,
        provider_agreed=conversation.provider_agreed_version == conversation.version,
        sealed_at=conversation.sealed_at,
        job_id=job.id if job else None,
        lead_charged_at=conversation.lead_charged_at,
        contact_fee_centimes=lead_fee.fee_for(db, request),
        last_message_at=conversation.last_message_at,
    )


def _other(
    conversation: Conversation, *, viewer_is_client: bool, db: DbSession
) -> ChatPartyOut:
    """The person on the other side, with no way to reach them off-platform."""
    if viewer_is_client:
        profile = db.get(ProviderProfile, conversation.provider_id)
        if profile is None:  # pragma: no cover — the FK forbids it
            raise DomainError(ErrorCode.NOT_FOUND)
        return ChatPartyOut(
            id=profile.id,
            full_name=profile.user.full_name,
            avatar_url=profile.user.avatar_url,
            rating_avg=profile.rating_avg,
            rating_count=profile.rating_count,
            jobs_done=profile.jobs_done,
        )

    client = db.get(User, conversation.client_id)
    if client is None:  # pragma: no cover — the FK forbids it
        raise DomainError(ErrorCode.NOT_FOUND)
    return ChatPartyOut(
        id=client.id, full_name=client.full_name, avatar_url=client.avatar_url
    )


def _message(message: Message) -> MessageOut:
    return MessageOut(
        id=message.id,
        kind=message.kind,
        body=message.body,
        redacted_count=message.redacted_count,
        sender_id=message.sender_id,
        attachment_path=message.attachment_path,
        attachment_name=message.attachment_name,
        attachment_bytes=message.attachment_bytes,
        created_at=message.created_at,
    )
