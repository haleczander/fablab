from orchestrator.application.ports import DeviceRuntimeRepositoryPort, PrinterBindingRepositoryPort


class UnbindPrinterUseCase:
    def __init__(
        self,
        binding_repo: PrinterBindingRepositoryPort,
        device_runtime_repo: DeviceRuntimeRepositoryPort,
    ) -> None:
        self._binding_repo = binding_repo
        self._device_runtime_repo = device_runtime_repo

    def execute(self, printer_id: str) -> None:
        row = self._binding_repo.get_by_printer_id(printer_id)
        if not row:
            raise LookupError(f"binding introuvable pour {printer_id}")

        old_ip = row.printer_ip
        old_mac = row.printer_mac
        old_serial = row.printer_serial
        self._binding_repo.delete(row)

        device = None
        if old_serial:
            device = self._device_runtime_repo.get_by_serial(old_serial)
        if not device and old_mac:
            device = self._device_runtime_repo.get_by_mac(old_mac)
        if not device and old_ip:
            device = self._device_runtime_repo.get_by_ip(old_ip)
        if device:
            device.is_bound = False
            device.bound_printer_id = None
            self._device_runtime_repo.save(device)
