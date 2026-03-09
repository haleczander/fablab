

from fastapi import APIRouter

from orchestrator.api.routes.bindings import router as bindings_router
from orchestrator.api.routes.dashboard import router as dashboard_router
from orchestrator.api.routes.devices import router as devices_router
from orchestrator.api.routes.external import router as external_router
from orchestrator.api.routes.health import router as health_router
from orchestrator.api.routes.printers import router as printers_router

router = APIRouter()
router.include_router(health_router)
router.include_router(dashboard_router)
router.include_router(bindings_router)
router.include_router(devices_router)
router.include_router(external_router)
router.include_router(printers_router)

__all__ = ["router"]
