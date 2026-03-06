from fastapi import APIRouter

from orchestrator.api.routes.orchestrator.bindings import router as bindings_router
from orchestrator.api.routes.orchestrator.dashboard import router as dashboard_router
from orchestrator.api.routes.orchestrator.devices import router as devices_router
from orchestrator.api.routes.orchestrator.health import router as health_router
from orchestrator.api.routes.orchestrator.printers import router as printers_router
from orchestrator.api.routes.orchestrator.ws import router as ws_router

router = APIRouter(tags=["orchestrator"])
router.include_router(health_router)
router.include_router(dashboard_router)
router.include_router(printers_router)
router.include_router(devices_router)
router.include_router(bindings_router)
router.include_router(ws_router)

