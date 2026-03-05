from datetime import datetime, timezone

from app.config import ORCH_HEARTBEAT_REFRESH_S
from app.orchestrator.domain.models import DeviceRuntime, PrinterBinding, PrinterRuntime
from app.orchestrator.domain.schemas import DeviceIngestInput, PrinterStateInput

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

    def new_binding(self, printer_id: str, printer_ip: str, printer_model: str | None, adapter_name: str | None) -> PrinterBinding:
        return PrinterBinding(
            printer_id=printer_id,
            printer_ip=printer_ip,
            printer_model=printer_model,
            adapter_name=adapter_name,
        )

    def new_printer_runtime(self, printer_id: str) -> PrinterRuntime:
        row = PrinterRuntime(printer_id=printer_id)
        row.last_heartbeat_at = now_utc()
        return row

    def new_device_runtime(self, device_ip: str) -> DeviceRuntime:
        row = DeviceRuntime(device_ip=device_ip)
        row.last_heartbeat_at = now_utc()
        return row

    def apply_printer_state(self, row: PrinterRuntime, data: PrinterStateInput, source_printer_ip: str | None = None) -> PrinterRuntime:
        status = self.normalize_status(data.status)
        if self.should_refresh_heartbeat(row.last_heartbeat_at, row.status != status):
            row.last_heartbeat_at = now_utc()

        row.status = status
        row.progress_pct = data.progress_pct
        row.nozzle_temp_c = data.nozzle_temp_c
        row.bed_temp_c = data.bed_temp_c
        row.current_job_id = data.current_job_id
        if source_printer_ip is not None:
            row.last_printer_ip = source_printer_ip
        return row

    def apply_device_state(self, row: DeviceRuntime, data: DeviceIngestInput, source_ip: str) -> DeviceRuntime:
        status = self.normalize_status(data.status)
        if self.should_refresh_heartbeat(row.last_heartbeat_at, row.status != status):
            row.last_heartbeat_at = now_utc()

        row.status = status
        row.progress_pct = data.progress_pct
        row.nozzle_temp_c = data.nozzle_temp_c
        row.bed_temp_c = data.bed_temp_c
        row.current_job_id = data.current_job_id
        row.last_printer_ip = source_ip
        return row

    def mark_job_sent(self, row: PrinterRuntime, job_id: str) -> PrinterRuntime:
        row.status = "IN_USE"
        row.current_job_id = job_id
        row.progress_pct = 0.0
        row.last_heartbeat_at = now_utc()
        return row

    def to_backend_payload(self, row: PrinterRuntime) -> dict:
        return {
            "status": row.status,
            "last_heartbeat_at": row.last_heartbeat_at.isoformat(),
            "progress_pct": row.progress_pct,
            "nozzle_temp_c": row.nozzle_temp_c,
            "bed_temp_c": row.bed_temp_c,
            "current_job_id": row.current_job_id,
        }
