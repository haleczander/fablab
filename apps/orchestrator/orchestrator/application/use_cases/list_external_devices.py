from orchestrator.application.app_services import FleetViewService


class ListExternalDevicesUseCase:
    def __init__(self, fleet_view: FleetViewService) -> None:
        self._fleet_view = fleet_view

    def execute(self) -> list[dict[str, str | None]]:
        rows: list[dict[str, str | None]] = []
        for item in self._fleet_view.machine_states_payload():
            rows.append(
                {
                    "printer_id": item.get("printer_id"),
                    "status": item.get("status"),
                    "current_job_id": item.get("current_job_id"),
                    "progress_pct": item.get("progress_pct"),
                    "nozzle_temp_c": item.get("nozzle_temp_c"),
                    "bed_temp_c": item.get("bed_temp_c"),
                    "last_heartbeat_at": item.get("last_heartbeat_at"),
                }
            )
        rows.sort(key=lambda item: item.get("printer_id") or "")
        return rows
