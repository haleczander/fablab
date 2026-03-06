from orchestrator.application.app_services import FleetViewService


class ListUnmatchedContractDevicesUseCase:
    def __init__(self, fleet_view: FleetViewService) -> None:
        self.fleet_view = fleet_view

    def execute(self) -> list[dict[str, str | None]]:
        return self.fleet_view.list_unmatched_contract_devices()
