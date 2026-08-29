"""The application: CORS, the error contract, and the router."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.config import API_PREFIX, get_settings
from app.core.errors import DomainError, ErrorCode
from app.schemas.common import ErrorOut


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Brikole API",
        version="0.1.0",
        description="Trade services marketplace — client, m3allem, moderator, admin.",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    # Credentials are on: the refresh token is an httpOnly cookie, so the
    # browser has to be allowed to send it back. That rules out "*" as an
    # origin, which is why the list is explicit in .env.
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(DomainError)
    def _domain_error(_request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.http_status, content=exc.as_dict())

    @app.exception_handler(RequestValidationError)
    def _validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        # Pydantic's own shape leaks internals and is not translatable. Collapse
        # it to the same {code, details} contract as everything else, keeping
        # only which field failed.
        fields = sorted(
            {".".join(str(p) for p in err["loc"][1:]) or "body" for err in exc.errors()}
        )
        body = ErrorOut(code=ErrorCode.VALIDATION_FAILED.value, details={"fields": fields})
        return JSONResponse(status_code=422, content=body.model_dump(exclude_none=True))

    @app.exception_handler(StarletteHTTPException)
    def _http_error(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {
            401: ErrorCode.NOT_AUTHENTICATED,
            403: ErrorCode.FORBIDDEN,
            404: ErrorCode.NOT_FOUND,
            409: ErrorCode.CONFLICT,
        }.get(exc.status_code, ErrorCode.VALIDATION_FAILED)
        body = ErrorOut(code=code.value).model_dump(exclude_none=True)
        return JSONResponse(status_code=exc.status_code, content=body)

    app.include_router(api_router, prefix=API_PREFIX)
    return app


app = create_app()
