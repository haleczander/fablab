from orchestrator.application.dependencies import autowired
from orchestrator.application.app_services.fleet_view import FleetViewService


class MachineStatesPayloadUseCase:
    fleet_view: FleetViewService = autowired()

    def execute(self) -> list[dict[str, str | None]]:
        return self.fleet_view.machine_states_payload()

