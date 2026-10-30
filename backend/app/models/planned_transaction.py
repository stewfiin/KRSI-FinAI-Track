import uuid
from decimal import Decimal
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Column, Date, DateTime, Numeric
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.user import User


class PlannedTransaction(SQLModel, table=True):
    __tablename__ = "planned_transactions"

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
    wallet_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="wallets.id",
        index=True,
        nullable=True,
        ondelete="SET NULL",
    )
    to_wallet_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="wallets.id",
        index=True,
        nullable=True,
        ondelete="SET NULL",
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
    type: str = Field(default="EXPENSE", max_length=20)  # INCOME, EXPENSE, TRANSFER, SAVINGS
    planned_date: date = Field(
        sa_column=Column(Date, nullable=False, index=True),
    )
    is_completed: bool = Field(default=False, nullable=False)
    notes: Optional[str] = Field(default=None, max_length=255)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    # Relasi
    user: "User" = Relationship(back_populates="planned_transactions")

