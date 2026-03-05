import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi import WebSocket, WebSocketDisconnect

from app.backend.api.dependencies import BackendDependencies, get_backend_dependencies
from app.backend.application.exceptions import DispatchTargetNotFoundError, PrinterNotRegisteredError
from app.backend.application.use_cases import CreateJobUseCase, ListJobsUseCase, UpdateJobProgressUseCase
from app.backend.domain.models import BackendJob
from app.backend.domain.schemas import CreateJobInput, JobProgressInput

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


@router.post("/jobs", response_model=BackendJob)
async def create_job(payload: CreateJobInput, deps: BackendDependencies = Depends(get_backend_dependencies)) -> BackendJob:
    try:
        row = CreateJobUseCase(
            job_repo=deps.job_repo,
            printer_access=deps.printer_access,
            orchestrator_gateway=deps.orchestrator_gateway,
        ).execute(payload)
    except PrinterNotRegisteredError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    except DispatchTargetNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    await _broadcast("job_created", row.model_dump(mode="json"))
    return row


@router.post("/jobs/{job_id}/progress", response_model=BackendJob)
async def update_job_progress(
    job_id: str,
    payload: JobProgressInput,
    deps: BackendDependencies = Depends(get_backend_dependencies),
) -> BackendJob:
    row = UpdateJobProgressUseCase(job_repo=deps.job_repo).execute(job_id, payload)
    if not row:
        raise HTTPException(status_code=404, detail="job_id inconnu")
    await _broadcast("job_updated", row.model_dump(mode="json"))
    return row


@router.websocket("/ws/jobs")
async def ws_jobs(websocket: WebSocket, deps: BackendDependencies = Depends(get_backend_dependencies)) -> None:
    await websocket.accept()
    ws_clients.add(websocket)
    try:
        snapshot = [j.model_dump(mode="json") for j in ListJobsUseCase(job_repo=deps.job_repo).execute()]
        await websocket.send_text(json.dumps({"event": "snapshot", "payload": snapshot}))
        while True:
            if await websocket.receive_text() == "ping":
                await websocket.send_text(json.dumps({"event": "pong", "payload": None}))
    except WebSocketDisconnect:
        pass
    finally:
        ws_clients.discard(websocket)
