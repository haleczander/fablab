import json

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from config import ORCH_DISCOVERY_CIDRS, ORCH_DISCOVERY_TIMEOUT_S
from orchestrator.application.dependencies import autowired
from orchestrator.application.use_cases import DiscoverDevicesUseCase, ListBindingsUseCase
from orchestrator.infrastructure.notifications import WebSocketNotificationAdapter

router = APIRouter(prefix="/devices", tags=["orchestrator"])


class DevicesController:
    discover_devices_use_case: DiscoverDevicesUseCase = autowired()
    list_bindings_use_case: ListBindingsUseCase = autowired()
    notification_adapter: WebSocketNotificationAdapter = autowired()

    async def discover_devices(self) -> dict[str, int]:
        try:
            return await self.discover_devices_use_case.execute(
                ORCH_DISCOVERY_CIDRS,
                ORCH_DISCOVERY_TIMEOUT_S,
            )
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err)) from err
        except RuntimeError as err:
            raise HTTPException(status_code=502, detail=str(err)) from err

    async def ws_devices(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.notification_adapter.add_device_client(websocket)
        try:
            rows = self.list_bindings_use_case.execute(include_ignored=True)
            await websocket.send_text(json.dumps({"event": "devices_snapshot", "payload": rows}))
            while True:
                if await websocket.receive_text() == "ping":
                    await websocket.send_text(json.dumps({"event": "pong", "payload": None}))
        except WebSocketDisconnect:
            pass
        finally:
            self.notification_adapter.remove_device_client(websocket)


controller = DevicesController()
router.add_api_route("/discover", controller.discover_devices, methods=["POST"])
router.add_api_websocket_route("/ws", controller.ws_devices)
