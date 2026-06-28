from fastapi import APIRouter
from datetime import datetime
from core.config import get_settings

router = APIRouter()


@router.get("/api/v1/health")
async def health():
    settings = get_settings()
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "index_ready": True,
        "model": settings.llm_model,
        "allowed_models": settings.allowed_models
    }
