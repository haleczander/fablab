from collections.abc import Callable

from orchestrator.application.ports import PrinterBindingRepositoryPort
from orchestrator.domain.models import PrinterBinding


class GetBindingBySerialUseCase:
    def __init__(
        self,
        repo: PrinterBindingRepositoryPort,
        discovery_snapshot_provider: Callable[[], list[dict[str, str | bool | int | float | None]]],
    ) -> None:
        self.repo = repo
        self.discovery_snapshot_provider = discovery_snapshot_provider

    def execute(self, printer_serial: str) -> PrinterBinding | None:
        serial = str(printer_serial or "").strip()
        if not serial:
            return None
        for row in self.discovery_snapshot_provider():
            if str(row.get("device_serial") or "").strip() != serial:
                continue
            mac = str(row.get("device_mac") or "").strip()
            if mac:
                return self.repo.get_by_mac(mac)
        return None
