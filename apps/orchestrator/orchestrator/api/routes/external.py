import json

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from orchestrator.api import dependencies
from orchestrator.application.use_cases import ListExternalDevicesUseCase
from orchestrator.infrastructure.notifications import WebSocketNotificationAdapter

router = APIRouter(prefix="/external", tags=["external"])


@router.websocket("/devices/ws")
async def ws_external_devices(
    websocket: WebSocket,
    list_external_devices_use_case: ListExternalDevicesUseCase = Depends(
        dependencies.get_list_external_devices_use_case
    ),
    notification_adapter: WebSocketNotificationAdapter = Depends(dependencies.get_notification_adapter),
) -> None:
    await websocket.accept()
    notification_adapter.add_external_device_client(websocket)
    try:
        rows = list_external_devices_use_case.execute()
        await websocket.send_text(json.dumps({"event": "devices_snapshot", "payload": rows}))
        while True:
            if await websocket.receive_text() == "ping":
                await websocket.send_text(json.dumps({"event": "pong", "payload": None}))
    except WebSocketDisconnect:
        pass
    finally:
        notification_adapter.remove_external_device_client(websocket)
