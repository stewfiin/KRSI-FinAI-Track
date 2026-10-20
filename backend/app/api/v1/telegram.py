from fastapi import APIRouter, Depends, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_session
from app.core.redis import create_telegram_otp
from app.models.user import User
from app.schemas.telegram import TelegramPairingCodeResponse, TelegramStatusResponse

router = APIRouter()


@router.post(
    "/pairing-code",
    response_model=TelegramPairingCodeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate Kode OTP Pairing Telegram (5 Menit)",
    description="Menghasilkan 6 digit kode OTP yang disimpan di Redis selama 5 menit untuk ditautkan via bot Telegram.",
)
async def generate_pairing_code(
    current_user: User = Depends(get_current_user),
):
    code = await create_telegram_otp(user_id=current_user.id, ttl_seconds=300)
    instructions = (
        f"Kirim perintah `/link {code}` ke bot Telegram kami. "
        "Kode berlaku selama 5 menit."
    )

    return TelegramPairingCodeResponse(
        pairing_code=code,
        expires_in_seconds=300,
        instructions=instructions,
    )


@router.get(
    "/status",
    response_model=TelegramStatusResponse,
    summary="Status Tautan Telegram Akun",
    description="Mengecek apakah akun pengguna sudah terhubung dengan bot Telegram.",
)
async def get_telegram_status(
    current_user: User = Depends(get_current_user),
):
    return TelegramStatusResponse(
        is_linked=current_user.telegram_chat_id is not None,
        telegram_chat_id=current_user.telegram_chat_id,
    )


@router.delete(
    "/unlink",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Putus Tautan Akun Telegram",
)
async def unlink_telegram(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    current_user.telegram_chat_id = None
    session.add(current_user)
    await session.commit()
    return None

