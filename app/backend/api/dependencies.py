from dataclasses import dataclass

from fastapi import Depends
from sqlmodel import Session

from app.backend.application.app_services import PrinterAccessService
from app.backend.application.ports import OrchestratorGatewayPort
from app.backend.infrastructure.db import get_session
from app.backend.infrastructure.orchestrator_gateway import OrchestratorGateway
from app.backend.infrastructure.repositories import SqlModelJobRepository, SqlModelPrinterRepository


@dataclass
class BackendDependencies:
    printer_repo: SqlModelPrinterRepository
    job_repo: SqlModelJobRepository
    printer_access: PrinterAccessService
    orchestrator_gateway: OrchestratorGatewayPort


def get_backend_dependencies(session: Session = Depends(get_session)) -> BackendDependencies:
    printer_repo = SqlModelPrinterRepository(session)
    job_repo = SqlModelJobRepository(session)
    printer_access = PrinterAccessService(printer_repo=printer_repo)
    orchestrator_gateway = OrchestratorGateway()
    return BackendDependencies(
        printer_repo=printer_repo,
        job_repo=job_repo,
        printer_access=printer_access,
        orchestrator_gateway=orchestrator_gateway,
    )
