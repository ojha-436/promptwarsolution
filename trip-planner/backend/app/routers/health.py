from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Cloud Run liveness probe."""
    return {"status": "ok"}
