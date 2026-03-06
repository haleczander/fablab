import json

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from orchestrator.api.dependencies import (
    get_list_device_binding_rows_use_case,
    get_list_fleet_use_case,
    get_list_unmatched_contract_devices_use_case,
    get_list_unbound_ips_use_case,
    get_machine_states_payload_use_case,
)
from orchestrator.api.events import (
    ws_device_clients,
    ws_device_lock,
    ws_events_clients,
    ws_events_lock,
    ws_machine_clients,
    ws_machine_lock,
)
from orchestrator.application.use_cases import (
    ListDeviceBindingRowsUseCase,
    ListFleetUseCase,
    ListUnboundIpsUseCase,
    ListUnmatchedContractDevicesUseCase,
    MachineStatesPayloadUseCase,
)

router = APIRouter(prefix="/ws", tags=["orchestrator"])


@router.websocket("/events")
async def ws_events(
    websocket: WebSocket,
    list_fleet_use_case: ListFleetUseCase = Depends(get_list_fleet_use_case),
    list_unbound_ips_use_case: ListUnboundIpsUseCase = Depends(get_list_unbound_ips_use_case),
    list_unmatched_contract_devices_use_case: ListUnmatchedContractDevicesUseCase = Depends(
        get_list_unmatched_contract_devices_use_case
    ),
) -> None:
    await websocket.accept()
    with ws_events_lock:
        ws_events_clients.add(websocket)
    try:
        snapshot = {
            "fleet": list_fleet_use_case.execute(),
            "unbound_ips": list_unbound_ips_use_case.execute(),
            "unmatched_contract_devices": list_unmatched_contract_devices_use_case.execute(),
        }
        await websocket.send_text(json.dumps({"event": "snapshot", "payload": snapshot}))
        while True:
            if await websocket.receive_text() == "ping":
                await websocket.send_text(json.dumps({"event": "pong", "payload": None}))
    except WebSocketDisconnect:
        pass
    finally:
        with ws_events_lock:
            ws_events_clients.discard(websocket)


@router.websocket("/machines")
async def ws_machines(
    websocket: WebSocket,
    machine_states_use_case: MachineStatesPayloadUseCase = Depends(get_machine_states_payload_use_case),
) -> None:
    await websocket.accept()
    with ws_machine_lock:
        ws_machine_clients.add(websocket)
    try:
        snapshot = machine_states_use_case.execute()
        await websocket.send_text(json.dumps({"event": "machines_snapshot", "payload": snapshot}))
        while True:
            if await websocket.receive_text() == "ping":
                await websocket.send_text(json.dumps({"event": "pong", "payload": None}))
    except WebSocketDisconnect:
        pass
    finally:
        with ws_machine_lock:
            ws_machine_clients.discard(websocket)


@router.websocket("/devices")
async def ws_devices(
    websocket: WebSocket,
    list_device_binding_rows_use_case: ListDeviceBindingRowsUseCase = Depends(get_list_device_binding_rows_use_case),
) -> None:
    await websocket.accept()
    with ws_device_lock:
        ws_device_clients.add(websocket)
    try:
        rows = list_device_binding_rows_use_case.execute()
        await websocket.send_text(json.dumps({"event": "devices_snapshot", "payload": rows}))
        while True:
            if await websocket.receive_text() == "ping":
                await websocket.send_text(json.dumps({"event": "pong", "payload": None}))
    except WebSocketDisconnect:
        pass
    finally:
        with ws_device_lock:
            ws_device_clients.discard(websocket)

