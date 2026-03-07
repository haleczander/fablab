from orchestrator.application.app_services import FleetViewService


class ListFleetUseCase:
    def __init__(self, fleet_view: FleetViewService) -> None:
        self._fleet_view = fleet_view

    def execute(self) -> list[dict[str, str | None]]:
        return self._fleet_view.list_fleet()

