"""C9 and M12 — the chat, and the handshake that ends it.

The shape of the flow this replaces is worth stating, because the change is not
cosmetic. It used to be: the client presses accept, the job exists, the
tradesman is charged. Now:

1. The client taps an offer. A conversation opens. Nothing is committed and
   nobody is charged.
2. They talk. Contact details are struck out of every message — see
   `core/redaction` for what that is and, more importantly, what it is not.
3. Either side puts a price and terms on the table. Every proposal clears both
   signatures, including the proposer's own.
4. Both sign the same version. *That* is the acceptance: the offer wins, the
   others are declined, the job is created at the agreed price, the tradesman
   is charged — and only then does either side see a phone number.

Step 4 is the same single transaction the accept button used to be. It moved;
it did not become two.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import (
    MessageKind,
    OfferStatus,
    ProviderStatus,
    RequestStatus,
    Role,
)
from app.core.errors import DomainError, ErrorCode
from app.core.negotiation import Terms, agree, propose, withdraw
from app.core.offer import MAX_MESSAGE
from app.core.redaction import redact
from app.models.base import utcnow
from app.models.conversation import Conversation, Message
from app.models.job import Job
from app.models.offer import Offer
from app.models.provider import ProviderProfile
from app.models.request import ServiceRequest
from app.models.user import User
from app.repositories.conversations import ConversationRepository
from app.services.jobs import JobService
from app.services.reports import ReportService


#: What a system line records. Rendered by the web app in the reader's own
#: language, so the stored body is a key and its arguments, never a sentence.
class SystemLine:
    OPENED = "conversation.opened"
    PROPOSED = "conversation.proposed"
    AGREED = "conversation.agreed"
    WITHDREW = "conversation.withdrew"
    SEALED = "conversation.sealed"


class ConversationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = ConversationRepository(db)

    # -- getting in ------------------------------------------------------

    def open_for_offer(self, user: User, offer_id: int) -> Conversation:
        """The client taps an offer and the thread opens. Idempotent.

        Opening commits him to nothing: no offer changes status, no request is
        assigned, no money moves. That is the point of the screen — the old
        flow made him commit before he could ask a single question.
        """
        offer = self.db.get(Offer, offer_id)
        if offer is None:
            raise DomainError(ErrorCode.NOT_FOUND)

        request = self.db.get(ServiceRequest, offer.request_id)
        if request is None or request.client_id != user.id:
            # Somebody else's, or he is the tradesman and came the wrong way.
            raise DomainError(ErrorCode.NOT_FOUND)

        existing = self.repo.for_offer(offer.id)
        if existing is not None:
            return existing

        if offer.status is not OfferStatus.PENDING:
            raise DomainError(
                ErrorCode.CONFLICT, reason="offer_not_pending", status=offer.status.value
            )

        conversation = Conversation(
            offer_id=offer.id,
            request_id=request.id,
            client_id=user.id,
            provider_id=offer.provider_id,
            # The offer's price is the opening position, not the deal.
            price_centimes=offer.price_centimes,
            terms="",
            version=1,
        )
        self.db.add(conversation)
        self.db.flush()

        self._system(conversation, SystemLine.OPENED)
        # Opening it is reading it. Without this the client's own first line
        # comes back to her as one unread thread.
        self._mark_own_read(user, conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def get_own(self, user: User, conversation_id: int) -> Conversation:
        """His conversation, from whichever side he is on.

        Somebody else's is *not found* rather than forbidden: the id space is
        guessable and a 403 confirms one exists.
        """
        conversation = self.repo.get(conversation_id)
        if conversation is None or not self._is_party(user, conversation):
            raise DomainError(ErrorCode.NOT_FOUND)
        return conversation

    def messages(
        self, user: User, conversation_id: int, *, after_id: int | None = None
    ) -> tuple[Conversation, list[Message]]:
        conversation = self.get_own(user, conversation_id)
        return conversation, self.repo.messages(conversation.id, after_id=after_id)

    def mark_read(self, user: User, conversation_id: int) -> Conversation:
        conversation = self.get_own(user, conversation_id)
        self._mark_own_read(user, conversation)
        self.db.commit()
        return conversation

    # -- talking ---------------------------------------------------------

    def send(
        self,
        user: User,
        conversation_id: int,
        *,
        body: str,
        attachment_path: str | None = None,
        attachment_name: str | None = None,
        attachment_bytes: int | None = None,
        kind: MessageKind = MessageKind.TEXT,
    ) -> Message:
        """Send one message. A contact detail in it is struck out, quietly.

        Nothing is refused and nothing is charged. He types his number, the
        message goes, and the number is not in it — the bubble says a contact
        was removed so he is not left waiting for a call that was never going
        to come. Refusing the message outright would only teach him to write
        `zero six`, and pricing it would put a paywall in the middle of a
        conversation two people are having in good faith.

        What the platform does instead is *count*. A tradesman who tries this
        with one client is answering a question; one who tries it with twenty
        is running his business off the back of the platform, and that is what
        `ContactWatch` is for.
        """
        conversation = self.get_own(user, conversation_id)

        text = body.strip()
        if len(text) > MAX_MESSAGE:
            raise DomainError(
                ErrorCode.VALIDATION_FAILED, field="body", max_length=MAX_MESSAGE
            )
        if not text and attachment_path is None:
            raise DomainError(ErrorCode.VALIDATION_FAILED, field="body")

        # Once the job exists the platform has been paid, so there is nothing
        # left to protect: they have each other's number on C4 already, and
        # striking one out of a message here would be pure superstition.
        removed = 0
        if conversation.sealed_at is None:
            cleaned = redact(text)
            text, removed = cleaned.text, cleaned.count

        message = Message(
            conversation_id=conversation.id,
            sender_id=user.id,
            kind=kind,
            body=text,
            redacted_count=removed,
            attachment_path=attachment_path,
            attachment_name=attachment_name,
            attachment_bytes=attachment_bytes,
        )
        self.db.add(message)
        conversation.last_message_at = utcnow()
        self._mark_own_read(user, conversation)

        if removed and conversation.client_id != user.id:
            # Flushed first: the count is taken over messages, and this one is
            # part of it. Filed inside the same transaction as the message it
            # was counted from — a flag standing on a message that rolled back
            # is an accusation with nothing behind it.
            self.db.flush()
            ReportService(self.db).flag_contact_sharing(conversation.provider_id)

        self.db.commit()
        self.db.refresh(message)
        return message

    # -- the handshake ---------------------------------------------------

    def propose(
        self, user: User, conversation_id: int, *, price_centimes: int, terms: str
    ) -> Conversation:
        conversation = self._open_conversation(user, conversation_id)

        moved = propose(
            self._terms(conversation), price_centimes=price_centimes, terms=terms
        )
        self._apply(conversation, moved)

        self._system(
            conversation,
            SystemLine.PROPOSED,
            by=user.id,
            price_centimes=moved.price_centimes,
        )
        self._mark_own_read(user, conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def agree(self, user: User, conversation_id: int, *, version: int) -> Conversation:
        """Sign, and close the deal if that was the second signature."""
        conversation = self._open_conversation(user, conversation_id)
        as_client = conversation.client_id == user.id

        signed = agree(self._terms(conversation), as_client=as_client, version=version)
        self._apply(conversation, signed)
        self._system(conversation, SystemLine.AGREED, by=user.id)
        self._mark_own_read(user, conversation)

        if signed.sealed:
            self._seal(conversation)

        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def withdraw(self, user: User, conversation_id: int) -> Conversation:
        conversation = self._open_conversation(user, conversation_id)
        as_client = conversation.client_id == user.id

        self._apply(conversation, withdraw(self._terms(conversation), as_client=as_client))
        self._system(conversation, SystemLine.WITHDREW, by=user.id)
        self._mark_own_read(user, conversation)

        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    # -- helpers ---------------------------------------------------------

    def _seal(self, conversation: Conversation) -> None:
        """Both signatures on one version. This is the acceptance.

        It runs the same single transaction the accept button used to be —
        offer accepted, the others declined, request assigned, job created, fee
        charged — at the price the two of them actually agreed rather than the
        one the tradesman guessed before he had seen the job.
        """
        client = self.db.get(User, conversation.client_id)
        if client is None:  # pragma: no cover — the FK forbids it
            raise DomainError(ErrorCode.NOT_FOUND)

        job = JobService(self.db).accept_offer(
            client,
            conversation.request_id,
            conversation.offer_id,
            price_centimes=conversation.price_centimes,
            commit=False,
        )

        conversation.sealed_at = utcnow()
        self._system(conversation, SystemLine.SEALED, job_id=job.id)

    def _open_conversation(self, user: User, conversation_id: int) -> Conversation:
        conversation = self.get_own(user, conversation_id)
        if conversation.sealed_at is not None:
            raise DomainError(ErrorCode.CONFLICT, reason="already_sealed")

        offer = self.db.get(Offer, conversation.offer_id)
        if offer is None or offer.status is not OfferStatus.PENDING:
            raise DomainError(ErrorCode.CONFLICT, reason="offer_not_pending")

        request = self.db.get(ServiceRequest, conversation.request_id)
        if request is None or request.status is not RequestStatus.OPEN:
            raise DomainError(ErrorCode.CONFLICT, reason="request_not_open")

        provider = self.db.get(ProviderProfile, conversation.provider_id)
        if provider is None or provider.status is not ProviderStatus.APPROVED:
            raise DomainError(ErrorCode.CONFLICT, reason="provider_unavailable")

        return conversation

    @staticmethod
    def _terms(conversation: Conversation) -> Terms:
        return Terms(
            price_centimes=conversation.price_centimes,
            terms=conversation.terms,
            version=conversation.version,
            client_agreed_version=conversation.client_agreed_version,
            provider_agreed_version=conversation.provider_agreed_version,
        )

    @staticmethod
    def _apply(conversation: Conversation, terms: Terms) -> None:
        conversation.price_centimes = terms.price_centimes
        conversation.terms = terms.terms
        conversation.version = terms.version
        conversation.client_agreed_version = terms.client_agreed_version
        conversation.provider_agreed_version = terms.provider_agreed_version

    def _system(self, conversation: Conversation, line: str, **details: int) -> Message:
        """A line the platform wrote, stored as a key and its arguments.

        Never a sentence: the two people reading this thread may be reading it
        in different languages, and a sentence frozen at write time would be in
        whichever one the actor happened to be using.
        """
        body = line
        if details:
            body = f"{line}?" + "&".join(f"{key}={value}" for key, value in details.items())

        message = Message(
            conversation_id=conversation.id,
            sender_id=None,
            kind=MessageKind.SYSTEM,
            body=body,
        )
        self.db.add(message)
        conversation.last_message_at = utcnow()
        self.db.flush()
        return message

    def _mark_own_read(self, user: User, conversation: Conversation) -> None:
        """Acting is reading: opening the thread, writing in it, moving the
        price or signing all mean he has plainly just looked at it. Without
        this every action a person takes comes back to him as unread."""
        self.db.flush()
        newest = self.repo.newest_message_id(conversation.id)
        if conversation.client_id == user.id:
            conversation.client_read_message_id = newest
        else:
            conversation.provider_read_message_id = newest

    def _is_party(self, user: User, conversation: Conversation) -> bool:
        if user.role is Role.CLIENT:
            return conversation.client_id == user.id
        if user.role is Role.PROVIDER:
            profile = user.provider_profile
            return profile is not None and profile.id == conversation.provider_id
        # Staff do not read private conversations. A moderator arbitrating a
        # dispute reads the job and what was filed about it, not the chat.
        return False

    def unread(self, user: User) -> int:
        """Threads where the other side has written since he last looked.

        The tradesman has no other way to learn that a client opened a chat on
        his offer: he sent it and went back to work. Without this he has to
        remember to check M6, which is the same as not being told.
        """
        if user.role is Role.CLIENT:
            return self.repo.unread_for_client(user.id)
        profile = user.provider_profile
        return self.repo.unread_for_provider(profile.id) if profile else 0

    # -- the job it became -----------------------------------------------

    def job_for(self, conversation: Conversation) -> Job | None:
        return self.db.execute(
            select(Job).where(Job.offer_id == conversation.offer_id)
        ).scalar_one_or_none()
