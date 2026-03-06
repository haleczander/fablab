from orchestrator.api.events import broadcast_devices, broadcast_events, broadcast_machines
from orchestrator.application.use_cases import (
    ListDeviceBindingRowsUseCase,
    ListFleetUseCase,
    ListUnboundIpsUseCase,
    ListUnmatchedContractDevicesUseCase,
    MachineStatesPayloadUseCase,
)


class OrchestratorNotifier:
    def __init__(
        self,
        list_fleet_use_case: ListFleetUseCase,
        list_unbound_ips_use_case: ListUnboundIpsUseCase,
        list_unmatched_contract_devices_use_case: ListUnmatchedContractDevicesUseCase,
        list_device_binding_rows_use_case: ListDeviceBindingRowsUseCase,
        machine_states_use_case: MachineStatesPayloadUseCase,
    ) -> None:
        self._list_fleet_use_case = list_fleet_use_case
        self._list_unbound_ips_use_case = list_unbound_ips_use_case
        self._list_unmatched_contract_devices_use_case = list_unmatched_contract_devices_use_case
        self._list_device_binding_rows_use_case = list_device_binding_rows_use_case
        self._machine_states_use_case = machine_states_use_case

    async def broadcast_fleet(self) -> None:
        await broadcast_events(
            "fleet_updated",
            {
                "fleet": self._list_fleet_use_case.execute(),
                "unbound_ips": self._list_unbound_ips_use_case.execute(),
                "unmatched_contract_devices": self._list_unmatched_contract_devices_use_case.execute(),
            },
        )

    async def broadcast_devices_snapshot(self) -> None:
        await broadcast_devices("devices_snapshot", self._list_device_binding_rows_use_case.execute())

    async def broadcast_machines(self) -> None:
        await broadcast_machines("machines_updated", self._machine_states_use_case.execute())

