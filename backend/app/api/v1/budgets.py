import uuid
from datetime import date
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import extract, func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_session
from app.models.budget import Budget
from app.models.category import Category
from app.models.enums import TransactionType
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.budget import BudgetCreate, BudgetResponse, BudgetUpdate

router = APIRouter()


@router.get("", response_model=List[BudgetResponse], summary="Daftar Anggaran Bulanan")
async def list_budgets(
    month: Optional[int] = Query(None, ge=1, le=12, description="Bulan (default: bulan berjalan)"),
    year: Optional[int] = Query(None, ge=2020, le=2100, description="Tahun (default: tahun berjalan)"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    target_month = month or date.today().month
    target_year = year or date.today().year

    query = (
        select(Budget, Category.name.label("category_name"), Category.icon.label("category_icon"), Category.color.label("category_color"))
        .join(Category, Budget.category_id == Category.id)
        .where(
            Budget.user_id == current_user.id,
            Budget.month == target_month,
            Budget.year == target_year,
        )
    )
    results = (await session.exec(query)).all()

    items: List[BudgetResponse] = []
    for b_obj, c_name, c_icon, c_color in results:
        # Hitung realisasi pengeluaran pada kategori ini di bulan target
        spent_query = select(func.coalesce(func.sum(Transaction.amount), Decimal("0.00"))).where(
            Transaction.user_id == current_user.id,
            Transaction.category_id == b_obj.category_id,
            Transaction.type == TransactionType.EXPENSE,
            extract("month", Transaction.transaction_date) == target_month,
            extract("year", Transaction.transaction_date) == target_year,
        )
        spent_amount: Decimal = (await session.exec(spent_query)).one()

        pct = float((spent_amount / b_obj.amount_limit) * Decimal("100.0")) if b_obj.amount_limit > 0 else 0.0
        remaining = max(b_obj.amount_limit - spent_amount, Decimal("0.00"))

        if pct >= 100.0:
            b_status = "overbudget"
        elif pct >= 80.0:
            b_status = "waspada"
        else:
            b_status = "aman"

        items.append(
            BudgetResponse(
                id=b_obj.id,
                user_id=b_obj.user_id,
                category_id=b_obj.category_id,
                amount_limit=b_obj.amount_limit,
                month=b_obj.month,
                year=b_obj.year,
                is_ai_generated=b_obj.is_ai_generated,
                created_at=b_obj.created_at,
                category_name=c_name,
                category_icon=c_icon,
                category_color=c_color,
                spent_amount=spent_amount,
                remaining_amount=remaining,
                percentage_used=round(pct, 1),
                status=b_status,
            )
        )
    return items


@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED, summary="Pasang Batas Anggaran Baru")
async def create_budget(
    payload: BudgetCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    # Validasi kategori
    category = await session.get(Category, payload.category_id)
    if not category or (category.user_id is not None and category.user_id != current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kategori tidak ditemukan.")

    # Cek duplikasi anggaran untuk kategori dan periode yang sama
    existing_query = select(Budget).where(
        Budget.user_id == current_user.id,
        Budget.category_id == payload.category_id,
        Budget.month == payload.month,
        Budget.year == payload.year,
    )
    existing = (await session.exec(existing_query)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batas anggaran untuk kategori '{category.name}' pada periode {payload.month}/{payload.year} sudah ada. Gunakan PUT untuk mengubah.",
        )

    new_budget = Budget(
        user_id=current_user.id,
        category_id=payload.category_id,
        amount_limit=payload.amount_limit,
        month=payload.month,
        year=payload.year,
        is_ai_generated=payload.is_ai_generated,
    )
    session.add(new_budget)
    await session.commit()
    await session.refresh(new_budget)

    # Hitung pengeluaran saat ini
    spent_query = select(func.coalesce(func.sum(Transaction.amount), Decimal("0.00"))).where(
        Transaction.user_id == current_user.id,
        Transaction.category_id == new_budget.category_id,
        Transaction.type == TransactionType.EXPENSE,
        extract("month", Transaction.transaction_date) == new_budget.month,
        extract("year", Transaction.transaction_date) == new_budget.year,
    )
    spent_amount: Decimal = (await session.exec(spent_query)).one()
    pct = float((spent_amount / new_budget.amount_limit) * Decimal("100.0")) if new_budget.amount_limit > 0 else 0.0

    return BudgetResponse(
        id=new_budget.id,
        user_id=new_budget.user_id,
        category_id=new_budget.category_id,
        amount_limit=new_budget.amount_limit,
        month=new_budget.month,
        year=new_budget.year,
        is_ai_generated=new_budget.is_ai_generated,
        created_at=new_budget.created_at,
        category_name=category.name,
        category_icon=category.icon,
        category_color=category.color,
        spent_amount=spent_amount,
        remaining_amount=max(new_budget.amount_limit - spent_amount, Decimal("0.00")),
        percentage_used=round(pct, 1),
        status="overbudget" if pct >= 100.0 else ("waspada" if pct >= 80.0 else "aman"),
    )


@router.put("/{budget_id}", response_model=BudgetResponse, summary="Ubah Batas Anggaran")
async def update_budget(
    budget_id: uuid.UUID,
    payload: BudgetUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    budget = await session.get(Budget, budget_id)
    if not budget or budget.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anggaran tidak ditemukan.")

    if payload.amount_limit is not None:
        budget.amount_limit = payload.amount_limit
    if payload.month is not None:
        budget.month = payload.month
    if payload.year is not None:
        budget.year = payload.year

    session.add(budget)
    await session.commit()
    await session.refresh(budget)

    category = await session.get(Category, budget.category_id)
    spent_query = select(func.coalesce(func.sum(Transaction.amount), Decimal("0.00"))).where(
        Transaction.user_id == current_user.id,
        Transaction.category_id == budget.category_id,
        Transaction.type == TransactionType.EXPENSE,
        extract("month", Transaction.transaction_date) == budget.month,
        extract("year", Transaction.transaction_date) == budget.year,
    )
    spent_amount: Decimal = (await session.exec(spent_query)).one()
    pct = float((spent_amount / budget.amount_limit) * Decimal("100.0")) if budget.amount_limit > 0 else 0.0

    return BudgetResponse(
        id=budget.id,
        user_id=budget.user_id,
        category_id=budget.category_id,
        amount_limit=budget.amount_limit,
        month=budget.month,
        year=budget.year,
        is_ai_generated=budget.is_ai_generated,
        created_at=budget.created_at,
        category_name=category.name if category else None,
        category_icon=category.icon if category else None,
        category_color=category.color if category else None,
        spent_amount=spent_amount,
        remaining_amount=max(budget.amount_limit - spent_amount, Decimal("0.00")),
        percentage_used=round(pct, 1),
        status="overbudget" if pct >= 100.0 else ("waspada" if pct >= 80.0 else "aman"),
    )


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Hapus Batas Anggaran")
async def delete_budget(
    budget_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    budget = await session.get(Budget, budget_id)
    if not budget or budget.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anggaran tidak ditemukan.")

    await session.delete(budget)
    await session.commit()
    return None

