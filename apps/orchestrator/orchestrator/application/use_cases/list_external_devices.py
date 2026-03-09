from orchestrator.application.dependencies import autowired
from orchestrator.application.app_services.fleet_view import FleetViewService


class ListExternalDevicesUseCase:
    fleet_view: FleetViewService = autowired()

    def execute(self) -> list[dict[str, str | None]]:
        rows: list[dict[str, str | None]] = []
        for item in self.fleet_view.machine_states_payload():
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
