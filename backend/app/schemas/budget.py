import uuid
from decimal import Decimal
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class BudgetCreate(BaseModel):
    category_id: uuid.UUID = Field(..., description="ID kategori pengeluaran")
    amount_limit: Decimal = Field(..., gt=0, description="Batas anggaran bulanan (harus > 0)")
    month: int = Field(..., ge=1, le=12, description="Bulan (1-12)")
    year: int = Field(..., ge=2020, le=2100, description="Tahun")
    is_ai_generated: bool = Field(default=False, description="Apakah dibuat oleh rekomendasi AI")


class BudgetUpdate(BaseModel):
    amount_limit: Optional[Decimal] = Field(None, gt=0)
    month: Optional[int] = Field(None, ge=1, le=12)
    year: Optional[int] = Field(None, ge=2020, le=2100)


class BudgetResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    category_id: uuid.UUID
    amount_limit: Decimal
    month: int
    year: int
    is_ai_generated: bool
    created_at: datetime
    # Atribut analitik pemakaian anggaran
    category_name: Optional[str] = None
    category_icon: Optional[str] = None
    category_color: Optional[str] = None
    spent_amount: Decimal = Decimal("0.00")
    remaining_amount: Decimal = Decimal("0.00")
    percentage_used: float = 0.0
    status: str = "aman"  # "aman" (<80%), "waspada" (80-99%), "overbudget" (>=100%)

    class Config:
        from_attributes = True


class BudgetAlert(BaseModel):
    level: str  # "warning" atau "danger"
    category_name: str
    amount_limit: Decimal
    spent_amount: Decimal
    percentage_used: float
    message: str

