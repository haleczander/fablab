import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from orchestrator.application.dependencies import autowired
from orchestrator.application.use_cases import ListExternalDevicesUseCase
from orchestrator.infrastructure.notifications import WebSocketNotificationAdapter

router = APIRouter(prefix="/external", tags=["external"])


class ExternalDevicesController:
    list_external_devices_use_case: ListExternalDevicesUseCase = autowired()
    notification_adapter: WebSocketNotificationAdapter = autowired()

    async def ws_external_devices(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.notification_adapter.add_external_device_client(websocket)
        try:
            rows = self.list_external_devices_use_case.execute()
            await websocket.send_text(json.dumps({"event": "devices_snapshot", "payload": rows}))
            while True:
                if await websocket.receive_text() == "ping":
                    await websocket.send_text(json.dumps({"event": "pong", "payload": None}))
        except WebSocketDisconnect:
            pass
        finally:
            self.notification_adapter.remove_external_device_client(websocket)


controller = ExternalDevicesController()
router.add_api_websocket_route("/devices/ws", controller.ws_external_devices)
