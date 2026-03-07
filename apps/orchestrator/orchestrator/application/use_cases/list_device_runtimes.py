from collections.abc import Callable

from orchestrator.domain.services import OrchestratorDomainService


class ListDeviceRuntimesUseCase:
    def __init__(
        self,
        discovery_snapshot_provider: Callable[[], list[dict[str, str | bool | int | float | None]]],
        domain_service: OrchestratorDomainService | None = None,
    ) -> None:
        self._discovery_snapshot_provider = discovery_snapshot_provider
        self._domain_service = domain_service or OrchestratorDomainService()

    def execute(self) -> list[dict[str, str | bool | float | None]]:
        rows: list[dict[str, str | bool | float | None]] = []
        for item in self._discovery_snapshot_provider():
            device = self._domain_service.device_from_snapshot(item)
            rows.append(
                {
                    "device_ip": str(device.ip) if device.ip else None,
                    "device_mac": str(device.mac) if device.mac else None,
                    "device_serial": device.serial,
                    "business_id": device.business_id,
                    "ignored": device.ignored,
                    "type": str(device.type),
                    "model": device.model,
                    "status": device.params.status,
                    "current_job_id": device.params.current_job_id,
                    "progress_pct": device.params.progress_pct,
                    "nozzle_temp_c": device.params.nozzle_temp_c,
                    "bed_temp_c": device.params.bed_temp_c,
                    "last_heartbeat_at": device.params.last_heartbeat_at,
                }
            )
        return rows

