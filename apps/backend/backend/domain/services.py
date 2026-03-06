import json
from datetime import datetime, timezone
from uuid import uuid4

from backend.domain.models import BackendJob, BackendPrinter
from backend.domain.schemas import CreateJobInput, JobProgressInput, PrinterStateReportInput

TERMINAL_JOB_STATUSES = {"DONE", "ERROR", "CANCELLED"}


class BackendDomainService:
    def new_printer(self, printer_id: str) -> BackendPrinter:
        return BackendPrinter(printer_id=printer_id, status="IDLE")

    def new_job(self, data: CreateJobInput) -> BackendJob:
        now = datetime.now(timezone.utc)
        return BackendJob(
            job_id=f"JOB-{uuid4().hex[:12].upper()}",
            printer_id=data.printer_id,
            gcode_url=data.gcode_url,
            parameters_json=json.dumps(data.parameters),
            status="QUEUED",
            created_at=now,
            updated_at=now,
        )

    def claim_next_job(self, job: BackendJob) -> dict:
        now = datetime.now(timezone.utc)
        job.status = "DISPATCHED"
        job.claimed_at = now
        job.updated_at = now
        return {
            "job_id": job.job_id,
            "printer_id": job.printer_id,
            "gcode_url": job.gcode_url,
            "parameters": json.loads(job.parameters_json),
        }

    def apply_printer_state(self, printer: BackendPrinter, data: PrinterStateReportInput) -> BackendPrinter:
        printer.status = data.status
        printer.last_heartbeat_at = data.last_heartbeat_at or datetime.now(timezone.utc)
        printer.current_job_id = data.current_job_id
        printer.progress_pct = data.progress_pct
        printer.nozzle_temp_c = data.nozzle_temp_c
        printer.bed_temp_c = data.bed_temp_c
        printer.updated_at = datetime.now(timezone.utc)
        return printer

    def apply_job_progress(self, job: BackendJob, data: JobProgressInput) -> BackendJob:
        job.status = data.status
        job.progress_pct = data.progress_pct
        job.message = data.message
        job.updated_at = datetime.now(timezone.utc)
        if data.status in TERMINAL_JOB_STATUSES:
            job.finished_at = datetime.now(timezone.utc)
        return job

