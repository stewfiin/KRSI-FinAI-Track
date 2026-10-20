import uuid
from decimal import Decimal
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.models.enums import TransactionSource, TransactionType
from app.schemas.budget import BudgetAlert


class TransactionCreate(BaseModel):
    wallet_id: uuid.UUID = Field(..., description="ID dompet sumber")
    category_id: uuid.UUID = Field(..., description="ID kategori transaksi")
    amount: Decimal = Field(..., gt=0, description="Nominal transaksi (harus > 0)")
    type: TransactionType = Field(..., description="Tipe transaksi: income, expense, atau transfer")
    description: Optional[str] = Field(default=None, description="Catatan atau deskripsi transaksi")
    transaction_date: Optional[date] = Field(default=None, description="Tanggal transaksi (default: hari ini)")
    source: TransactionSource = Field(
        default=TransactionSource.MANUAL_WEB,
        description="Asal input transaksi: manual_web, ai_chat, ai_voice, telegram_bot",
    )
    # Khusus untuk tipe transaksi 'transfer'
    destination_wallet_id: Optional[uuid.UUID] = Field(
        default=None,
        description="ID dompet tujuan jika tipe transaksi adalah transfer",
    )


class TransactionUpdate(BaseModel):
    wallet_id: Optional[uuid.UUID] = None
    category_id: Optional[uuid.UUID] = None
    amount: Optional[Decimal] = Field(None, gt=0)
    type: Optional[TransactionType] = None
    description: Optional[str] = None
    transaction_date: Optional[date] = None


class TransactionResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    wallet_id: uuid.UUID
    category_id: uuid.UUID
    amount: Decimal
    type: TransactionType
    description: Optional[str] = None
    transaction_date: date
    source: TransactionSource
    created_at: datetime
    # Metadata relasi untuk kemudahan frontend
    wallet_name: Optional[str] = None
    category_name: Optional[str] = None
    category_color: Optional[str] = None
    category_icon: Optional[str] = None

    class Config:
        from_attributes = True


class TransactionResultResponse(BaseModel):
    """Respons pembuatan transaksi yang menyertakan data transaksi dan peringatan anggaran jika ada."""
    transaction: TransactionResponse
    budget_alert: Optional[BudgetAlert] = None

