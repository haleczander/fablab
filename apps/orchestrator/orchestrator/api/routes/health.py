from fastapi import APIRouter

router = APIRouter(tags=["orchestrator"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "orchestrator"}

