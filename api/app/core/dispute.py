"""Disputes: who may open one, when, and what a verdict is allowed to do.

Framework-free. The rule that shapes the whole module: **the platform never
held the client's money**, so a dispute cannot order a refund of the job price.
The only money it can move is the *lead fee* the platform itself took from the
tradesman, and only back to him.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.core.enums import DisputeReason, DisputeVerdict, JobStatus

MIN_DESCRIPTION = 20
MAX_DESCRIPTION = 2000
MAX_EVIDENCE = 6
MAX_MESSAGE = 2000

#: A dispute nobody has picked up in this long is flagged on D1. Not a
#: deadline — a queue where everything looks equally urgent has no queue.
STALE_HOURS = 48

#: Jobs a dispute can be opened against. Anything earlier has nothing to argue
#: about yet, and a cancelled job was already settled by whoever cancelled it.
DISPUTABLE = frozenset({JobStatus.IN_PROGRESS, JobStatus.DONE, JobStatus.CONFIRMED})


@dataclass(frozen=True, slots=True)
class NewDispute:
    reason: DisputeReason
    description: str
    evidence_paths: tuple[str, ...]


def validate_dispute(
    *, reason: DisputeReason, description: str, evidence_paths: list[str] | None = None
) -> NewDispute:
    cleaned = " ".join((description or "").split())
    if len(cleaned) < MIN_DESCRIPTION or len(cleaned) > MAX_DESCRIPTION:
        raise ValueError("description")

    seen: list[str] = []
    for path in evidence_paths or []:
        if path and path not in seen:
            seen.append(path)
    if len(seen) > MAX_EVIDENCE:
        raise ValueError("evidence_paths")

    return NewDispute(reason=reason, description=cleaned, evidence_paths=tuple(seen))


def within_window(finished_at: datetime | None, now: datetime, *, days: int) -> bool:
    """Whether the job is still young enough to argue about.

    Counted from when the work finished, not from when it was confirmed: a
    client who never confirms would otherwise hold the window open forever.
    """
    if finished_at is None:
        # Still in progress — nothing has "ended" to start a clock.
        return True
    return now - finished_at <= timedelta(days=days)


def refund_allowed(verdict: DisputeVerdict) -> bool:
    """Whether this verdict may hand the lead fee back to the tradesman.

    Only when the *client* was at fault. The fee bought a real introduction to
    a real job; it is refunded when the person who wasted it was on the other
    side, and not as a way of splitting the difference.
    """
    return verdict is DisputeVerdict.CLIENT_AT_FAULT


def at_fault_party(verdict: DisputeVerdict) -> str | None:
    """Which side a warning or suspension may land on. `None` means neither."""
    return {
        DisputeVerdict.CLIENT_AT_FAULT: "client",
        DisputeVerdict.PROVIDER_AT_FAULT: "provider",
        DisputeVerdict.NO_FAULT: None,
    }[verdict]


def is_stale(opened_at: datetime, now: datetime) -> bool:
    return now - opened_at > timedelta(hours=STALE_HOURS)
