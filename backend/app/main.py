from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.api.v1.ai import router as ai_direct_router
from app.core.config import settings

app = FastAPI(
    title="FinAI Track API",
    description="Smart Personal Finance & AI Assistant Backend (FastAPI + SQLModel + PostgreSQL)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
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

# Route langsung untuk AI endpoints sesuai PRD (/api/ai/...)
app.include_router(ai_direct_router, prefix="/api/ai", tags=["AI Assistant Direct"])


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
    }
