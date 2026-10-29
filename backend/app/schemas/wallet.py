import uuid
from decimal import Decimal
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.models.enums import WalletType


class WalletCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Nama dompet/rekening (misal: BCA, Tunai, GoPay)")
    type: WalletType = Field(default=WalletType.CASH, description="Tipe dompet: cash, bank, atau ewallet")
    purpose: str = Field(default="operational", description="operational | savings | subscription")
    balance: Decimal = Field(default=Decimal("0.00"), description="Saldo awal dompet")


class WalletUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    type: Optional[WalletType] = None
    purpose: Optional[str] = None
    balance: Optional[Decimal] = None


class WalletResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    type: WalletType
    purpose: str = "operational"
    balance: Decimal
    created_at: datetime

    class Config:
        from_attributes = True

