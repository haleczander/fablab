from orchestrator.application.ports import PrinterBindingRepositoryPort
from orchestrator.domain.models import MacAddress, PrinterBinding


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
        _ = device_serial, detected_adapter
        mac = MacAddress.parse(device_mac)
        if not mac:
            raise ValueError("invalid device_mac")

        row = self._binding_repo.get_by_mac(str(mac))
        if not row:
            if not is_ignored:
                raise LookupError("device not found")
            row = PrinterBinding(
                printer_mac=str(mac),
                printer_ip=device_ip or None,
                printer_model=detected_model or None,
                is_ignored=True,
            )

        row.is_ignored = is_ignored
        row.printer_ip = device_ip or row.printer_ip
        row.printer_model = detected_model or row.printer_model
        return self._binding_repo.save(row)
