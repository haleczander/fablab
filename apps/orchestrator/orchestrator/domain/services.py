from datetime import datetime, timezone

from config import ORCH_HEARTBEAT_REFRESH_S
from orchestrator.application.dto import PrinterStateInput
from orchestrator.domain.models import (
    Device,
    DeviceParams,
    DeviceType,
    IpAddress,
    MacAddress,
    PrinterBinding,
)

ALLOWED_STATUS = {"ON", "OFF", "IN_USE", "ERROR", "IDLE", "PRINTING"}


def to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class OrchestratorDomainService:
    def normalize_status(self, status: str) -> str:
        return status if status in ALLOWED_STATUS else "OFF"

    def should_refresh_heartbeat(self, last: datetime, status_changed: bool) -> bool:
        elapsed_s = (now_utc() - to_utc(last)).total_seconds()
        return status_changed or elapsed_s >= ORCH_HEARTBEAT_REFRESH_S

    def new_binding(
        self,
        printer_id: str | None,
        printer_mac: str,
        printer_ip: str | None = None,
        printer_model: str | None = None,
        is_ignored: bool = False,
    ) -> PrinterBinding:
        return PrinterBinding(
            printer_id=printer_id,
            printer_mac=printer_mac,
            printer_ip=printer_ip,
            printer_model=printer_model,
            bound_at=now_utc().isoformat() if printer_id else None,
            is_ignored=is_ignored,
        )

    def device_params_from_snapshot(
        self,
        row: dict[str, str | bool | int | float | None],
        *,
        fallback_status: str = "OFF",
    ) -> DeviceParams:
        return DeviceParams(
            status=self.normalize_status(str(row.get("status") or fallback_status)),
            current_job_id=str(row.get("current_job_id") or "") or None,
            progress_pct=float(row["progress_pct"]) if row.get("progress_pct") is not None else None,
            nozzle_temp_c=float(row["nozzle_temp_c"]) if row.get("nozzle_temp_c") is not None else None,
            bed_temp_c=float(row["bed_temp_c"]) if row.get("bed_temp_c") is not None else None,
            last_heartbeat_at=str(row.get("last_heartbeat_at") or "") or None,
        )

    def device_from_snapshot(
        self,
        row: dict[str, str | bool | int | float | None],
        *,
        binding: PrinterBinding | None = None,
    ) -> Device:
        params = self.device_params_from_snapshot(row)
        device = Device(
            mac=MacAddress.parse(str(row.get("device_mac") or "") or None),
            ip=IpAddress.parse(str(row.get("device_ip") or "") or None),
            business_id=binding.printer_id if binding else None,
            ignored=binding.is_ignored if binding else bool(row.get("is_ignored")),
            type=DeviceType.from_detected_adapter(str(row.get("detected_adapter") or "") or None),
            params=params,
            serial=str(row.get("device_serial") or "") or None,
            model=(binding.printer_model if binding and binding.printer_model else (str(row.get("detected_model") or "") or None)),
        )
        return device

    def device_from_binding(self, binding: PrinterBinding) -> Device:
        return Device(
            mac=MacAddress.parse(binding.printer_mac),
            ip=IpAddress.parse(binding.printer_ip),
            business_id=binding.printer_id,
            ignored=binding.is_ignored,
            type=DeviceType.UNKNOWN,
            params=DeviceParams(status="OFF"),
            model=binding.printer_model,
        )

