from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["orchestrator"])

_TEMPLATE_PATH = Path(__file__).resolve().parents[2] / "templates" / "dashboard.html"


@router.get("/dashboard", response_class=FileResponse)
def dashboard() -> FileResponse:
    return FileResponse(_TEMPLATE_PATH, media_type="text/html; charset=utf-8")
