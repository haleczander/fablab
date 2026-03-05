from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.orchestrator.application import services
from app.orchestrator.domain.models import PrinterBinding, PrinterRuntime
from app.orchestrator.domain.schemas import BindPrinterInput, PrinterIngestInput, PrinterStateInput
from app.orchestrator.infrastructure.db import get_session

router = APIRouter(tags=["orchestrator"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "orchestrator"}


@router.get("/printers", response_model=list[PrinterRuntime])
def list_printers(session: Session = Depends(get_session)) -> list[PrinterRuntime]:
    return services.list_runtimes(session)


@router.get("/printer-bindings", response_model=list[PrinterBinding])
def list_bindings(session: Session = Depends(get_session)) -> list[PrinterBinding]:
    return services.list_bindings(session)


@router.post("/printer-bindings", response_model=PrinterBinding)
def bind_printer(payload: BindPrinterInput, session: Session = Depends(get_session)) -> PrinterBinding:
    return services.upsert_binding(session, payload.printer_id, str(payload.printer_ip))


@router.post("/printers/{printer_id}/state", response_model=PrinterRuntime)
def update_printer_state(
    printer_id: str,
    payload: PrinterStateInput,
    session: Session = Depends(get_session),
) -> PrinterRuntime:
    return services.upsert_runtime(session, printer_id=printer_id, data=payload)


@router.post("/printers/state-ingest", response_model=PrinterRuntime)
def ingest_printer_state(
    payload: PrinterIngestInput,
    session: Session = Depends(get_session),
) -> PrinterRuntime:
    binding = services.get_binding_by_printer_id(session, payload.printer_id)
    if not binding:
        raise HTTPException(status_code=404, detail="printer_id non associe a une IP interne")

    state = PrinterStateInput(
        status=payload.status,
        progress_pct=payload.progress_pct,
        nozzle_temp_c=payload.nozzle_temp_c,
        bed_temp_c=payload.bed_temp_c,
        current_job_id=payload.current_job_id,
    )
    return services.upsert_runtime(
        session,
        printer_id=payload.printer_id,
        data=state,
        source_printer_ip=binding.printer_ip,
    )


@router.post("/printers/{printer_id}/jobs/poll-once")
def poll_next_job(printer_id: str) -> dict[str, str | bool | None]:
    return services.poll_next_job_once(printer_id)
