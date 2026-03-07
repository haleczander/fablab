from collections.abc import Callable

from orchestrator.application.ports import PrinterBindingRepositoryPort
from orchestrator.domain.services import OrchestratorDomainService
from orchestrator.infrastructure.state.live_machine_state import get_machine_state


class FleetViewService:
    SUPPORTED_ADAPTERS = {"prusalink"}

    def __init__(
        self,
        binding_repo: PrinterBindingRepositoryPort,
        discovery_snapshot_provider: Callable[[], list[dict[str, str | bool | int | float | None]]],
    ) -> None:
        self.binding_repo = binding_repo
        self.discovery_snapshot_provider = discovery_snapshot_provider
        self._domain_service = OrchestratorDomainService()

    def _snapshot_rows(self) -> list[dict[str, str | bool | int | float | None]]:
        return self.discovery_snapshot_provider() or []

    def _snapshot_by_mac(self) -> dict[str, dict[str, str | bool | int | float | None]]:
        out: dict[str, dict[str, str | bool | int | float | None]] = {}
        for row in self._snapshot_rows():
            mac = str(row.get("device_mac") or "").strip()
            if mac:
                out[mac] = row
        return out

    def list_fleet(self) -> list[dict[str, str | None]]:
        rows: list[dict[str, str | None]] = []
        snapshot_by_mac = self._snapshot_by_mac()
        for binding in self.binding_repo.list_all():
            if not binding.printer_id:
                continue
            device = snapshot_by_mac.get(binding.printer_mac)
            live = get_machine_state(binding.printer_id)
            domain_device = self._domain_service.device_from_snapshot(device or {}, binding=binding)

            rows.append(
                {
                    "printer_id": binding.printer_id,
                    "printer_ip": str(domain_device.ip) if domain_device.ip else None,
                    "printer_mac": str(domain_device.mac) if domain_device.mac else binding.printer_mac,
                    "printer_serial": domain_device.serial,
                    "printer_model": domain_device.model,
                    "adapter_name": str(domain_device.type),
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
        bindings_by_mac = {row.printer_mac: row for row in self.binding_repo.list_all()}
        for item in self._snapshot_rows():
            mac = str(item.get("device_mac") or "").strip()
            binding = bindings_by_mac.get(mac) if mac else None
            if binding and binding.printer_id:
                continue
            device = self._domain_service.device_from_snapshot(item, binding=binding)
            rows.append(
                {
                    "device_ip": str(device.ip) if device.ip else None,
                    "device_mac": str(device.mac) if device.mac else None,
                    "device_serial": device.serial,
                    "status": device.params.status,
                    "detected_model": device.model,
                    "detected_adapter": str(device.type),
                    "last_heartbeat_at": device.params.last_heartbeat_at,
                }
            )
        rows.sort(key=lambda r: r["device_ip"] or "")
        return rows

    def machine_states_payload(self) -> list[dict[str, str | None]]:
        payload: list[dict[str, str | None]] = []
        bindings_by_mac = {row.printer_mac: row for row in self.binding_repo.list_all()}
        for item in self._snapshot_rows():
            mac = str(item.get("device_mac") or "").strip()
            binding = bindings_by_mac.get(mac) if mac else None
            if not binding or not binding.printer_id or binding.is_ignored:
                continue
            printer_id = binding.printer_id
            live = get_machine_state(printer_id)
            machine_id = printer_id

            status = live.get("status") if live and live.get("status") is not None else item.get("status")
            current_job_id = (
                live.get("current_job_id")
                if live and live.get("current_job_id") is not None
                else item.get("current_job_id")
            )
            progress_pct = (
                live.get("progress_pct")
                if live and live.get("progress_pct") is not None
                else item.get("progress_pct")
            )
            nozzle_temp_c = (
                live.get("nozzle_temp_c")
                if live and live.get("nozzle_temp_c") is not None
                else item.get("nozzle_temp_c")
            )
            bed_temp_c = (
                live.get("bed_temp_c")
                if live and live.get("bed_temp_c") is not None
                else item.get("bed_temp_c")
            )
            last_heartbeat_at = (
                live.get("last_heartbeat_at")
                if live and live.get("last_heartbeat_at") is not None
                else item.get("last_heartbeat_at")
            )

            payload.append(
                {
                    "printer_id": printer_id,
                    "printer_ip": str(item.get("device_ip") or "") or binding.printer_ip or None,
                    "printer_mac": binding.printer_mac or mac or None,
                    "printer_serial": str(item.get("device_serial") or "") or None,
                    "printer_model": binding.printer_model or (str(item.get("detected_model") or "") or None),
                    "last_heartbeat_at": str(last_heartbeat_at) if last_heartbeat_at is not None else None,
                    "machine_id": machine_id,
                    "status": str(status) if status is not None else None,
                    "current_job_id": str(current_job_id) if current_job_id is not None else None,
                    "progress_pct": str(progress_pct) if progress_pct is not None else None,
                    "nozzle_temp_c": str(nozzle_temp_c) if nozzle_temp_c is not None else None,
                    "bed_temp_c": str(bed_temp_c) if bed_temp_c is not None else None,
                    "model": str(item.get("detected_model") or "") or None,
                }
            )
        seen_printer_ids = {item["printer_id"] for item in payload if item.get("printer_id")}
        for binding in self.binding_repo.list_all():
            if not binding.printer_id or binding.is_ignored or binding.printer_id in seen_printer_ids:
                continue
            live = get_machine_state(binding.printer_id)
            payload.append(
                {
                    "printer_id": binding.printer_id,
                    "printer_ip": binding.printer_ip,
                    "printer_mac": binding.printer_mac,
                    "printer_serial": None,
                    "printer_model": binding.printer_model,
                    "last_heartbeat_at": str(live.get("last_heartbeat_at")) if live and live.get("last_heartbeat_at") is not None else None,
                    "machine_id": binding.printer_id,
                    "status": str(live.get("status")) if live and live.get("status") is not None else "OFF",
                    "current_job_id": str(live.get("current_job_id")) if live and live.get("current_job_id") is not None else None,
                    "progress_pct": str(live.get("progress_pct")) if live and live.get("progress_pct") is not None else None,
                    "nozzle_temp_c": str(live.get("nozzle_temp_c")) if live and live.get("nozzle_temp_c") is not None else None,
                    "bed_temp_c": str(live.get("bed_temp_c")) if live and live.get("bed_temp_c") is not None else None,
                    "model": None,
                }
            )
        payload.sort(key=lambda item: item["machine_id"] or "")
        return payload

