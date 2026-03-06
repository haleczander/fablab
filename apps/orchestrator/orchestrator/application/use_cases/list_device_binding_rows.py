from orchestrator.application.ports import DeviceRuntimeRepositoryPort, PrinterBindingRepositoryPort
from typing import Callable


class ListDeviceBindingRowsUseCase:
    def __init__(
        self,
        device_runtime_repo: DeviceRuntimeRepositoryPort,
        binding_repo: PrinterBindingRepositoryPort,
        discovery_snapshot_provider: Callable[[], list[dict[str, str | bool | int | float | None]]] | None = None,
    ) -> None:
        self.device_runtime_repo = device_runtime_repo
        self.binding_repo = binding_repo
        self.discovery_snapshot_provider = discovery_snapshot_provider

    def execute(self, include_ignored: bool = False) -> list[dict[str, str | bool | int | None]]:
        rows: list[dict[str, str | bool | int | None]] = []
        persisted_by_ip: dict[str, object] = {}
        persisted_by_mac: dict[str, object] = {}
        persisted_by_serial: dict[str, object] = {}
        ignored_by_mac: dict[str, object] = {}

        devices = self.device_runtime_repo.list_all()
        for device in devices:
            if device.device_ip:
                persisted_by_ip[device.device_ip] = device
            if device.device_mac:
                persisted_by_mac[device.device_mac] = device
                if device.is_ignored:
                    ignored_by_mac[device.device_mac] = device
            if device.device_serial:
                persisted_by_serial[device.device_serial] = device

        # Bound view: comes from base (device_runtime + bindings)
        for device in devices:
            binding = None
            if device.device_serial:
                binding = self.binding_repo.get_by_serial(device.device_serial)
            if not binding and device.device_mac:
                binding = self.binding_repo.get_by_mac(device.device_mac)
            if not binding and device.device_ip:
                binding = self.binding_repo.get_by_ip(device.device_ip)
            if not binding:
                continue

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
                    "is_bound": True,
                    "is_ignored": device.is_ignored,
                    "printer_id": binding.printer_id,
                    "printer_model": binding.printer_model,
                }
            )

        # Ensure binded machines are visible even if runtime row was never created yet.
        for binding in self.binding_repo.list_all():
            has_device = False
            if binding.printer_serial and binding.printer_serial in persisted_by_serial:
                has_device = True
            if not has_device and binding.printer_mac and binding.printer_mac in persisted_by_mac:
                has_device = True
            if not has_device and binding.printer_ip and binding.printer_ip in persisted_by_ip:
                has_device = True
            if has_device:
                continue

            rows.append(
                {
                    "device_ip": binding.printer_ip,
                    "device_mac": binding.printer_mac,
                    "device_serial": binding.printer_serial,
                    "device_id": None,
                    "detected_adapter": binding.adapter_name,
                    "detected_model": binding.printer_model,
                    "status": "OFF",
                    "current_job_id": None,
                    "progress_pct": None,
                    "nozzle_temp_c": None,
                    "bed_temp_c": None,
                    "last_heartbeat_at": None,
                    "is_bound": True,
                    "is_ignored": False,
                    "printer_id": binding.printer_id,
                    "printer_model": binding.printer_model,
                }
            )

        # Available view: network snapshot + ignored tags from DB.
        emitted_keys: set[str] = set()
        if self.discovery_snapshot_provider:
            for item in self.discovery_snapshot_provider():
                ip = str(item.get("device_ip") or "").strip()
                mac = str(item.get("device_mac") or "").strip()
                serial = str(item.get("device_serial") or "").strip()
                key = mac or serial or ip
                if not key or key in emitted_keys:
                    continue
                emitted_keys.add(key)

                binding = None
                if serial:
                    binding = self.binding_repo.get_by_serial(serial)
                if not binding and mac:
                    binding = self.binding_repo.get_by_mac(mac)
                if not binding and ip:
                    binding = self.binding_repo.get_by_ip(ip)
                if binding:
                    continue

                ignored_device = ignored_by_mac.get(mac) if mac else None
                if ignored_device and not include_ignored:
                    continue

                rows.append(
                    {
                        "device_ip": ip or None,
                        "device_mac": mac or None,
                        "device_serial": serial or None,
                        "device_id": getattr(ignored_device, "id", None),
                        "detected_adapter": item.get("detected_adapter"),
                        "detected_model": item.get("detected_model"),
                        "status": None,
                        "current_job_id": None,
                        "progress_pct": None,
                        "nozzle_temp_c": None,
                        "bed_temp_c": None,
                        "last_heartbeat_at": None,
                        "is_bound": False,
                        "is_ignored": bool(getattr(ignored_device, "is_ignored", False)),
                        "printer_id": None,
                        "printer_model": None,
                    }
                )
        rows.sort(key=lambda item: (not bool(item["is_bound"]), str(item["device_ip"] or "")))
        return rows
