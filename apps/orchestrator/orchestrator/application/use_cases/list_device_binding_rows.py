from typing import Callable

from orchestrator.application.ports import PrinterBindingRepositoryPort


class ListDeviceBindingRowsUseCase:
    def __init__(
        self,
        binding_repo: PrinterBindingRepositoryPort,
        discovery_snapshot_provider: Callable[[], list[dict[str, str | bool | int | float | None]]] | None = None,
    ) -> None:
        self._binding_repo = binding_repo
        self._discovery_snapshot_provider = discovery_snapshot_provider

    @staticmethod
    def _row_key(row: dict[str, str | bool | int | float | None]) -> str:
        return (
            str(row.get("device_mac") or "").strip()
            or str(row.get("device_serial") or "").strip()
            or str(row.get("device_ip") or "").strip()
        )

    def execute(self, include_ignored: bool = False) -> list[dict[str, str | bool | int | None]]:
        rows: list[dict[str, str | bool | int | None]] = []
        bindings = self._binding_repo.list_all()
        binding_by_mac = {binding.printer_mac: binding for binding in bindings if binding.printer_mac}

        emitted_keys: set[str] = set()
        if self._discovery_snapshot_provider:
            for item in self._discovery_snapshot_provider():
                key = self._row_key(item)
                if not key or key in emitted_keys:
                    continue
                emitted_keys.add(key)

                ip = str(item.get("device_ip") or "").strip()
                mac = str(item.get("device_mac") or "").strip()
                serial = str(item.get("device_serial") or "").strip()
                binding = binding_by_mac.get(mac) if mac else None
                if binding and binding.is_ignored and not include_ignored:
                    continue

                rows.append(
                    {
                        "device_ip": ip or None,
                        "device_mac": mac or None,
                        "device_serial": serial or None,
                        "device_id": binding.id if binding else None,
                        "detected_adapter": item.get("detected_adapter"),
                        "detected_model": item.get("detected_model"),
                        "status": item.get("status"),
                        "current_job_id": item.get("current_job_id"),
                        "progress_pct": item.get("progress_pct"),
                        "nozzle_temp_c": item.get("nozzle_temp_c"),
                        "bed_temp_c": item.get("bed_temp_c"),
                        "last_heartbeat_at": item.get("last_heartbeat_at"),
                        "is_bound": bool(binding and binding.printer_id),
                        "is_ignored": bool(binding.is_ignored) if binding else False,
                        "printer_id": binding.printer_id if binding else None,
                        "printer_model": binding.printer_model if binding else None,
                    }
                )
        for binding in bindings:
            if not binding.printer_id:
                continue
            key = binding.printer_mac or binding.printer_id
            if key in emitted_keys:
                continue
            rows.append(
                {
                    "device_ip": binding.printer_ip,
                    "device_mac": binding.printer_mac,
                    "device_serial": None,
                    "device_id": binding.id,
                    "detected_adapter": None,
                    "detected_model": None,
                    "status": "OFF",
                    "current_job_id": None,
                    "progress_pct": None,
                    "nozzle_temp_c": None,
                    "bed_temp_c": None,
                    "last_heartbeat_at": None,
                    "is_bound": True,
                    "is_ignored": binding.is_ignored,
                    "printer_id": binding.printer_id,
                    "printer_model": binding.printer_model,
                }
            )
        rows.sort(key=lambda item: (not bool(item["is_bound"]), str(item["device_ip"] or "")))
        return rows
