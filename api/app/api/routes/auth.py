"""P4, P5 and everything that keeps a session alive."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response, status

from app.core.errors import DomainError, ErrorCode
from app.deps import (
    REFRESH_COOKIE,
    REFRESH_COOKIE_PATH,
    AuthServiceDep,
    CurrentUser,
    SettingsDep,
)
from app.schemas.auth import ChangePasswordIn, LoginIn, LoginOut, MeOut, RegisterIn, TokenOut
from app.services.auth import IssuedTokens, me_payload

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_refresh_cookie(response: Response, tokens: IssuedTokens, *, secure: bool) -> None:
    """The refresh token lives in an httpOnly cookie, never in JavaScript.

    Scoped to the auth routes so it is not attached to every API call, and
    `lax` so it survives a normal navigation without riding along on
    cross-site requests.
    """
    response.set_cookie(
        REFRESH_COOKIE,
        tokens.refresh,
        max_age=tokens.refresh_max_age,
        httponly=True,
        samesite="lax",
        secure=secure,
        path=REFRESH_COOKIE_PATH,
    )


@router.post("/register", response_model=LoginOut, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterIn, response: Response, auth: AuthServiceDep, settings: SettingsDep
) -> LoginOut:
    user = auth.register(
        phone=payload.phone,
        full_name=payload.full_name,
        password=payload.password,
        role=payload.role,
        language=payload.language,
    )
    tokens = auth.issue_tokens(user)
    _set_refresh_cookie(response, tokens, secure=settings.is_production)
    return LoginOut(token=tokens.access, user=me_payload(user))


@router.post("/login", response_model=LoginOut)
def login(
    payload: LoginIn, response: Response, auth: AuthServiceDep, settings: SettingsDep
) -> LoginOut:
    user = auth.authenticate(phone=payload.phone, password=payload.password)
    tokens = auth.issue_tokens(user)
    _set_refresh_cookie(response, tokens, secure=settings.is_production)
    return LoginOut(token=tokens.access, user=me_payload(user))


@router.post("/refresh", response_model=TokenOut)
def refresh(
    request: Request, response: Response, auth: AuthServiceDep, settings: SettingsDep
) -> TokenOut:
    cookie = request.cookies.get(REFRESH_COOKIE)
    if not cookie:
        raise DomainError(ErrorCode.NOT_AUTHENTICATED)
    _user, tokens = auth.refresh(cookie)
    # Rotate: the old refresh token is replaced on every use.
    _set_refresh_cookie(response, tokens, secure=settings.is_production)
    return tokens.access


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH)


@router.get("/me", response_model=MeOut)
def me(user: CurrentUser) -> MeOut:
    return me_payload(user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(payload: ChangePasswordIn, user: CurrentUser, auth: AuthServiceDep) -> None:
    auth.change_password(user, current=payload.current_password, new=payload.new_password)
