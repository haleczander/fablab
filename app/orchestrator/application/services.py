from datetime import datetime, timezone

from sqlmodel import Session, select

from app.backend.client import get_next_job, post_printer_state
from app.orchestrator.domain.models import PrinterBinding, PrinterRuntime
from app.orchestrator.domain.schemas import PrinterStateInput

ALLOWED_STATUS = {"ON", "OFF", "IN_USE", "ERROR", "IDLE", "PRINTING"}


def list_bindings(session: Session) -> list[PrinterBinding]:
    return list(session.exec(select(PrinterBinding)).all())


def list_runtimes(session: Session) -> list[PrinterRuntime]:
    return list(session.exec(select(PrinterRuntime)).all())


def upsert_binding(session: Session, printer_id: str, printer_ip: str) -> PrinterBinding:
    by_printer = session.exec(select(PrinterBinding).where(PrinterBinding.printer_id == printer_id)).first()
    by_ip = session.exec(select(PrinterBinding).where(PrinterBinding.printer_ip == printer_ip)).first()

    if by_ip and by_ip.printer_id != printer_id:
        session.delete(by_ip)
        session.commit()

    if by_printer:
        by_printer.printer_ip = printer_ip
        session.add(by_printer)
        session.commit()
        session.refresh(by_printer)
        return by_printer

    created = PrinterBinding(printer_id=printer_id, printer_ip=printer_ip)
    session.add(created)
    session.commit()
    session.refresh(created)
    return created


def get_printer_id_by_ip(session: Session, printer_ip: str) -> str | None:
    row = session.exec(select(PrinterBinding).where(PrinterBinding.printer_ip == printer_ip)).first()
    return row.printer_id if row else None


def get_binding_by_printer_id(session: Session, printer_id: str) -> PrinterBinding | None:
    return session.exec(select(PrinterBinding).where(PrinterBinding.printer_id == printer_id)).first()


def upsert_runtime(
    session: Session,
    printer_id: str,
    data: PrinterStateInput,
    source_printer_ip: str | None = None,
) -> PrinterRuntime:
    status = data.status if data.status in ALLOWED_STATUS else "OFF"
    row = session.exec(select(PrinterRuntime).where(PrinterRuntime.printer_id == printer_id)).first()

    if not row:
        row = PrinterRuntime(printer_id=printer_id)

    row.status = status
    row.last_heartbeat_at = datetime.now(timezone.utc)
    row.progress_pct = data.progress_pct
    row.nozzle_temp_c = data.nozzle_temp_c
    row.bed_temp_c = data.bed_temp_c
    row.current_job_id = data.current_job_id
    if source_printer_ip is not None:
        row.last_printer_ip = source_printer_ip

    session.add(row)
    session.commit()
    session.refresh(row)

    post_printer_state(
        printer_id,
        {
            "status": row.status,
            "last_heartbeat_at": row.last_heartbeat_at.isoformat(),
            "progress_pct": row.progress_pct,
            "nozzle_temp_c": row.nozzle_temp_c,
            "bed_temp_c": row.bed_temp_c,
            "current_job_id": row.current_job_id,
        },
    )
    return row


def poll_next_job_once(printer_id: str) -> dict[str, str | bool | None]:
    job = get_next_job(printer_id)
    if not job:
        return {"printer_id": printer_id, "job_found": False, "job_id": None}

    return {
        "printer_id": printer_id,
        "job_found": True,
        "job_id": str(job.get("job_id")) if job.get("job_id") is not None else None,
    }
