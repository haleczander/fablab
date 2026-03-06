import json

from fastapi import APIRouter, Depends

from backend.api.dependencies import BackendDependencies, get_backend_dependencies
from backend.application.use_cases import RegisterPrinterUseCase, ReportPrinterStateUseCase
from backend.domain.models import BackendPrinter
from backend.domain.schemas import PrinterStateReportInput, RegisterPrinterInput

router = APIRouter(tags=["backend-api"])


@router.post("/printers/register", response_model=BackendPrinter)
async def register_printer(
    payload: RegisterPrinterInput,
    deps: BackendDependencies = Depends(get_backend_dependencies),
) -> BackendPrinter:
    return RegisterPrinterUseCase(printer_access=deps.printer_access).execute(payload.printer_id)


@router.post("/printers/{printer_id}/state", response_model=BackendPrinter)
async def report_printer_state(
    printer_id: str,
    payload: PrinterStateReportInput,
    deps: BackendDependencies = Depends(get_backend_dependencies),
) -> BackendPrinter:
    row = ReportPrinterStateUseCase(
        printer_repo=deps.printer_repo,
        printer_access=deps.printer_access,
    ).execute(printer_id, payload)
    return row

