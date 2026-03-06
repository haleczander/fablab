from orchestrator.application.ports import (
    DeviceRuntimeRepositoryPort,
    PrinterBindingRepositoryPort,
    PrinterRuntimeRepositoryPort,
)
from orchestrator.infrastructure.state.live_machine_state import get_machine_state


class FleetViewService:
    SUPPORTED_ADAPTERS = {"prusalink"}

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
            device = None
            if binding.printer_mac:
                device = self.device_runtime_repo.get_by_mac(binding.printer_mac)
            if not device and binding.printer_serial:
                device = self.device_runtime_repo.get_by_serial(binding.printer_serial)
            if not device and binding.printer_ip:
                device = self.device_runtime_repo.get_by_ip(binding.printer_ip)
            live = get_machine_state(binding.printer_id)

            rows.append(
                {
                    "printer_id": binding.printer_id,
                    "printer_ip": binding.printer_ip,
                    "printer_mac": binding.printer_mac,
                    "printer_serial": binding.printer_serial,
                    "printer_model": binding.printer_model,
                    "adapter_name": binding.adapter_name or (device.detected_adapter if device else None),
                    "status": str(live.get("status")) if live and live.get("status") is not None else None,
                    "current_job_id": str(live.get("current_job_id")) if live and live.get("current_job_id") is not None else None,
                    "progress_pct": str(live.get("progress_pct")) if live and live.get("progress_pct") is not None else None,
                    "nozzle_temp_c": str(live.get("nozzle_temp_c")) if live and live.get("nozzle_temp_c") is not None else None,
                    "bed_temp_c": str(live.get("bed_temp_c")) if live and live.get("bed_temp_c") is not None else None,
                    "last_heartbeat_at": str(live.get("last_heartbeat_at")) if live and live.get("last_heartbeat_at") is not None else None,
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
                    "device_serial": device.device_serial,
                    "status": device.status,
                    "detected_model": device.detected_model,
                    "detected_adapter": device.detected_adapter,
                    "last_heartbeat_at": device.last_heartbeat_at.isoformat() if device.last_heartbeat_at else None,
                }
            )
        rows.sort(key=lambda r: r["device_ip"] or "")
        return rows

    def list_unmatched_contract_devices(self) -> list[dict[str, str | None]]:
        rows: list[dict[str, str | None]] = []
        for device in self.device_runtime_repo.list_all():
            adapter = (device.detected_adapter or "").lower()
            if adapter in self.SUPPORTED_ADAPTERS:
                continue
            rows.append(
                {
                    "device_ip": device.device_ip,
                    "device_mac": device.device_mac,
                    "device_serial": device.device_serial,
                    "status": device.status,
                    "detected_model": device.detected_model,
                    "detected_adapter": device.detected_adapter,
                    "last_heartbeat_at": device.last_heartbeat_at.isoformat() if device.last_heartbeat_at else None,
                }
            )
        rows.sort(key=lambda r: r["device_ip"] or "")
        return rows

    def machine_states_payload(self) -> list[dict[str, str | None]]:
        payload: list[dict[str, str | None]] = []
        for device in self.device_runtime_repo.list_all():
            if device.is_ignored:
                continue

            binding = None
            if device.device_serial:
                binding = self.binding_repo.get_by_serial(device.device_serial)
            if not binding and device.device_mac:
                binding = self.binding_repo.get_by_mac(device.device_mac)
            if not binding and device.device_ip:
                binding = self.binding_repo.get_by_ip(device.device_ip)

            printer_id = binding.printer_id if binding else None
            live = get_machine_state(printer_id) if printer_id else None
            machine_id = printer_id or device.device_serial or device.device_mac or device.device_ip

            status = live.get("status") if live and live.get("status") is not None else device.status
            current_job_id = (
                live.get("current_job_id")
                if live and live.get("current_job_id") is not None
                else device.current_job_id
            )
            progress_pct = (
                live.get("progress_pct")
                if live and live.get("progress_pct") is not None
                else device.progress_pct
            )
            nozzle_temp_c = (
                live.get("nozzle_temp_c")
                if live and live.get("nozzle_temp_c") is not None
                else device.nozzle_temp_c
            )
            bed_temp_c = (
                live.get("bed_temp_c")
                if live and live.get("bed_temp_c") is not None
                else device.bed_temp_c
            )
            last_heartbeat_at = (
                live.get("last_heartbeat_at")
                if live and live.get("last_heartbeat_at") is not None
                else (device.last_heartbeat_at.isoformat() if device.last_heartbeat_at else None)
            )

            payload.append(
                {
                    "printer_id": printer_id,
                    "printer_ip": (binding.printer_ip if binding else None) or device.last_printer_ip or device.device_ip,
                    "printer_mac": (binding.printer_mac if binding else None) or device.last_printer_mac or device.device_mac,
                    "printer_serial": (binding.printer_serial if binding else None) or device.last_printer_serial or device.device_serial,
                    "printer_model": (binding.printer_model if binding else None) or device.detected_model,
                    "last_heartbeat_at": str(last_heartbeat_at) if last_heartbeat_at is not None else None,
                    "machine_id": machine_id,
                    "status": str(status) if status is not None else None,
                    "current_job_id": str(current_job_id) if current_job_id is not None else None,
                    "progress_pct": str(progress_pct) if progress_pct is not None else None,
                    "nozzle_temp_c": str(nozzle_temp_c) if nozzle_temp_c is not None else None,
                    "bed_temp_c": str(bed_temp_c) if bed_temp_c is not None else None,
                    "model": (binding.printer_model if binding else None) or device.detected_model,
                }
            )
        payload.sort(key=lambda item: item["machine_id"] or "")
        return payload

