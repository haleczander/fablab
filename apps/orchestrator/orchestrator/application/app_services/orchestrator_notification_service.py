from __future__ import annotations

from typing import TYPE_CHECKING

from orchestrator.application.ports import NotificationPort
from orchestrator.domain.models import PrinterBinding

if TYPE_CHECKING:
    from orchestrator.application.use_cases.list_device_binding_rows import ListDeviceBindingRowsUseCase
    from orchestrator.application.use_cases.list_fleet import ListFleetUseCase
    from orchestrator.application.use_cases.list_unbound_ips import ListUnboundIpsUseCase
    from orchestrator.application.use_cases.machine_states_payload import MachineStatesPayloadUseCase


class OrchestratorNotificationService:
    def __init__(
        self,
        notification_port: NotificationPort,
        list_fleet_use_case: ListFleetUseCase,
        list_unbound_ips_use_case: ListUnboundIpsUseCase,
        list_device_binding_rows_use_case: ListDeviceBindingRowsUseCase,
        machine_states_use_case: MachineStatesPayloadUseCase,
    ) -> None:
        self._notification_port = notification_port
        self._list_fleet_use_case = list_fleet_use_case
        self._list_unbound_ips_use_case = list_unbound_ips_use_case
        self._list_device_binding_rows_use_case = list_device_binding_rows_use_case
        self._machine_states_use_case = machine_states_use_case

    async def notify_binding_updated(self, row: PrinterBinding) -> None:
        await self._notification_port.notify_event("binding_updated", row.model_dump(mode="json"))
        await self.notify_topology_changed()

    async def notify_binding_deleted(self, printer_id: str) -> None:
        await self._notification_port.notify_event("binding_deleted", {"printer_id": printer_id})
        await self.notify_topology_changed()

    async def notify_command_queued(self, payload: dict[str, str | int]) -> None:
        await self._notification_port.notify_event("command_queued", payload)
        await self.notify_fleet_changed()
        await self.notify_machines_changed()

    async def notify_discovery_refreshed(self) -> None:
        await self.notify_devices_changed()
        await self.notify_machines_changed()

    async def notify_devices_changed(self) -> None:
        await self._notification_port.notify_devices(
            "devices_snapshot",
            self._list_device_binding_rows_use_case.execute(),
        )

    async def notify_machines_changed(self) -> None:
        await self._notification_port.notify_machines(
            "machines_updated",
            self._machine_states_use_case.execute(),
        )

    async def notify_fleet_changed(self) -> None:
        await self._notification_port.notify_event(
            "fleet_updated",
            {
                "fleet": self._list_fleet_use_case.execute(),
                "unbound_ips": self._list_unbound_ips_use_case.execute(),
            },
        )

    async def notify_topology_changed(self) -> None:
        await self.notify_fleet_changed()
        await self.notify_devices_changed()
        await self.notify_machines_changed()
