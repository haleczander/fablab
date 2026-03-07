from orchestrator.application.app_services import FleetViewService


class MachineStatesPayloadUseCase:
    def __init__(self, fleet_view: FleetViewService) -> None:
        self._fleet_view = fleet_view

    def execute(self) -> list[dict[str, str | None]]:
        return self._fleet_view.machine_states_payload()

