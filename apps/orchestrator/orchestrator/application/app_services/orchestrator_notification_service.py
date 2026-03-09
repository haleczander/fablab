from __future__ import annotations

from orchestrator.application.dependencies import autowired
from orchestrator.application.ports import NotificationPort
from orchestrator.application.use_cases.list_bindings import ListBindingsUseCase
from orchestrator.application.use_cases.list_external_devices import ListExternalDevicesUseCase
from orchestrator.domain.models import PrinterBinding


class OrchestratorNotificationService:
    notification_port: NotificationPort = autowired()
    list_bindings_use_case: ListBindingsUseCase = autowired()
    list_external_devices_use_case: ListExternalDevicesUseCase = autowired()

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
        await self.notification_port.notify_device_rows(
            self.list_bindings_use_case.execute(include_ignored=True),
        )

    async def notify_external_devices_changed(self) -> None:
        await self.notification_port.notify_external_rows(
            self.list_external_devices_use_case.execute(),
        )
