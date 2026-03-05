from sqlmodel import Session

from app.backend.application.app_services import PrinterAccessService
from app.backend.application.use_cases import (
    CreateJobUseCase,
    GetNextJobUseCase,
    ListJobsUseCase,
    ListPrintersUseCase,
    RegisterPrinterUseCase,
    ReportPrinterStateUseCase,
    UpdateJobProgressUseCase,
)
from app.backend.domain.models import BackendJob, BackendPrinter
from app.backend.domain.schemas import CreateJobInput, JobProgressInput, PrinterStateReportInput
from app.backend.infrastructure.repositories import SqlModelJobRepository, SqlModelPrinterRepository


def _build_dependencies(session: Session) -> tuple[SqlModelPrinterRepository, SqlModelJobRepository, PrinterAccessService]:
    printer_repo = SqlModelPrinterRepository(session)
    job_repo = SqlModelJobRepository(session)
    printer_access = PrinterAccessService(printer_repo=printer_repo)
    return printer_repo, job_repo, printer_access


def list_printers(session: Session) -> list[BackendPrinter]:
    printer_repo, _, _ = _build_dependencies(session)
    return ListPrintersUseCase(printer_repo=printer_repo).execute()


def list_jobs(session: Session) -> list[BackendJob]:
    _, job_repo, _ = _build_dependencies(session)
    return ListJobsUseCase(job_repo=job_repo).execute()


def register_printer(session: Session, printer_id: str) -> BackendPrinter:
    _, _, printer_access = _build_dependencies(session)
    return RegisterPrinterUseCase(printer_access=printer_access).execute(printer_id)


def create_job(session: Session, data: CreateJobInput) -> BackendJob:
    _, job_repo, printer_access = _build_dependencies(session)
    return CreateJobUseCase(job_repo=job_repo, printer_access=printer_access).execute(data)


def get_next_job(session: Session, printer_id: str) -> dict | None:
    _, job_repo, _ = _build_dependencies(session)
    return GetNextJobUseCase(job_repo=job_repo).execute(printer_id)


def upsert_printer_state(session: Session, printer_id: str, data: PrinterStateReportInput) -> BackendPrinter:
    printer_repo, _, printer_access = _build_dependencies(session)
    return ReportPrinterStateUseCase(printer_repo=printer_repo, printer_access=printer_access).execute(printer_id, data)


def update_job_progress(session: Session, job_id: str, data: JobProgressInput) -> BackendJob | None:
    _, job_repo, _ = _build_dependencies(session)
    return UpdateJobProgressUseCase(job_repo=job_repo).execute(job_id, data)
