import uuid
from decimal import Decimal
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Column, DateTime, Numeric
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.user import User


class FinancialPlan(SQLModel, table=True):
    __tablename__ = "financial_plans"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    user_id: uuid.UUID = Field(
        foreign_key="users.id",
        index=True,
        nullable=False,
        ondelete="CASCADE",
    )
    monthly_income: Decimal = Field(
        default=Decimal("2600000.00"),
        sa_column=Column(Numeric(15, 2), nullable=False),
    )
    daily_living_budget: Decimal = Field(
        default=Decimal("45000.00"),
        sa_column=Column(Numeric(15, 2), nullable=False),
    )
    monthly_savings_target: Decimal = Field(
        default=Decimal("695000.00"),
        sa_column=Column(Numeric(15, 2), nullable=False),
    )
    cycle_start_day: int = Field(default=1, nullable=False, ge=1, le=31)
    weekly_allowance: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(Numeric(15, 2), nullable=True),
    )
    is_active: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    # Relasi
    user: "User" = Relationship(back_populates="financial_plans")

