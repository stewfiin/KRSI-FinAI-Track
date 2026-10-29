import uuid
from decimal import Decimal
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Column, DateTime, Numeric
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.category import Category


class FixedExpense(SQLModel, table=True):
    __tablename__ = "fixed_expenses"

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
    category_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="categories.id",
        index=True,
        nullable=True,
        ondelete="SET NULL",
    )
    name: str = Field(nullable=False, max_length=150)
    amount: Decimal = Field(
        sa_column=Column(Numeric(15, 2), nullable=False),
    )
    due_day_of_month: Optional[int] = Field(default=None, ge=1, le=31)
    frequency: str = Field(default="monthly", max_length=20)
    is_paid_this_cycle: bool = Field(default=False, nullable=False)
    last_paid_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    # Relasi
    user: "User" = Relationship(back_populates="fixed_expenses")
    category: Optional["Category"] = Relationship()

