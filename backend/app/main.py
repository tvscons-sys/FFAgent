from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.ingestion import router as ingestion_router
from app.core.config import settings

app = FastAPI(title=settings.app_name, version="0.1.0")
app.include_router(health_router, tags=["health"])
app.include_router(ingestion_router, prefix="/ingestion", tags=["ingestion"])