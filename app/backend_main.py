from fastapi import FastAPI

from app.backend.api.routes.backend import router as backend_router
from app.backend.api.routes.backoffice import router as backoffice_router
from app.backend.infrastructure.db import init_db

app = FastAPI(title="fablab-backend-and-backoffice")


@app.on_event("startup")
def startup() -> None:
    init_db()


app.include_router(backend_router)
app.include_router(backoffice_router)
