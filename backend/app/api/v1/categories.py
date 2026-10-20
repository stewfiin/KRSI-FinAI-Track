import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_session
from app.models.category import Category
from app.models.enums import CategoryType
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate

router = APIRouter()


@router.get("", response_model=List[CategoryResponse], summary="Daftar Kategori")
async def list_categories(
    type: Optional[CategoryType] = Query(None, description="Filter tipe kategori (income / expense)"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Menampilkan kategori milik user dan kategori bawaan sistem (user_id IS NULL)."""
    query = select(Category).where(
        or_(Category.user_id == current_user.id, Category.user_id.is_(None))
    )
    if type:
        query = query.where(Category.type == type)

    query = query.order_by(Category.name)
    result = await session.exec(query)
    return result.all()


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED, summary="Tambah Kategori Kustom")
async def create_category(
    payload: CategoryCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    new_cat = Category(
        user_id=current_user.id,
        name=payload.name.strip(),
        type=payload.type,
        icon=payload.icon,
        color=payload.color,
    )
    session.add(new_cat)
    await session.commit()
    await session.refresh(new_cat)
    return new_cat


@router.put("/{category_id}", response_model=CategoryResponse, summary="Ubah Kategori Kustom")
async def update_category(
    category_id: uuid.UUID,
    payload: CategoryUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    cat = await session.get(Category, category_id)
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kategori tidak ditemukan.")
    if cat.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Kategori sistem atau milik pengguna lain tidak dapat diubah.",
        )

    if payload.name is not None:
        cat.name = payload.name.strip()
    if payload.type is not None:
        cat.type = payload.type
    if payload.icon is not None:
        cat.icon = payload.icon
    if payload.color is not None:
        cat.color = payload.color

    session.add(cat)
    await session.commit()
    await session.refresh(cat)
    return cat


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Hapus Kategori Kustom")
async def delete_category(
    category_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    cat = await session.get(Category, category_id)
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kategori tidak ditemukan.")
    if cat.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Kategori sistem atau milik pengguna lain tidak dapat dihapus.",
        )

    await session.delete(cat)
    await session.commit()
    return None

