from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.backend.application import services
from app.backend.domain.models import BackendJob, BackendPrinter
from app.backend.domain.schemas import (
    CreateJobInput,
    JobProgressInput,
    PrinterStateReportInput,
    RegisterPrinterInput,
)
from app.backend.infrastructure.db import get_session

router = APIRouter(tags=["backend-api"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "backend"}


@router.get("/printers", response_model=list[BackendPrinter])
def list_printers(session: Session = Depends(get_session)) -> list[BackendPrinter]:
    return services.list_printers(session)


@router.post("/printers/register", response_model=BackendPrinter)
def register_printer(payload: RegisterPrinterInput, session: Session = Depends(get_session)) -> BackendPrinter:
    return services.register_printer(session, payload.printer_id)


@router.get("/printers/{printer_id}/next-job")
def next_job(printer_id: str, session: Session = Depends(get_session)) -> dict | None:
    return services.get_next_job(session, printer_id)


@router.post("/printers/{printer_id}/state", response_model=BackendPrinter)
def report_printer_state(
    printer_id: str,
    payload: PrinterStateReportInput,
    session: Session = Depends(get_session),
) -> BackendPrinter:
    return services.upsert_printer_state(session, printer_id, payload)


@router.get("/jobs", response_model=list[BackendJob])
def list_jobs(session: Session = Depends(get_session)) -> list[BackendJob]:
    return services.list_jobs(session)


@router.post("/jobs", response_model=BackendJob)
def create_job(payload: CreateJobInput, session: Session = Depends(get_session)) -> BackendJob:
    return services.create_job(session, payload)


@router.post("/jobs/{job_id}/progress", response_model=BackendJob)
def update_job_progress(
    job_id: str,
    payload: JobProgressInput,
    session: Session = Depends(get_session),
) -> BackendJob:
    row = services.update_job_progress(session, job_id, payload)
    if not row:
        raise HTTPException(status_code=404, detail="job_id inconnu")
    return row
