import uuid
from decimal import Decimal
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import Column, DateTime, Numeric
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.category import Category


class Budget(SQLModel, table=True):
    __tablename__ = "budgets"

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
    category_id: uuid.UUID = Field(
        foreign_key="categories.id",
        index=True,
        nullable=False,
        ondelete="CASCADE",
    )
    amount_limit: Decimal = Field(
        sa_column=Column(Numeric(15, 2), nullable=False),
    )
    month: int = Field(nullable=False, ge=1, le=12)
    year: int = Field(nullable=False)
    is_ai_generated: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    # Relasi
    user: "User" = Relationship(back_populates="budgets")
    category: "Category" = Relationship(back_populates="budgets")

