import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlmodel import Session, select

from app.backend.domain.models import BackendJob, BackendPrinter
from app.backend.domain.schemas import CreateJobInput, JobProgressInput, PrinterStateReportInput

TERMINAL_JOB_STATUSES = {"DONE", "ERROR", "CANCELLED"}


def list_printers(session: Session) -> list[BackendPrinter]:
    return list(session.exec(select(BackendPrinter).order_by(BackendPrinter.printer_id)).all())


def list_jobs(session: Session) -> list[BackendJob]:
    return list(session.exec(select(BackendJob).order_by(BackendJob.created_at.desc())).all())


def register_printer(session: Session, printer_id: str) -> BackendPrinter:
    row = session.exec(select(BackendPrinter).where(BackendPrinter.printer_id == printer_id)).first()
    if row:
        return row

    row = BackendPrinter(printer_id=printer_id, status="IDLE")
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def create_job(session: Session, data: CreateJobInput) -> BackendJob:
    register_printer(session, data.printer_id)
    now = datetime.now(timezone.utc)
    row = BackendJob(
        job_id=f"JOB-{uuid4().hex[:12].upper()}",
        printer_id=data.printer_id,
        gcode_url=data.gcode_url,
        parameters_json=json.dumps(data.parameters),
        status="QUEUED",
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_next_job(session: Session, printer_id: str) -> dict | None:
    row = session.exec(
        select(BackendJob).where(
            BackendJob.printer_id == printer_id,
            BackendJob.status == "QUEUED",
        ).order_by(BackendJob.created_at.asc())
    ).first()
    if not row:
        return None

    now = datetime.now(timezone.utc)
    row.status = "DISPATCHED"
    row.claimed_at = now
    row.updated_at = now
    session.add(row)
    session.commit()
    session.refresh(row)

    return {
        "job_id": row.job_id,
        "printer_id": row.printer_id,
        "gcode_url": row.gcode_url,
        "parameters": json.loads(row.parameters_json),
    }


def upsert_printer_state(session: Session, printer_id: str, data: PrinterStateReportInput) -> BackendPrinter:
    row = session.exec(select(BackendPrinter).where(BackendPrinter.printer_id == printer_id)).first()
    if not row:
        row = BackendPrinter(printer_id=printer_id)

    row.status = data.status
    row.last_heartbeat_at = data.last_heartbeat_at or datetime.now(timezone.utc)
    row.current_job_id = data.current_job_id
    row.progress_pct = data.progress_pct
    row.nozzle_temp_c = data.nozzle_temp_c
    row.bed_temp_c = data.bed_temp_c
    row.updated_at = datetime.now(timezone.utc)

    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def update_job_progress(session: Session, job_id: str, data: JobProgressInput) -> BackendJob | None:
    row = session.exec(select(BackendJob).where(BackendJob.job_id == job_id)).first()
    if not row:
        return None

    row.status = data.status
    row.progress_pct = data.progress_pct
    row.message = data.message
    row.updated_at = datetime.now(timezone.utc)
    if data.status in TERMINAL_JOB_STATUSES:
        row.finished_at = datetime.now(timezone.utc)

    session.add(row)
    session.commit()
    session.refresh(row)
    return row
