from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel

from app.schemas.transaction import TransactionResponse
from app.schemas.wallet import WalletResponse


class CategoryExpenseBreakdown(BaseModel):
    category_id: str
    category_name: str
    category_color: Optional[str] = None
    category_icon: Optional[str] = None
    total_amount: Decimal
    percentage: float


class DailyCashflow(BaseModel):
    date: str  # Format YYYY-MM-DD
    day_name: str  # Misal: "Sen", "Sel", dst.
    income: Decimal
    expense: Decimal


class BudgetSummaryItem(BaseModel):
    category_id: str
    category_name: str
    category_color: Optional[str] = None
    amount_limit: Decimal
    spent_amount: Decimal
    percentage_used: float
    status: str  # "aman", "waspada", "overbudget"


class DashboardSummaryResponse(BaseModel):
    total_balance: Decimal
    wallets: List[WalletResponse]
    monthly_income: Decimal
    monthly_expense: Decimal
    net_cashflow: Decimal
    category_breakdown: List[CategoryExpenseBreakdown]
    recent_7_days_cashflow: List[DailyCashflow]
    recent_transactions: List[TransactionResponse]
    budget_statuses: List[BudgetSummaryItem]

