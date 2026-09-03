"""The chat that stands between an offer and a job.

One conversation per offer. It opens when the client taps the offer — which
commits him to nothing — and it closes when both sides have signed the same
terms, which is the moment the job exists and the tradesman is charged.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import MessageKind
from app.models.base import Base, PkMixin, TimestampMixin, enum_column

if TYPE_CHECKING:
    from app.models.offer import Offer
    from app.models.user import User


class Conversation(PkMixin, TimestampMixin, Base):
    __tablename__ = "conversations"
    __table_args__ = (
        # One thread per offer. A second one would split the history of a
        # single negotiation across two rows nobody would think to join.
        UniqueConstraint("offer_id", name="uq_conversations_offer_id"),
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"},
    )

    offer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("offers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    request_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    client_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("provider_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # -- the deal on the table -------------------------------------------
    #
    # Seeded from the offer, then moved by either side. `version` is what makes
    # a signature specific: agreeing to version 4 says nothing about version 5,
    # so a price changed after somebody signed is a price nobody has signed.

    price_centimes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    terms: Mapped[str] = mapped_column(Text, nullable=False, default="")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    client_agreed_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider_agreed_version: Mapped[int | None] = mapped_column(Integer, nullable=True)

    #: Set the moment both signatures land on the same version. The job it
    #: produced hangs off the offer, not off here.
    sealed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    #: Cheap ordering for a future inbox, and what "unread" is measured against.
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    client_read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    provider_read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    offer: Mapped[Offer] = relationship()
    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.id",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Conversation {self.id} offer={self.offer_id} v{self.version}>"


class Message(PkMixin, TimestampMixin, Base):
    __tablename__ = "conversation_messages"

    conversation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    #: Null on a system line — the platform said it, not a person.
    sender_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    kind: Mapped[MessageKind] = mapped_column(
        enum_column(MessageKind), nullable=False, default=MessageKind.TEXT
    )

    #: Stored **after** redaction. The struck-out number is never written down:
    #: keeping it would hand it to anyone who reads the table and make the rule
    #: theatre.
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    #: How many contacts were struck out of this message. Zero for almost every
    #: message; a moderator reads a run of them as somebody trying repeatedly.
    redacted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    #: A photo or a document, in the private bucket. Read through the route
    #: that checks membership of this conversation, never from a public path.
    attachment_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    attachment_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attachment_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
    sender: Mapped[User | None] = relationship()

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Message {self.id} conv={self.conversation_id} {self.kind}>"
