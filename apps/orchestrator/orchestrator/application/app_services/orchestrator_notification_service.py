from __future__ import annotations

from typing import TYPE_CHECKING

from orchestrator.application.ports import NotificationPort
from orchestrator.domain.models import PrinterBinding

if TYPE_CHECKING:
    from orchestrator.application.use_cases.list_bindings import ListBindingsUseCase
    from orchestrator.application.use_cases.list_external_devices import ListExternalDevicesUseCase


class OrchestratorNotificationService:
    def __init__(
        self,
        notification_port: NotificationPort,
        list_bindings_use_case: ListBindingsUseCase,
        list_external_devices_use_case: ListExternalDevicesUseCase,
    ) -> None:
        self._notification_port = notification_port
        self._list_bindings_use_case = list_bindings_use_case
        self._list_external_devices_use_case = list_external_devices_use_case

    async def notify_binding_updated(self, row: PrinterBinding) -> None:
        _ = row
        await self.notify_devices_changed()
        await self.notify_external_devices_changed()

    async def notify_binding_deleted(self, device_mac: str) -> None:
        _ = device_mac
        await self.notify_devices_changed()
        await self.notify_external_devices_changed()

    async def notify_command_queued(self, payload: dict[str, str | int]) -> None:
        _ = payload
        await self.notify_devices_changed()
        await self.notify_external_devices_changed()

    async def notify_discovery_refreshed(self) -> None:
        await self.notify_devices_changed()
        await self.notify_external_devices_changed()

    async def notify_devices_changed(self) -> None:
        await self._notification_port.notify_device_rows(
            self._list_bindings_use_case.execute(include_ignored=True),
        )

    async def notify_external_devices_changed(self) -> None:
        await self._notification_port.notify_external_rows(
            self._list_external_devices_use_case.execute(),
        )
