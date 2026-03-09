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
        self.devices = WebSocketChannel()
        self.external_devices = WebSocketChannel()
        self._device_rows_by_key: dict[str, dict[str, str | bool | int | float | None]] = {}
        self._device_rows_lock = Lock()
        self._external_rows_by_printer_id: dict[str, dict[str, str | None]] = {}
        self._external_rows_lock = Lock()

    def add_device_client(self, websocket: WebSocket) -> None:
        self._add_client(self.devices, websocket)

    def remove_device_client(self, websocket: WebSocket) -> None:
        self._remove_client(self.devices, websocket)

    def add_external_device_client(self, websocket: WebSocket) -> None:
        self._add_client(self.external_devices, websocket)

    def remove_external_device_client(self, websocket: WebSocket) -> None:
        self._remove_client(self.external_devices, websocket)

    async def notify_device_rows(
        self,
        rows: list[dict[str, str | bool | int | float | None]],
    ) -> None:
        current = {
            self._device_key(row): row
            for row in rows
            if self._device_key(row)
        }

        with self._device_rows_lock:
            previous = dict(self._device_rows_by_key)
            self._device_rows_by_key = current

        if not previous:
            await self._broadcast_event("devices_snapshot", rows)
            return

        for key, row in current.items():
            previous_row = previous.get(key)
            if previous_row is None:
                await self._broadcast_event("device_added", row)
                continue

            if self._binding_changed(previous_row, row):
                await self._broadcast_event("device_binding_updated", row)
            if self._state_changed(previous_row, row):
                await self._broadcast_event("device_state_updated", row)

        for key, row in previous.items():
            if key not in current:
                await self._broadcast_event(
                    "device_removed",
                    {
                        "device_key": key,
                        "device_mac": row.get("device_mac"),
                        "device_ip": row.get("device_ip"),
                    },
                )

    async def notify_external_rows(
        self,
        rows: list[dict[str, str | None]],
    ) -> None:
        current = {
            str(row.get("printer_id") or "").strip(): row
            for row in rows
            if str(row.get("printer_id") or "").strip()
        }

        with self._external_rows_lock:
            previous = dict(self._external_rows_by_printer_id)
            self._external_rows_by_printer_id = current

        if not previous:
            await self._broadcast_external("devices_snapshot", rows)
            return

        for printer_id, row in current.items():
            previous_row = previous.get(printer_id)
            if previous_row is None:
                await self._broadcast_external("device_added", row)
                continue
            if any(previous_row.get(key) != row.get(key) for key in row):
                await self._broadcast_external("device_state_updated", row)

        for printer_id in previous:
            if printer_id not in current:
                await self._broadcast_external("device_removed", {"printer_id": printer_id})

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

    async def _broadcast_event(self, event: str, payload: dict | list | None) -> None:
        await self._broadcast(
            channel=self.devices,
            message=json.dumps({"event": event, "payload": payload}),
        )

    async def _broadcast_external(self, event: str, payload: dict | list | None) -> None:
        await self._broadcast(
            channel=self.external_devices,
            message=json.dumps({"event": event, "payload": payload}),
        )

    @staticmethod
    def _device_key(row: dict[str, str | bool | int | float | None]) -> str:
        return str(
            row.get("device_mac")
            or row.get("device_serial")
            or row.get("device_ip")
            or ""
        ).strip()

    @staticmethod
    def _binding_changed(
        previous: dict[str, str | bool | int | float | None],
        current: dict[str, str | bool | int | float | None],
    ) -> bool:
        keys = ("device_id", "is_bound", "is_ignored", "printer_id", "printer_model")
        return any(previous.get(key) != current.get(key) for key in keys)

    @staticmethod
    def _state_changed(
        previous: dict[str, str | bool | int | float | None],
        current: dict[str, str | bool | int | float | None],
    ) -> bool:
        keys = (
            "device_ip",
            "detected_adapter",
            "detected_model",
            "status",
            "current_job_id",
            "progress_pct",
            "nozzle_temp_c",
            "bed_temp_c",
            "last_heartbeat_at",
        )
        return any(previous.get(key) != current.get(key) for key in keys)
