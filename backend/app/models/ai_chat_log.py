import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional
from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

from app.models.enums import ChatPlatform, ChatRole

if TYPE_CHECKING:
    from app.models.user import User


class AIChatLog(SQLModel, table=True):
    __tablename__ = "ai_chat_logs"

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
    platform: ChatPlatform = Field(default=ChatPlatform.WEB, nullable=False)
    role: ChatRole = Field(default=ChatRole.USER, nullable=False)
    message: str = Field(nullable=False)
    extracted_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    # Relasi
    user: "User" = Relationship(back_populates="ai_chat_logs")

