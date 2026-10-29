import uuid
from decimal import Decimal
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Column, DateTime, Numeric, String
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.user import User


class Wishlist(SQLModel, table=True):
    __tablename__ = "wishlists"

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
    item_name: str = Field(nullable=False, max_length=150)
    estimated_price: Decimal = Field(
        sa_column=Column(Numeric(15, 2), nullable=False),
    )
    priority: str = Field(default="medium", max_length=20)
    target_source: str = Field(default="savings_pool", max_length=30)
    is_purchased: bool = Field(default=False, nullable=False)
    purchased_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    notes: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    # Relasi
    user: "User" = Relationship(back_populates="wishlists")

