import asyncio

from fastapi import FastAPI

from config import (
    ORCH_BOUND_REFRESH_INTERVAL_S,
    ORCH_DISCOVERY_CIDRS,
    ORCH_DISCOVERY_ENABLED,
    ORCH_DISCOVERY_INTERVAL_S,
    ORCH_DISCOVERY_TIMEOUT_S,
)
from orchestrator.api.routes.orchestrator import router as orchestrator_router
from orchestrator.infrastructure.network_discovery.runtime import bound_refresh_loop, discovery_loop
from orchestrator.infrastructure.persistence.db import init_db

app = FastAPI(title="fablab-local-orchestrator")
_discovery_stop_event: asyncio.Event | None = None
_discovery_task: asyncio.Task | None = None
_bound_refresh_task: asyncio.Task | None = None


@app.on_event("startup")
async def startup() -> None:
    global _discovery_stop_event, _discovery_task, _bound_refresh_task
    init_db()
    if ORCH_DISCOVERY_ENABLED:
        _discovery_stop_event = asyncio.Event()
        _discovery_task = asyncio.create_task(
            discovery_loop(
                stop_event=_discovery_stop_event,
                cidr=ORCH_DISCOVERY_CIDRS,
                timeout_s=ORCH_DISCOVERY_TIMEOUT_S,
                interval_s=ORCH_DISCOVERY_INTERVAL_S,
            )
        )
        _bound_refresh_task = asyncio.create_task(
            bound_refresh_loop(
                stop_event=_discovery_stop_event,
                timeout_s=ORCH_DISCOVERY_TIMEOUT_S,
                interval_s=ORCH_BOUND_REFRESH_INTERVAL_S,
            )
        )


@app.on_event("shutdown")
async def shutdown() -> None:
    global _discovery_stop_event, _discovery_task, _bound_refresh_task
    if _discovery_stop_event:
        _discovery_stop_event.set()
    if _bound_refresh_task:
        _bound_refresh_task.cancel()
        try:
            await _bound_refresh_task
        except asyncio.CancelledError:
            pass
    if _discovery_task:
        _discovery_task.cancel()
        try:
            await _discovery_task
        except asyncio.CancelledError:
            pass
    _bound_refresh_task = None
    _discovery_task = None
    _discovery_stop_event = None


app.include_router(orchestrator_router)


