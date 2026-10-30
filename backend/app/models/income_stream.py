import uuid
from decimal import Decimal
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Column, DateTime, Numeric
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.user import User


class IncomeStream(SQLModel, table=True):
    __tablename__ = "income_streams"

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
    name: str = Field(nullable=False, max_length=150)
    amount: Decimal = Field(
        sa_column=Column(Numeric(15, 2), nullable=False),
    )
    frequency: str = Field(default="monthly", max_length=20)  # daily, weekly, biweekly, monthly
    receive_day: Optional[int] = Field(default=None)  # Tanggal (1-31) jika bulanan, atau hari (0=Senin, 6=Minggu) jika mingguan
    wallet_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="wallets.id",
        index=True,
        nullable=True,
        ondelete="SET NULL",
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
    user: "User" = Relationship(back_populates="income_streams")

