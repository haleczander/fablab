import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from app.backend.api.routes.backend import router as backend_router
from app.backend.application.use_cases import RetryQueuedJobsUseCase
from app.backend.infrastructure.db import init_db
from app.backend.infrastructure.db import engine
from app.backend.infrastructure.orchestrator_gateway import OrchestratorGateway
from app.backend.infrastructure.orchestrator_ws import consume_machine_feed
from app.backend.infrastructure.repositories import SqlModelJobRepository

app = FastAPI(title="fablab-backend-api")
_ws_stop_event: asyncio.Event | None = None
_ws_task: asyncio.Task | None = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:8081",
        "http://127.0.0.1:8081",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:
    global _ws_stop_event, _ws_task
    init_db()
    with Session(engine) as session:
        RetryQueuedJobsUseCase(
            job_repo=SqlModelJobRepository(session),
            orchestrator_gateway=OrchestratorGateway(),
        ).execute()
    _ws_stop_event = asyncio.Event()
    _ws_task = asyncio.create_task(consume_machine_feed(_ws_stop_event))


@app.on_event("shutdown")
async def shutdown() -> None:
    global _ws_stop_event, _ws_task
    if _ws_stop_event:
        _ws_stop_event.set()
    if _ws_task:
        _ws_task.cancel()
        try:
            await _ws_task
        except asyncio.CancelledError:
            pass
        _ws_task = None
    _ws_stop_event = None


app.include_router(backend_router)
