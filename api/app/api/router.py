"""Everything the API exposes, mounted under /api/v1."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import (
    admin,
    approvals,
    auth,
    catalog,
    health,
    pro,
    providers,
    requests,
    uploads,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(catalog.router)
api_router.include_router(providers.router)
api_router.include_router(uploads.router)
api_router.include_router(pro.router)
api_router.include_router(requests.router)
api_router.include_router(admin.router)
api_router.include_router(approvals.router)
