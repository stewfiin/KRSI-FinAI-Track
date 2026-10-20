import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserRegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150, description="Nama lengkap pengguna")
    email: EmailStr = Field(..., description="Alamat email aktif")
    password: str = Field(..., min_length=6, max_length=100, description="Password minimal 6 karakter")
    default_currency: Optional[str] = Field(default="IDR", max_length=10, description="Mata uang bawaan")


class UserLoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Alamat email terdaftar")
    password: str = Field(..., description="Password pengguna")


class UserResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    default_currency: str
    telegram_chat_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

