import uuid
from decimal import Decimal
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List
from sqlalchemy import Column, DateTime, Numeric
from sqlmodel import Field, Relationship, SQLModel

from app.models.enums import WalletType

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.transaction import Transaction


class Wallet(SQLModel, table=True):
    __tablename__ = "wallets"

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
    name: str = Field(nullable=False, max_length=100)
    type: WalletType = Field(default=WalletType.CASH, nullable=False)
    purpose: str = Field(default="operational", max_length=30)  # operational | savings | subscription
    balance: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=Column(Numeric(15, 2), default=0.00, nullable=False),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    # Relasi
    user: "User" = Relationship(back_populates="wallets")
    transactions: List["Transaction"] = Relationship(
        back_populates="wallet",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

