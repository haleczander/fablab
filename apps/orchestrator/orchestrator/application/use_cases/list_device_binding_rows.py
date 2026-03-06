from orchestrator.application.ports import DeviceRuntimeRepositoryPort, PrinterBindingRepositoryPort


class ListDeviceBindingRowsUseCase:
    def __init__(
        self,
        device_runtime_repo: DeviceRuntimeRepositoryPort,
        binding_repo: PrinterBindingRepositoryPort,
    ) -> None:
        self.device_runtime_repo = device_runtime_repo
        self.binding_repo = binding_repo

    def execute(self, include_ignored: bool = False) -> list[dict[str, str | bool | int | None]]:
        rows: list[dict[str, str | bool | int | None]] = []
        for device in self.device_runtime_repo.list_all():
            if device.is_ignored and not include_ignored:
                continue
            binding = None
            if device.device_serial:
                binding = self.binding_repo.get_by_serial(device.device_serial)
            if not binding and device.device_mac:
                binding = self.binding_repo.get_by_mac(device.device_mac)
            if not binding and device.device_ip:
                binding = self.binding_repo.get_by_ip(device.device_ip)

            rows.append(
                {
                    "device_ip": device.device_ip,
                    "device_mac": device.device_mac,
                    "device_serial": device.device_serial,
                    "device_id": device.id,
                    "detected_adapter": device.detected_adapter,
                    "detected_model": device.detected_model,
                    "status": device.status,
                    "current_job_id": device.current_job_id,
                    "progress_pct": device.progress_pct,
                    "nozzle_temp_c": device.nozzle_temp_c,
                    "bed_temp_c": device.bed_temp_c,
                    "last_heartbeat_at": device.last_heartbeat_at.isoformat() if device.last_heartbeat_at else None,
                    "is_bound": binding is not None,
                    "is_ignored": device.is_ignored,
                    "printer_id": binding.printer_id if binding else None,
                    "printer_model": binding.printer_model if binding else None,
                }
            )
        rows.sort(key=lambda item: (not bool(item["is_bound"]), str(item["device_ip"] or "")))
        return rows
