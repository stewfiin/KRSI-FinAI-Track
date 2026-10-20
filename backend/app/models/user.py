import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import BigInteger, Column, DateTime
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.wallet import Wallet
    from app.models.category import Category
    from app.models.transaction import Transaction
    from app.models.budget import Budget
    from app.models.ai_chat_log import AIChatLog


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    name: str = Field(nullable=False, max_length=150)
    email: str = Field(unique=True, index=True, nullable=False, max_length=255)
    password_hash: str = Field(nullable=False)
    telegram_chat_id: Optional[int] = Field(
        default=None,
        sa_column=Column(BigInteger, unique=True, nullable=True, index=True),
    )
    default_currency: str = Field(default="IDR", max_length=10)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    # Relasi
    wallets: List["Wallet"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    categories: List["Category"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    transactions: List["Transaction"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    budgets: List["Budget"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    ai_chat_logs: List["AIChatLog"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

