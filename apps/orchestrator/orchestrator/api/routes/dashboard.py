from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["orchestrator"])

_TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "templates" / "dashboard.html"
_CSS_PATH = Path(__file__).resolve().parents[1] / "templates" / "dashboard.css"
_JS_PATH = Path(__file__).resolve().parents[1] / "templates" / "dashboard.js"


@router.get("/dashboard", response_class=FileResponse)
def dashboard() -> FileResponse:
    return FileResponse(_TEMPLATE_PATH, media_type="text/html; charset=utf-8")


@router.get("/dashboard.css", response_class=FileResponse)
def dashboard_css() -> FileResponse:
    return FileResponse(_CSS_PATH, media_type="text/css; charset=utf-8")


@router.get("/dashboard.js", response_class=FileResponse)
def dashboard_js() -> FileResponse:
    return FileResponse(_JS_PATH, media_type="text/javascript; charset=utf-8")
