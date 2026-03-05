import json

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlmodel import Session

from app.backend.api.dependencies import BackendDependencies, get_backend_dependencies
from app.backend.application.use_cases import (
    GetNextJobUseCase,
    ListPrintersUseCase,
    RegisterPrinterUseCase,
    ReportPrinterStateUseCase,
)
from app.backend.domain.models import BackendPrinter
from app.backend.domain.schemas import PrinterStateReportInput, RegisterPrinterInput
from app.backend.infrastructure.db import engine
from app.backend.infrastructure.repositories import SqlModelPrinterRepository

router = APIRouter(tags=["backend-api"])
ws_clients: set[WebSocket] = set()


async def _broadcast(event: str, payload: dict | list | None = None) -> None:
    message = json.dumps({"event": event, "payload": payload})
    clients = list(ws_clients)
    dead: list[WebSocket] = []
    for client in clients:
        try:
            await client.send_text(message)
        except Exception:
            dead.append(client)
    for client in dead:
        ws_clients.discard(client)


@router.get("/printers", response_model=list[BackendPrinter])
def list_printers(deps: BackendDependencies = Depends(get_backend_dependencies)) -> list[BackendPrinter]:
    return ListPrintersUseCase(printer_repo=deps.printer_repo).execute()


@router.post("/printers/register", response_model=BackendPrinter)
async def register_printer(
    payload: RegisterPrinterInput,
    deps: BackendDependencies = Depends(get_backend_dependencies),
) -> BackendPrinter:
    row = RegisterPrinterUseCase(printer_access=deps.printer_access).execute(payload.printer_id)
    await _broadcast("printer_registered", row.model_dump(mode="json"))
    return row


@router.get("/printers/{printer_id}/next-job")
def next_job(printer_id: str, deps: BackendDependencies = Depends(get_backend_dependencies)) -> dict | None:
    return GetNextJobUseCase(job_repo=deps.job_repo).execute(printer_id)


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
    await _broadcast("printer_state", row.model_dump(mode="json"))
    return row


@router.websocket("/ws/printers")
async def ws_printers(websocket: WebSocket) -> None:
    await websocket.accept()
    ws_clients.add(websocket)
    try:
        with Session(engine) as session:
            printer_repo = SqlModelPrinterRepository(session)
            snapshot = [p.model_dump(mode="json") for p in ListPrintersUseCase(printer_repo=printer_repo).execute()]
        await websocket.send_text(json.dumps({"event": "snapshot", "payload": snapshot}))
        while True:
            if await websocket.receive_text() == "ping":
                await websocket.send_text(json.dumps({"event": "pong", "payload": None}))
    except WebSocketDisconnect:
        pass
    finally:
        ws_clients.discard(websocket)
