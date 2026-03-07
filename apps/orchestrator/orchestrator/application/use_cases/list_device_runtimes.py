from collections.abc import Callable

from orchestrator.domain.models import DeviceRuntime


class ListDeviceRuntimesUseCase:
    def __init__(
        self,
        discovery_snapshot_provider: Callable[[], list[dict[str, str | bool | int | float | None]]],
    ) -> None:
        self.discovery_snapshot_provider = discovery_snapshot_provider

    def execute(self) -> list[DeviceRuntime]:
        rows: list[DeviceRuntime] = []
        for item in self.discovery_snapshot_provider():
            rows.append(
                DeviceRuntime(
                    device_ip=str(item.get("device_ip") or ""),
                    device_mac=str(item.get("device_mac") or "") or None,
                    device_serial=str(item.get("device_serial") or "") or None,
                    detected_adapter=str(item.get("detected_adapter") or "") or None,
                    detected_model=str(item.get("detected_model") or "") or None,
                    status=str(item.get("status") or "OFF"),
                    current_job_id=str(item.get("current_job_id") or "") or None,
                    progress_pct=float(item["progress_pct"]) if item.get("progress_pct") is not None else None,
                    nozzle_temp_c=float(item["nozzle_temp_c"]) if item.get("nozzle_temp_c") is not None else None,
                    bed_temp_c=float(item["bed_temp_c"]) if item.get("bed_temp_c") is not None else None,
                    last_printer_ip=str(item.get("device_ip") or "") or None,
                    last_printer_mac=str(item.get("device_mac") or "") or None,
                    last_printer_serial=str(item.get("device_serial") or "") or None,
                    last_heartbeat_at=item.get("last_heartbeat_at"),  # type: ignore[arg-type]
                )
            )
        return rows

