from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_session
from app.models.enums import ChatPlatform, TransactionSource
from app.models.user import User
from app.schemas.ai import (
    AIBudgetRequest,
    AIBudgetResponse,
    AIChatRequest,
    AIChatResponse,
    AIVoiceResponse,
)
from app.services.ai_service import AIService

router = APIRouter()


@router.post(
    "/chat",
    response_model=AIChatResponse,
    summary="AI Chat Assistant (Text Input)",
    description="Menganalisis teks pesan pengguna, mengekstrak niat (Catat Transaksi otomatis atau Q&A Data Finansial), dan mengembalikan respons cerdas.",
)
async def ai_chat_endpoint(
    payload: AIChatRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await AIService.process_chat_message(
        session=session,
        user_id=current_user.id,
        message=payload.message,
        platform=payload.platform,
        source=TransactionSource.AI_CHAT,
    )


@router.post(
    "/voice",
    response_model=AIVoiceResponse,
    summary="AI Voice Logging (Speech-to-Text & Processing)",
    description="Menerima file audio rekaman suara (.webm / .ogg / .wav / .mp3), mentranskripsikannya via Groq Whisper API (id), dan otomatis memproses hasilnya.",
)
async def ai_voice_endpoint(
    file: UploadFile = File(..., description="File audio rekaman suara dari Web atau Telegram"),
    platform: ChatPlatform = Form(ChatPlatform.WEB, description="Platform pengirim: web atau telegram"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    # Validasi format audio dasar
    allowed_extensions = (".webm", ".ogg", ".wav", ".mp3", ".m4a")
    filename = file.filename or "recording.webm"
    if not any(filename.lower().endswith(ext) for ext in allowed_extensions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Format audio tidak didukung. Format yang diizinkan: {', '.join(allowed_extensions)}",
        )

    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:  # Maks 10 MB
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ukuran file audio terlalu besar. Maksimal 10 MB.",
        )

    # 1. Transkripsi audio via Groq Whisper
    transcript = await AIService.transcribe_audio(
        file_bytes=file_bytes,
        filename=filename,
    )

    # 2. Proses hasil transkripsi ke AI Orchestrator
    chat_result = await AIService.process_chat_message(
        session=session,
        user_id=current_user.id,
        message=transcript,
        platform=platform,
        source=TransactionSource.AI_VOICE,
    )

    return AIVoiceResponse(
        transcript=transcript,
        chat_result=chat_result,
    )


@router.post(
    "/budget",
    response_model=AIBudgetResponse,
    summary="AI Dynamic Budgeting Engine",
    description="Menerima preferensi constraint anggaran dari user, menganalisis rata-rata historis pengeluaran, dan menghasilkan rekomendasi alokasi bulanan adaptif.",
)
async def ai_budget_endpoint(
    payload: AIBudgetRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await AIService.generate_auto_budget(
        session=session,
        user_id=current_user.id,
        payload=payload,
    )

