import asyncio
import json

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from config import ORCH_DISCOVERY_CIDRS, ORCH_DISCOVERY_TIMEOUT_S
from orchestrator.api import dependencies
from orchestrator.application.app_services import OrchestratorNotificationService
from orchestrator.application.use_cases import ListBindingsUseCase, RefreshNetworkDiscoveryUseCase
from orchestrator.domain.models import NetworkRange
from orchestrator.infrastructure.notifications import WebSocketNotificationAdapter

router = APIRouter(prefix="/devices", tags=["orchestrator"])


@router.post("/discover")
async def discover_devices(
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


@router.websocket("/ws")
async def ws_devices(
    websocket: WebSocket,
    list_bindings_use_case: ListBindingsUseCase = Depends(dependencies.get_list_bindings_use_case),
    notification_adapter: WebSocketNotificationAdapter = Depends(dependencies.get_notification_adapter),
) -> None:
    await websocket.accept()
    notification_adapter.add_device_client(websocket)
    try:
        rows = list_bindings_use_case.execute(include_ignored=True)
        await websocket.send_text(json.dumps({"event": "devices_snapshot", "payload": rows}))
        while True:
            if await websocket.receive_text() == "ping":
                await websocket.send_text(json.dumps({"event": "pong", "payload": None}))
    except WebSocketDisconnect:
        pass
    finally:
        notification_adapter.remove_device_client(websocket)
