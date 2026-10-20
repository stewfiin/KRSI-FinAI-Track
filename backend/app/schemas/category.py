import uuid
from typing import Optional
from pydantic import BaseModel, Field
from app.models.enums import CategoryType


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Nama kategori")
    type: CategoryType = Field(..., description="Tipe kategori: income atau expense")
    icon: Optional[str] = Field(default="tag", max_length=50, description="Ikon kategori (Lucide icon name)")
    color: Optional[str] = Field(default="#6B7280", max_length=30, description="Kode warna hex")


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    type: Optional[CategoryType] = None
    icon: Optional[str] = None
    color: Optional[str] = None


class CategoryResponse(BaseModel):
    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    name: str
    type: CategoryType
    icon: Optional[str] = None
    color: Optional[str] = None

    class Config:
        from_attributes = True

