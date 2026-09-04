"""Every query about conversations. Nothing else writes SQL against them."""

from __future__ import annotations

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.orm.attributes import InstrumentedAttribute

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
        """Threads with a message the other side wrote that he has not seen."""
        return self._unread(
            Conversation.client_id == client_id,
            Conversation.client_read_message_id,
            Message.sender_id != Conversation.client_id,
        )

    def unread_for_provider(self, provider_id: int) -> int:
        return self._unread(
            Conversation.provider_id == provider_id,
            Conversation.provider_read_message_id,
            Message.sender_id == Conversation.client_id,
        )

    def _unread(
        self,
        mine: ColumnElement[bool],
        marker: InstrumentedAttribute[int | None],
        from_the_other_side: ColumnElement[bool],
    ) -> int:
        """Counted on message ids, never on timestamps.

        Two things make a thread unread, and the first is the one that matters
        most: **he has never opened it at all.** A client tapping an offer is
        the event the tradesman most needs to hear about, and it writes only a
        system line — no sender, so a rule that counted messages from the other
        side would stay silent on exactly the case the badge exists for.

        After that it is what it sounds like: a message the other person wrote
        that he has not seen. System lines are not counted there — "the price
        moved" already shows on the deal card, and a badge for your own action
        is noise.
        """
        never_opened = marker.is_(None)
        theirs = (
            select(Message.id)
            .where(
                Message.conversation_id == Conversation.id,
                Message.sender_id.is_not(None),
                from_the_other_side,
                Message.id > marker,
            )
            .exists()
        )

        return int(
            self.db.execute(
                select(func.count())
                .select_from(Conversation)
                .where(mine, or_(never_opened, theirs))
            ).scalar_one()
        )

    def newest_message_id(self, conversation_id: int) -> int | None:
        return self.db.execute(
            select(func.max(Message.id)).where(Message.conversation_id == conversation_id)
        ).scalar_one()
