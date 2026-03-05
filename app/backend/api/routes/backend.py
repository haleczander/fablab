import json

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlmodel import Session

from app.backend.application import services
from app.backend.domain.models import BackendJob, BackendPrinter
from app.backend.domain.schemas import (
    CreateJobInput,
    JobProgressInput,
    PrinterStateReportInput,
    RegisterPrinterInput,
)
from app.backend.infrastructure.db import engine, get_session

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


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "backend"}


@router.get("/printers", response_model=list[BackendPrinter])
def list_printers(session: Session = Depends(get_session)) -> list[BackendPrinter]:
    return services.list_printers(session)


@router.post("/printers/register", response_model=BackendPrinter)
async def register_printer(payload: RegisterPrinterInput, session: Session = Depends(get_session)) -> BackendPrinter:
    row = services.register_printer(session, payload.printer_id)
    await _broadcast("printer_registered", row.model_dump(mode="json"))
    return row


@router.get("/printers/{printer_id}/next-job")
def next_job(printer_id: str, session: Session = Depends(get_session)) -> dict | None:
    return services.get_next_job(session, printer_id)


@router.post("/printers/{printer_id}/state", response_model=BackendPrinter)
async def report_printer_state(
    printer_id: str,
    payload: PrinterStateReportInput,
    session: Session = Depends(get_session),
) -> BackendPrinter:
    row = services.upsert_printer_state(session, printer_id, payload)
    await _broadcast("printer_state", row.model_dump(mode="json"))
    return row


@router.websocket("/ws/printers")
async def ws_printers(websocket: WebSocket) -> None:
    await websocket.accept()
    ws_clients.add(websocket)
    try:
        with Session(engine) as session:
            snapshot = [p.model_dump(mode="json") for p in services.list_printers(session)]
        await websocket.send_text(json.dumps({"event": "snapshot", "payload": snapshot}))
        while True:
            if await websocket.receive_text() == "ping":
                await websocket.send_text(json.dumps({"event": "pong", "payload": None}))
    except WebSocketDisconnect:
        pass
    finally:
        ws_clients.discard(websocket)


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
