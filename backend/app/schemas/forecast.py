import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field


# ==============================================================================
# Income Stream Schemas (Multi-Sumber Pendapatan & Siklus Harian/Mingguan/Bulanan)
# ==============================================================================
class IncomeStreamBase(BaseModel):
    name: str = Field(..., max_length=150, description="Nama sumber pendapatan (cth: Gaji Kantor, Uang Saku Mingguan, Omzet Warung)")
    amount: Decimal = Field(..., gt=0, description="Nominal per siklus penerimaan")
    frequency: str = Field(default="monthly", description="daily, weekly, biweekly, monthly")
    receive_day: Optional[int] = Field(default=None, description="Tanggal (1-31) jika bulanan, atau hari (0=Senin, 6=Minggu) jika mingguan")
    is_active: bool = Field(default=True)


class IncomeStreamCreate(IncomeStreamBase):
    pass


class IncomeStreamUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[Decimal] = None
    frequency: Optional[str] = None
    receive_day: Optional[int] = None
    is_active: Optional[bool] = None


class IncomeStreamResponse(IncomeStreamBase):
    id: uuid.UUID
    user_id: uuid.UUID
    monthly_equivalent: Decimal = Field(default=Decimal("0.00"), description="Estimasi setara bulanan otomatis")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==============================================================================
# Financial Plan Schemas
# ==============================================================================
class FinancialPlanBase(BaseModel):
    monthly_income: Decimal = Field(default=Decimal("2600000.00"), description="Pendapatan bulanan")
    daily_living_budget: Decimal = Field(default=Decimal("45000.00"), description="Patokan jatah makan/belanja harian normal")
    monthly_savings_target: Decimal = Field(default=Decimal("695000.00"), description="Target tabungan bulanan")
    cycle_start_day: int = Field(default=1, ge=1, le=31, description="Tanggal awal siklus/gajian")
    weekly_allowance: Optional[Decimal] = Field(default=None, description="Uang saku mingguan jika mode mingguan aktif")
    is_active: bool = Field(default=True)


class FinancialPlanUpdate(BaseModel):
    monthly_income: Optional[Decimal] = None
    daily_living_budget: Optional[Decimal] = None
    monthly_savings_target: Optional[Decimal] = None
    cycle_start_day: Optional[int] = Field(default=None, ge=1, le=31)
    weekly_allowance: Optional[Decimal] = None
    is_active: Optional[bool] = None


