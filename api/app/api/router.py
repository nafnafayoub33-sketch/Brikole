"""Everything the API exposes, mounted under /api/v1."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import (
    admin,
    admin_settings,
    approvals,
    auth,
    catalog,
    credit,
    disputes,
    health,
    jobs,
    offers,
    pro,
    providers,
    reports,
    requests,
    uploads,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(catalog.router)
api_router.include_router(credit.router)
api_router.include_router(disputes.router)
api_router.include_router(providers.router)
api_router.include_router(uploads.router)
api_router.include_router(pro.router)
api_router.include_router(requests.router)
api_router.include_router(reports.router)
api_router.include_router(jobs.router)
api_router.include_router(offers.router)
api_router.include_router(admin.router)
api_router.include_router(admin_settings.router)
api_router.include_router(approvals.router)
