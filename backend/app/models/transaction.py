import uuid
from decimal import Decimal
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Column, DateTime, Numeric
from sqlmodel import Field, Relationship, SQLModel

from app.models.enums import TransactionSource, TransactionType

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.wallet import Wallet
    from app.models.category import Category


class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"

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
    wallet_id: uuid.UUID = Field(
        foreign_key="wallets.id",
        index=True,
        nullable=False,
        ondelete="CASCADE",
    )
    category_id: uuid.UUID = Field(
        foreign_key="categories.id",
        index=True,
        nullable=False,
        ondelete="CASCADE",
    )
    amount: Decimal = Field(
        sa_column=Column(Numeric(15, 2), nullable=False),
    )
    type: TransactionType = Field(nullable=False)
    description: Optional[str] = Field(default=None)
    transaction_date: date = Field(nullable=False, index=True)
    source: TransactionSource = Field(
        default=TransactionSource.MANUAL_WEB,
        nullable=False,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    # Relasi
    user: "User" = Relationship(back_populates="transactions")
    wallet: "Wallet" = Relationship(back_populates="transactions")
    category: "Category" = Relationship(back_populates="transactions")

