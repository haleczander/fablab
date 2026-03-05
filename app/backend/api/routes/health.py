from fastapi import APIRouter

router = APIRouter(tags=["backend-api"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "backend"}