class FinancialPlanResponse(FinancialPlanBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==============================================================================
# Fixed Expense Schemas (Pengeluaran Pasti)
# ==============================================================================
class FixedExpenseBase(BaseModel):
    name: str = Field(..., max_length=150, description="Nama pengeluaran pasti (cth: iCloud, Pulsa, Token)")
    amount: Decimal = Field(..., gt=0, description="Nominal tagihan per siklus")
    category_id: Optional[uuid.UUID] = None
    due_day_of_month: Optional[int] = Field(default=None, ge=1, le=31)
    frequency: str = Field(default="monthly")
    is_paid_this_cycle: bool = Field(default=False)


class FixedExpenseCreate(FixedExpenseBase):
    pass


class FixedExpenseUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[Decimal] = None
    category_id: Optional[uuid.UUID] = None
    due_day_of_month: Optional[int] = Field(default=None, ge=1, le=31)
    frequency: Optional[str] = None
    is_paid_this_cycle: Optional[bool] = None


class FixedExpenseResponse(FixedExpenseBase):
    id: uuid.UUID
    user_id: uuid.UUID
    category_name: Optional[str] = None
    last_paid_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ==============================================================================
# Wishlist Schemas (Simulasi Belanja Impian)
# ==============================================================================
class WishlistBase(BaseModel):
    item_name: str = Field(..., max_length=150, description="Nama barang/keinginan")
    estimated_price: Decimal = Field(..., gt=0, description="Estimasi harga")
    priority: str = Field(default="medium", description="low, medium, high")
    target_source: str = Field(default="savings_pool", description="savings_pool atau operational_wallet")
    notes: Optional[str] = None


class WishlistCreate(WishlistBase):
    pass


class WishlistUpdate(BaseModel):
    item_name: Optional[str] = None
    estimated_price: Optional[Decimal] = None
    priority: Optional[str] = None
    target_source: Optional[str] = None
    is_purchased: Optional[bool] = None
    notes: Optional[str] = None


class WishlistResponse(WishlistBase):
    id: uuid.UUID
    user_id: uuid.UUID
    is_purchased: bool
    purchased_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ==============================================================================
# What-If Simulator Schemas
# ==============================================================================
class SimulationRequest(BaseModel):
    item_name: str = Field(..., description="Nama barang yang ingin dibeli")
    amount: Decimal = Field(..., gt=0, description="Harga barang")
    source: str = Field(default="savings_pool", description="savings_pool atau operational_wallet")


class SimulationResponse(BaseModel):
    item_name: str
    amount: Decimal
    source: str
    is_affordable: bool
    verdict: str  # "safe" | "warning" | "danger"
    headline: str
    explanation: str
    current_savings: Decimal
    projected_savings_after: Decimal
    current_daily_ideal: Decimal
    projected_daily_ideal_after: Decimal


# ==============================================================================
# Daily Ledger Schemas (Sesuai Spreadsheet 1 Tabel Kanan)
# ==============================================================================
class DailyLedgerItem(BaseModel):
    date: date
    day_name: str
    total_spent: Decimal
    ideal_spending: Decimal
    daily_variance: Decimal  # ideal - spent (Positif = Surplus, Negatif = Defisit)
    status: str  # "surplus" | "deficit" | "neutral"
    scheduled_income: Optional[Decimal] = None
    scheduled_income_names: Optional[List[str]] = None


class DailyLedgerResponse(BaseModel):
    cycle_start_date: date
    cycle_end_date: date
    items: List[DailyLedgerItem]
    total_spent_cycle: Decimal
    total_ideal_cycle: Decimal
    net_variance: Decimal


# ==============================================================================
# Forecast Summary Response (Output Utama Halaman Proyeksi)
# ==============================================================================
class CycleInfo(BaseModel):
    cycle_start_date: date
    cycle_end_date: date
    days_elapsed: int
    days_remaining: int
    total_days: int


class TodayMetrics(BaseModel):
    date: date
    ideal_spending_today: Decimal
    actual_spent_today: Decimal
    daily_variance: Decimal
    status: str  # "surplus" | "warning" | "deficit"
    percentage_used: float


class RunwayPrediction(BaseModel):
    operational_balance_available: Decimal
    current_burn_rate_daily: Decimal
    predicted_runway_days: float
    runway_exhaustion_date: Optional[date] = None
    is_runway_safe: bool
    status_label: str


class FixedObligationsSummary(BaseModel):
    total_monthly_fixed: Decimal
    unpaid_fixed_buffer: Decimal
    paid_fixed: Decimal
    items: List[FixedExpenseResponse]


class EndOfMonthForecast(BaseModel):
    monthly_income: Decimal
    target_savings: Decimal
    projected_end_savings: Decimal
    savings_delta: Decimal  # projected - target
    forecast_status: str  # "on_track" | "warning" | "deficit"
    advice: str


class ForecastSummaryResponse(BaseModel):
    cycle_info: CycleInfo
    today_metrics: TodayMetrics
    runway_prediction: RunwayPrediction
    fixed_obligations: FixedObligationsSummary
    end_of_month_forecast: EndOfMonthForecast
    savings_pool_balance: Decimal
    safe_to_spend_total: Decimal
    income_streams: List[IncomeStreamResponse] = []
    total_monthly_income_estimated: Decimal = Decimal("0.00")

