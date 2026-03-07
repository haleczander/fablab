import json

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from orchestrator.api.dependencies import (
    get_list_device_binding_rows_use_case,
    get_list_fleet_use_case,
    get_notification_adapter,
    get_list_unbound_ips_use_case,
    get_machine_states_payload_use_case,
)
from orchestrator.application.use_cases import (
    ListDeviceBindingRowsUseCase,
    ListFleetUseCase,
    ListUnboundIpsUseCase,
    MachineStatesPayloadUseCase,
)
from orchestrator.infrastructure.notifications import WebSocketNotificationAdapter

router = APIRouter(prefix="/ws", tags=["orchestrator"])


@router.websocket("/events")
async def ws_events(
    websocket: WebSocket,
    list_fleet_use_case: ListFleetUseCase = Depends(get_list_fleet_use_case),
    list_unbound_ips_use_case: ListUnboundIpsUseCase = Depends(get_list_unbound_ips_use_case),
    notification_adapter: WebSocketNotificationAdapter = Depends(get_notification_adapter),
) -> None:
    await websocket.accept()
    notification_adapter.add_event_client(websocket)
    try:
        snapshot = {
            "fleet": list_fleet_use_case.execute(),
            "unbound_ips": list_unbound_ips_use_case.execute(),
        }
        await websocket.send_text(json.dumps({"event": "snapshot", "payload": snapshot}))
        while True:
            if await websocket.receive_text() == "ping":
                await websocket.send_text(json.dumps({"event": "pong", "payload": None}))
    except WebSocketDisconnect:
        pass
    finally:
        notification_adapter.remove_event_client(websocket)


@router.websocket("/machines")
async def ws_machines(
    websocket: WebSocket,
    machine_states_use_case: MachineStatesPayloadUseCase = Depends(get_machine_states_payload_use_case),
    notification_adapter: WebSocketNotificationAdapter = Depends(get_notification_adapter),
) -> None:
    await websocket.accept()
    notification_adapter.add_machine_client(websocket)
    try:
        snapshot = machine_states_use_case.execute()
        await websocket.send_text(json.dumps({"event": "machines_snapshot", "payload": snapshot}))
        while True:
            if await websocket.receive_text() == "ping":
                await websocket.send_text(json.dumps({"event": "pong", "payload": None}))
    except WebSocketDisconnect:
        pass
    finally:
        notification_adapter.remove_machine_client(websocket)


@router.websocket("/devices")
async def ws_devices(
    websocket: WebSocket,
    list_device_binding_rows_use_case: ListDeviceBindingRowsUseCase = Depends(get_list_device_binding_rows_use_case),
    notification_adapter: WebSocketNotificationAdapter = Depends(get_notification_adapter),
) -> None:
    await websocket.accept()
    notification_adapter.add_device_client(websocket)
    try:
        rows = list_device_binding_rows_use_case.execute()
        await websocket.send_text(json.dumps({"event": "devices_snapshot", "payload": rows}))
        while True:
            if await websocket.receive_text() == "ping":
                await websocket.send_text(json.dumps({"event": "pong", "payload": None}))
    except WebSocketDisconnect:
        pass
    finally:
        notification_adapter.remove_device_client(websocket)

