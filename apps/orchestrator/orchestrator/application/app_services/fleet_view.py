from collections.abc import Callable

from orchestrator.application.ports import PrinterBindingRepositoryPort
from orchestrator.domain.models import DeviceRuntime
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

    def _snapshot_rows(self) -> list[dict[str, str | bool | int | float | None]]:
        return self.discovery_snapshot_provider() or []

    def _snapshot_by_mac(self) -> dict[str, dict[str, str | bool | int | float | None]]:
        out: dict[str, dict[str, str | bool | int | float | None]] = {}
        for row in self._snapshot_rows():
            mac = str(row.get("device_mac") or "").strip()
            if mac:
                out[mac] = row
        return out

    def _row_to_device(
        self,
        row: dict[str, str | bool | int | float | None],
        *,
        binding_printer_id: str | None = None,
        is_ignored: bool = False,
    ) -> DeviceRuntime:
        last_heartbeat = row.get("last_heartbeat_at")
        return DeviceRuntime(
            device_ip=str(row.get("device_ip") or ""),
            device_mac=str(row.get("device_mac") or "") or None,
            device_serial=str(row.get("device_serial") or "") or None,
            is_bound=binding_printer_id is not None,
            is_ignored=is_ignored,
            bound_printer_id=binding_printer_id,
            detected_model=str(row.get("detected_model") or "") or None,
            detected_adapter=str(row.get("detected_adapter") or "") or None,
            probe_reachable=bool(row.get("status")),
            status=str(row.get("status") or "OFF"),
            current_job_id=str(row.get("current_job_id") or "") or None,
            progress_pct=float(row["progress_pct"]) if row.get("progress_pct") is not None else None,
            nozzle_temp_c=float(row["nozzle_temp_c"]) if row.get("nozzle_temp_c") is not None else None,
            bed_temp_c=float(row["bed_temp_c"]) if row.get("bed_temp_c") is not None else None,
            last_printer_ip=str(row.get("device_ip") or "") or None,
            last_printer_mac=str(row.get("device_mac") or "") or None,
            last_printer_serial=str(row.get("device_serial") or "") or None,
            last_heartbeat_at=last_heartbeat,  # type: ignore[arg-type]
        )

    def list_fleet(self) -> list[dict[str, str | None]]:
        rows: list[dict[str, str | None]] = []
        snapshot_by_mac = self._snapshot_by_mac()
        for binding in self.binding_repo.list_all():
            if not binding.printer_id:
                continue
            device = snapshot_by_mac.get(binding.printer_mac)
            live = get_machine_state(binding.printer_id)

            rows.append(
                {
                    "printer_id": binding.printer_id,
                    "printer_ip": str(device.get("device_ip")) if device and device.get("device_ip") is not None else None,
                    "printer_mac": binding.printer_mac,
                    "printer_serial": str(device.get("device_serial")) if device and device.get("device_serial") is not None else None,
                    "printer_model": str(device.get("detected_model")) if device and device.get("detected_model") is not None else None,
                    "adapter_name": str(device.get("detected_adapter")) if device and device.get("detected_adapter") is not None else None,
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
            rows.append(
                {
                    "device_ip": str(item.get("device_ip") or "") or None,
                    "device_mac": str(item.get("device_mac") or "") or None,
                    "device_serial": str(item.get("device_serial") or "") or None,
                    "status": str(item.get("status") or "") or None,
                    "detected_model": str(item.get("detected_model") or "") or None,
                    "detected_adapter": str(item.get("detected_adapter") or "") or None,
                    "last_heartbeat_at": str(item.get("last_heartbeat_at") or "") or None,
                }
            )
        rows.sort(key=lambda r: r["device_ip"] or "")
        return rows

    def list_unmatched_contract_devices(self) -> list[dict[str, str | None]]:
        rows: list[dict[str, str | None]] = []
        bindings_by_mac = {row.printer_mac: row for row in self.binding_repo.list_all()}
        for item in self._snapshot_rows():
            mac = str(item.get("device_mac") or "").strip()
            binding = bindings_by_mac.get(mac) if mac else None
            if binding and binding.is_ignored:
                continue
            adapter = str(item.get("detected_adapter") or "").lower()
            if adapter in self.SUPPORTED_ADAPTERS:
                continue
            rows.append(
                {
                    "device_ip": str(item.get("device_ip") or "") or None,
                    "device_mac": str(item.get("device_mac") or "") or None,
                    "device_serial": str(item.get("device_serial") or "") or None,
                    "status": str(item.get("status") or "") or None,
                    "detected_model": str(item.get("detected_model") or "") or None,
                    "detected_adapter": str(item.get("detected_adapter") or "") or None,
                    "last_heartbeat_at": str(item.get("last_heartbeat_at") or "") or None,
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
                    "printer_model": str(item.get("detected_model") or "") or None,
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
                    "printer_model": None,
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

