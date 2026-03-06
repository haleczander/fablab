from fastapi import APIRouter

from backend.api.routes.cms import router as cms_router
from backend.api.routes.health import router as health_router
from backend.api.routes.jobs import router as jobs_router
from backend.api.routes.machines import router as machines_router
from backend.api.routes.printers import router as printers_router

router = APIRouter(tags=["backend-api"])
router.include_router(health_router)
router.include_router(printers_router)
router.include_router(jobs_router)
router.include_router(machines_router)
router.include_router(cms_router)

