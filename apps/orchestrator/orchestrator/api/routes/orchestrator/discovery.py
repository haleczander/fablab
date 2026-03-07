import asyncio

from fastapi import APIRouter, Depends

from orchestrator.api import dependencies
from orchestrator.application.app_services import OrchestratorNotificationService
from orchestrator.application.use_cases import (
    RefreshNetworkDiscoveryUseCase,
)
from orchestrator.domain.models import NetworkRange
from config import ORCH_DISCOVERY_CIDRS, ORCH_DISCOVERY_TIMEOUT_S

router = APIRouter(prefix="/discovery", tags=["orchestrator"])


@router.post("/refresh")
async def refresh_network_discovery(
    refresh_network_discovery_use_case: RefreshNetworkDiscoveryUseCase = Depends(
        dependencies.dep(RefreshNetworkDiscoveryUseCase)
    ),
    notifications: OrchestratorNotificationService = Depends(dependencies.get_orchestrator_notification_service),
) -> dict[str, int]:
    cidr = NetworkRange.parse(ORCH_DISCOVERY_CIDRS).cidr
    updated = await asyncio.to_thread(
        refresh_network_discovery_use_case.execute,
        cidr,
        ORCH_DISCOVERY_TIMEOUT_S,
    )
    await notifications.notify_discovery_refreshed()
    return {"updated": int(updated)}

