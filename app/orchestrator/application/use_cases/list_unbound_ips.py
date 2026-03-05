from app.orchestrator.application.app_services import FleetViewService


class ListUnboundIpsUseCase:
    def __init__(self, fleet_view: FleetViewService) -> None:
        self.fleet_view = fleet_view

    def execute(self) -> list[dict[str, str | None]]:
        return self.fleet_view.list_unbound_ips()
