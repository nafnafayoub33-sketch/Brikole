"""Every query about conversations. Nothing else writes SQL against them."""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.conversation import Conversation, Message
from app.models.offer import Offer


class ConversationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, conversation_id: int) -> Conversation | None:
        return self.db.execute(
            select(Conversation)
            .options(selectinload(Conversation.offer).selectinload(Offer.provider))
            .where(Conversation.id == conversation_id)
        ).scalar_one_or_none()

    def for_offer(self, offer_id: int) -> Conversation | None:
        return self.db.execute(
            select(Conversation).where(Conversation.offer_id == offer_id)
        ).scalar_one_or_none()

    def messages(
        self, conversation_id: int, *, after_id: int | None = None, limit: int = 200
    ) -> list[Message]:
        """Oldest first — a conversation is read forwards.

        `after_id` is the cheap poll: the screen asks for what it has not seen
        rather than re-reading the thread every few seconds.
        """
        stmt = (
            select(Message)
            .options(selectinload(Message.sender))
            .where(Message.conversation_id == conversation_id)
        )
        if after_id is not None:
            stmt = stmt.where(Message.id > after_id)

        return list(
            self.db.execute(stmt.order_by(Message.id).limit(limit)).scalars().all()
        )

    def unread_for_client(self, client_id: int) -> int:
        """Messages the other side sent since he last looked."""
        return self._unread(
            Conversation.client_id == client_id, Conversation.client_read_at
        )

    def unread_for_provider(self, provider_id: int) -> int:
        return self._unread(
            Conversation.provider_id == provider_id, Conversation.provider_read_at
        )

    def _unread(self, mine, read_at) -> int:  # type: ignore[no-untyped-def]
        return int(
            self.db.execute(
                select(func.count())
                .select_from(Conversation)
                .where(
                    mine,
                    Conversation.last_message_at.is_not(None),
                    or_(read_at.is_(None), read_at < Conversation.last_message_at),
                )
            ).scalar_one()
        )
