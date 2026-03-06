from orchestrator.application.ports import (
    DeviceRuntimeRepositoryPort,
    PrinterBindingRepositoryPort,
    PrinterRuntimeRepositoryPort,
)


class FleetViewService:
    def __init__(
        self,
        binding_repo: PrinterBindingRepositoryPort,
        printer_runtime_repo: PrinterRuntimeRepositoryPort,
        device_runtime_repo: DeviceRuntimeRepositoryPort,
    ) -> None:
        self.binding_repo = binding_repo
        self.printer_runtime_repo = printer_runtime_repo
        self.device_runtime_repo = device_runtime_repo

    def list_fleet(self) -> list[dict[str, str | None]]:
        rows: list[dict[str, str | None]] = []
        for binding in self.binding_repo.list_all():
            runtime = self.printer_runtime_repo.get_by_printer_id(binding.printer_id)
            device = None
            if binding.printer_mac:
                device = self.device_runtime_repo.get_by_mac(binding.printer_mac)
            if not device and binding.printer_ip:
                device = self.device_runtime_repo.get_by_ip(binding.printer_ip)
            heartbeat = None
            if runtime and runtime.last_heartbeat_at:
                heartbeat = runtime.last_heartbeat_at.isoformat()
            elif device and device.last_heartbeat_at:
                heartbeat = device.last_heartbeat_at.isoformat()

            rows.append(
                {
                    "printer_id": binding.printer_id,
                    "printer_ip": binding.printer_ip,
                    "printer_mac": binding.printer_mac,
                    "printer_model": binding.printer_model,
                    "status": runtime.status if runtime else (device.status if device else None),
                    "last_heartbeat_at": heartbeat,
                }
            )
        rows.sort(key=lambda r: r["printer_id"] or "")
        return rows

    def list_unbound_ips(self) -> list[dict[str, str | None]]:
        rows: list[dict[str, str | None]] = []
        for device in self.device_runtime_repo.list_all():
            if device.is_bound:
                continue
            rows.append(
                {
                    "device_ip": device.device_ip,
                    "device_mac": device.device_mac,
                    "status": device.status,
                    "detected_model": device.detected_model,
                    "last_heartbeat_at": device.last_heartbeat_at.isoformat() if device.last_heartbeat_at else None,
                }
            )
        rows.sort(key=lambda r: r["device_ip"] or "")
        return rows

    def machine_states_payload(self) -> list[dict[str, str | None]]:
        payload: list[dict[str, str | None]] = []
        for row in self.list_fleet():
            payload.append(
                {
                    "printer_id": row.get("printer_id"),
                    "printer_ip": row.get("printer_ip"),
                    "printer_mac": row.get("printer_mac"),
                    "printer_model": row.get("printer_model"),
                    "last_heartbeat_at": row.get("last_heartbeat_at"),
                    "machine_id": row.get("printer_id"),
                    "status": row.get("status"),
                    "model": row.get("printer_model"),
                }
            )
        payload.sort(key=lambda item: item["machine_id"] or "")
        return payload

