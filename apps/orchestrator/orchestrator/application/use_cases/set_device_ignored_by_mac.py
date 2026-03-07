from orchestrator.application.ports import PrinterBindingRepositoryPort
from orchestrator.domain.mac import normalize_mac
from orchestrator.domain.models import PrinterBinding


class SetDeviceIgnoredByMacUseCase:
    def __init__(self, binding_repo: PrinterBindingRepositoryPort) -> None:
        self._binding_repo = binding_repo

    def execute(
        self,
        device_mac: str,
        device_ip: str,
        is_ignored: bool,
        device_serial: str | None = None,
        detected_adapter: str | None = None,
        detected_model: str | None = None,
    ) -> PrinterBinding:
        mac = normalize_mac(device_mac)
        if not mac:
            raise ValueError("invalid device_mac")

        row = self._binding_repo.get_by_mac(mac)
        if not row:
            if not is_ignored:
                raise LookupError("device not found")
            row = PrinterBinding(printer_mac=mac, printer_ip=device_ip or None, is_ignored=True)

        row.is_ignored = is_ignored
        row.printer_ip = device_ip or row.printer_ip
        return self._binding_repo.save(row)
