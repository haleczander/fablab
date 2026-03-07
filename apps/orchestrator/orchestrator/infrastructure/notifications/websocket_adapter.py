import json
from dataclasses import dataclass, field
from threading import Lock

from fastapi import WebSocket

from orchestrator.application.ports import NotificationPort


@dataclass
class WebSocketChannel:
    clients: set[WebSocket] = field(default_factory=set)
    lock: Lock = field(default_factory=Lock)


class WebSocketNotificationAdapter(NotificationPort):
    def __init__(self) -> None:
        self.events = WebSocketChannel()
        self.machines = WebSocketChannel()
        self.devices = WebSocketChannel()

    def add_event_client(self, websocket: WebSocket) -> None:
        self._add_client(self.events, websocket)

    def remove_event_client(self, websocket: WebSocket) -> None:
        self._remove_client(self.events, websocket)

    def add_machine_client(self, websocket: WebSocket) -> None:
        self._add_client(self.machines, websocket)

    def remove_machine_client(self, websocket: WebSocket) -> None:
        self._remove_client(self.machines, websocket)

    def add_device_client(self, websocket: WebSocket) -> None:
        self._add_client(self.devices, websocket)

    def remove_device_client(self, websocket: WebSocket) -> None:
        self._remove_client(self.devices, websocket)

    async def notify_event(self, event: str, payload: dict | list | None = None) -> None:
        await self._broadcast(
            channel=self.events,
            message=json.dumps({"event": event, "payload": payload}),
        )

    async def notify_devices(
        self,
        event: str,
        payload: list[dict[str, str | bool | int | None]],
    ) -> None:
        await self._broadcast(
            channel=self.devices,
            message=json.dumps({"event": event, "payload": payload}),
        )

    async def notify_machines(
        self,
        event: str,
        payload: list[dict[str, str | None]],
    ) -> None:
        await self._broadcast(
            channel=self.machines,
            message=json.dumps({"event": event, "payload": payload}),
        )

    def _add_client(self, channel: WebSocketChannel, websocket: WebSocket) -> None:
        with channel.lock:
            channel.clients.add(websocket)

    def _remove_client(self, channel: WebSocketChannel, websocket: WebSocket) -> None:
        with channel.lock:
            channel.clients.discard(websocket)

    async def _broadcast(self, channel: WebSocketChannel, message: str) -> None:
        with channel.lock:
            live_clients = list(channel.clients)

        dead: list[WebSocket] = []
        for client in live_clients:
            try:
                await client.send_text(message)
            except Exception:
                dead.append(client)

        if dead:
            with channel.lock:
                for client in dead:
                    channel.clients.discard(client)
