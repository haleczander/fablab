from fastapi import FastAPI

from app.orchestrator.api.routes.orchestrator import router as orchestrator_router
from app.orchestrator.infrastructure.db import init_db

app = FastAPI(title="fablab-local-orchestrator")


@app.on_event("startup")
def startup() -> None:
    init_db()


app.include_router(orchestrator_router)
