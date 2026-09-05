"""M10 — the tradesman's one answer to a review.

`docs/SCREENS.md` says "he may reply **once** to each", and the once is the
whole rule. A reply that can be rewritten after the client has read it is not a
reply, it is a moving target: the client sees an apology, comes back a week
later and finds an accusation, and the review thread stops being evidence of
anything. So the first one stands.

That cuts both ways, which is why the screen warns before it sends rather than
after. Nobody should discover the rule by hitting it.
"""

from __future__ import annotations

from app.core.errors import DomainError, ErrorCode

MIN_REPLY = 2

#: Long enough to explain what happened, short enough that nobody argues a case
#: underneath a one-line review. The column is TEXT, so this is a judgement
#: about reading, not a storage limit.
MAX_REPLY = 600


def validate_reply(value: str, *, already_replied: bool) -> str:
    """Clean the text, or say why it is refused."""
    if already_replied:
        # 409, not 422: the text is fine and he is allowed to be here — the
        # world says no, because he already used his answer.
        raise DomainError(ErrorCode.CONFLICT, reason="already_replied")

    cleaned = " ".join(value.split())
    if not (MIN_REPLY <= len(cleaned) <= MAX_REPLY):
        raise DomainError(
            ErrorCode.VALIDATION_FAILED, field="reply", max_length=MAX_REPLY
        )
    return cleaned
