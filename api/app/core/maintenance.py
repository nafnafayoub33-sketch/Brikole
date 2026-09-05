"""S4 — the platform closed for work.

A7 has had a `maintenance_mode` switch since it was built. It was validated,
stored, audited, and read by nothing: flipping it changed the row and nothing
else. This is the rule that makes it mean something.

Closed means closed to everyone but an admin — including the anonymous visitor
on the landing page, because "we are down" is a better answer than a list of
tradesmen who cannot be contacted.
"""

from __future__ import annotations

from app.core.enums import Role

#: Paths that answer even with the switch on. Each is here for one reason:
#:
#: * `/health` — a monitor must not go red because somebody flipped a switch.
#:   It is the one endpoint whose job is to answer whatever the platform is
#:   doing.
#: * `/auth/login`, `/auth/refresh` — the admin has to be able to get *in* to
#:   turn maintenance off. Closing sign-in during maintenance is how a platform
#:   locks its own keys inside. Everyone else signs in fine and then meets S4
#:   on the next call, which is a truer answer than "wrong password".
#: * `/auth/logout` — leaving is never blocked.
OPEN_PATHS = ("/health", "/auth/login", "/auth/refresh", "/auth/logout")


def is_closed(*, maintenance_on: bool, role: Role | None, path: str) -> bool:
    """Whether this request should be turned away.

    `path` is relative to the API prefix, so the rule reads the way the routes
    are written rather than repeating `/api/v1` in every comparison.
    """
    if not maintenance_on:
        return False
    if role is Role.ADMIN:
        return False
    return not path.startswith(OPEN_PATHS)
