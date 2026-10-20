from typing import Optional
from pydantic import BaseModel, Field


class TelegramPairingCodeResponse(BaseModel):
    pairing_code: str = Field(..., description="6 digit kode OTP pairing")
    expires_in_seconds: int = Field(default=300, description="Sisa masa berlaku kode (detik)")
    bot_username: Optional[str] = Field(None, description="Username bot Telegram")
    deep_link: Optional[str] = Field(None, description="Tautan langsung ke bot Telegram")
    instructions: str = Field(
        ...,
        description="Petunjuk langkah untuk menghubungkan akun Telegram",
    )


class TelegramStatusResponse(BaseModel):
    is_linked: bool
    telegram_chat_id: Optional[int] = None

