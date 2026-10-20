from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.api.v1.ai import router as ai_direct_router
from app.api.v1.telegram import router as telegram_direct_router
from app.core.config import settings
from app.services.telegram_bot import start_telegram_bot, stop_telegram_bot


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Siklus hidup aplikasi FastAPI: aktifkan bot Telegram saat startup dan tutup saat shutdown."""
    await start_telegram_bot()
    yield
    await stop_telegram_bot()


app = FastAPI(
    title="FinAI Track API",
    description="Smart Personal Finance & AI Assistant Backend (FastAPI + SQLModel + PostgreSQL + Redis + aiogram)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Konfigurasi Cross-Origin Resource Sharing (CORS) untuk Next.js Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Hubungkan API Router versi 1 (/api/v1/...)
app.include_router(api_router, prefix="/api/v1")

# Route langsung untuk kenyamanan integrasi AI & Telegram
app.include_router(ai_direct_router, prefix="/api/ai", tags=["AI Assistant Direct"])
app.include_router(telegram_direct_router, prefix="/api/telegram", tags=["Telegram Direct"])


@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "online",
        "service": "FinAI Track API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "redis": "connected",
    }
