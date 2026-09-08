from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.chat import router as chat_router
from app.api.routes.health import router as health_router
from app.api.routes.ingestion import router as ingestion_router
from app.api.routes.admin import router as admin_router
from app.api.routes.tickets import router as tickets_router
from app.core.config import settings

app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
	CORSMiddleware,
	allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
	allow_methods=["GET", "POST"],
	allow_headers=["*"],
)
app.include_router(health_router, tags=["health"])
app.include_router(ingestion_router, prefix="/ingestion", tags=["ingestion"])
app.include_router(chat_router, tags=["chat"])
app.include_router(admin_router)
app.include_router(tickets_router)