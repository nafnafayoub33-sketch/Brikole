"""FastAPI dependencies: the session, the current user, and the role gates.

This is the security boundary. A router that forgets to declare a gate gets no
gate — so every non-public route below declares one explicitly, and there is no
"default allow" anywhere in the file.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.config import API_PREFIX, Settings, get_settings
from app.core import security
from app.core.enums import Role
from app.core.errors import DomainError, ErrorCode
from app.core.permissions import require_permission as _require_permission
from app.db import get_db
from app.models.user import User
from app.services.auth import AuthService

REFRESH_COOKIE = "brikole_refresh"
#: Scoped to the auth routes so it is not attached to every API call — and
#: scoped to where they actually live, which is behind the API prefix.
REFRESH_COOKIE_PATH = f"{API_PREFIX}/auth"

DbSession = Annotated[Session, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_auth_service(db: DbSession, settings: SettingsDep) -> AuthService:
    return AuthService(db, settings)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def _bearer_token(request: Request) -> str:
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise DomainError(ErrorCode.NOT_AUTHENTICATED)
    return token.strip()


def get_current_user(request: Request, auth: AuthServiceDep) -> User:
    return auth.user_from_token(_bearer_token(request), expected_type=security.ACCESS_TOKEN)


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: Role) -> Callable[[User], User]:
    """Gate a route to specific roles.

        @router.get("/approvals", dependencies=[Depends(require_roles(Role.ADMIN))])
    """

    def dependency(user: CurrentUser) -> User:
        if user.role not in roles:
            raise DomainError(
                ErrorCode.FORBIDDEN,
                role=user.role.value,
                allowed=[r.value for r in roles],
            )
        return user

    return dependency


def require_permission(permission: str) -> Callable[[User], User]:
    """Gate a route on a capability rather than a role.

    Preferred wherever two roles share an ability — a moderator and an admin
    both resolve disputes — so the route says what it needs, not who is allowed.
    """

    def dependency(user: CurrentUser) -> User:
        _require_permission(user.role, permission)
        return user

    return dependency


#: Common gates, named once.
RequireAdmin = Annotated[User, Depends(require_roles(Role.ADMIN))]
RequireStaff = Annotated[User, Depends(require_roles(Role.MODERATOR, Role.ADMIN))]
RequireClient = Annotated[User, Depends(require_roles(Role.CLIENT))]
RequireProvider = Annotated[User, Depends(require_roles(Role.PROVIDER))]
