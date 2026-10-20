import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlmodel import Field, Relationship, SQLModel

from app.models.enums import CategoryType

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.transaction import Transaction
    from app.models.budget import Budget


class Category(SQLModel, table=True):
    __tablename__ = "categories"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    user_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="users.id",
        index=True,
        nullable=True,
        ondelete="CASCADE",
    )
    name: str = Field(nullable=False, max_length=100)
    type: CategoryType = Field(default=CategoryType.EXPENSE, nullable=False)
    icon: Optional[str] = Field(default=None, max_length=50)
    color: Optional[str] = Field(default=None, max_length=30)

    # Relasi
    user: Optional["User"] = Relationship(back_populates="categories")
    transactions: List["Transaction"] = Relationship(
        back_populates="category",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    budgets: List["Budget"] = Relationship(
        back_populates="category",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

