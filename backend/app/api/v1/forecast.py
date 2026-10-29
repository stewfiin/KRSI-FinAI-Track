import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select, desc
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_session
from app.models.category import Category
from app.models.financial_plan import FinancialPlan
from app.models.fixed_expense import FixedExpense
from app.models.user import User
from app.models.wishlist import Wishlist
from app.schemas.forecast import (
    DailyLedgerResponse,
    FinancialPlanResponse,
    FinancialPlanUpdate,
    FixedExpenseCreate,
    FixedExpenseResponse,
    FixedExpenseUpdate,
    ForecastSummaryResponse,
    SimulationRequest,
    SimulationResponse,
    WishlistCreate,
    WishlistResponse,
    WishlistUpdate,
)
from app.services.forecast_service import ForecastService

router = APIRouter()


# ==============================================================================
# 1. Ringkasan Prediksi & Daily Runway
# ==============================================================================
@router.get(
    "/summary",
    response_model=ForecastSummaryResponse,
    summary="Ringkasan Prediksi & Runway Finansial Adaptif",
)
async def get_forecast_summary(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await ForecastService.get_forecast_summary(
        session=session,
        user_id=current_user.id,
    )


@router.get(
    "/daily-ledger",
    response_model=DailyLedgerResponse,
    summary="Buku Pengeluaran Harian vs Ideal Sesuai Spreadsheet",
)
async def get_daily_ledger(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await ForecastService.get_daily_ledger(
        session=session,
        user_id=current_user.id,
    )


# ==============================================================================
# 2. Financial Blueprint / Plan Pengguna
# ==============================================================================
@router.get(
    "/plan",
    response_model=FinancialPlanResponse,
    summary="Ambil Blueprint Keuangan Bulanan",
)
async def get_financial_plan(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    plan = await ForecastService.get_or_create_financial_plan(session, current_user.id)
    return plan


@router.put(
    "/plan",
    response_model=FinancialPlanResponse,
    summary="Perbarui Blueprint Keuangan Bulanan",
)
async def update_financial_plan(
    payload: FinancialPlanUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    plan = await ForecastService.get_or_create_financial_plan(session, current_user.id)
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(plan, key, value)

    session.add(plan)
    await session.commit()
    await session.refresh(plan)
    return plan


# ==============================================================================
# 3. Manajemen Tagihan Pasti / Fixed Expenses (Checklist 1-Tap)
# ==============================================================================
@router.get(
    "/fixed-expenses",
    response_model=List[FixedExpenseResponse],
    summary="Daftar Tagihan & Pengeluaran Pasti Bulanan",
)
async def list_fixed_expenses(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    query = select(FixedExpense).where(FixedExpense.user_id == current_user.id).order_by(FixedExpense.created_at)
    res = await session.exec(query)
    items = res.all()

    results = []
    for item in items:
        cat_name = None
        if item.category_id:
            cat = await session.get(Category, item.category_id)
            cat_name = cat.name if cat else None

        results.append(
            FixedExpenseResponse(
                id=item.id,
                user_id=item.user_id,
                name=item.name,
                amount=item.amount,
                category_id=item.category_id,
                category_name=cat_name,
                due_day_of_month=item.due_day_of_month,
                frequency=item.frequency,
                is_paid_this_cycle=item.is_paid_this_cycle,
                last_paid_at=item.last_paid_at,
                created_at=item.created_at,
            )
        )
    return results


@router.post(
    "/fixed-expenses",
    response_model=FixedExpenseResponse,
    summary="Tambah Tagihan Pasti Baru",
)
async def create_fixed_expense(
    payload: FixedExpenseCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    item = FixedExpense(
        user_id=current_user.id,
        name=payload.name,
        amount=payload.amount,
        category_id=payload.category_id,
        due_day_of_month=payload.due_day_of_month,
        frequency=payload.frequency,
        is_paid_this_cycle=payload.is_paid_this_cycle,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)

    cat_name = None
    if item.category_id:
        cat = await session.get(Category, item.category_id)
        cat_name = cat.name if cat else None

    return FixedExpenseResponse(
        id=item.id,
        user_id=item.user_id,
        name=item.name,
        amount=item.amount,
        category_id=item.category_id,
        category_name=cat_name,
        due_day_of_month=item.due_day_of_month,
        frequency=item.frequency,
        is_paid_this_cycle=item.is_paid_this_cycle,
        last_paid_at=item.last_paid_at,
        created_at=item.created_at,
    )


@router.post(
    "/fixed-expenses/{expense_id}/toggle-paid",
    response_model=FixedExpenseResponse,
    summary="1-Tap Checklist Status Lunas Tagihan Pasti",
)
async def toggle_fixed_expense_paid(
    expense_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await ForecastService.toggle_fixed_expense_paid(
        session=session,
        user_id=current_user.id,
        expense_id=expense_id,
    )


@router.delete(
    "/fixed-expenses/{expense_id}",
    summary="Hapus Tagihan Pasti",
)
async def delete_fixed_expense(
    expense_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    item = await session.get(FixedExpense, expense_id)
    if not item or item.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tagihan tidak ditemukan.")
    await session.delete(item)
    await session.commit()
    return {"ok": True}


# ==============================================================================
# 4. Wishlist & Simulasi Belanja Impian
# ==============================================================================
@router.get(
    "/wishlists",
    response_model=List[WishlistResponse],
    summary="Daftar Wishlist Belanja Tabungan",
)
async def list_wishlists(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    query = select(Wishlist).where(Wishlist.user_id == current_user.id).order_by(desc(Wishlist.created_at))
    res = await session.exec(query)
    return res.all()


@router.post(
    "/wishlists",
    response_model=WishlistResponse,
    summary="Tambah Barang Wishlist Baru",
)
async def create_wishlist(
    payload: WishlistCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    item = Wishlist(
        user_id=current_user.id,
        item_name=payload.item_name,
        estimated_price=payload.estimated_price,
        priority=payload.priority,
        target_source=payload.target_source,
        notes=payload.notes,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@router.delete(
    "/wishlists/{wishlist_id}",
    summary="Hapus Barang Wishlist",
)
async def delete_wishlist(
    wishlist_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    item = await session.get(Wishlist, wishlist_id)
    if not item or item.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wishlist tidak ditemukan.")
    await session.delete(item)
    await session.commit()
    return {"ok": True}


# ==============================================================================
# 5. What-If Simulator Endpoint ("Bisa Beli Nggak?")
# ==============================================================================
@router.post(
    "/simulate",
    response_model=SimulationResponse,
    summary="Simulasikan Dampak Pembelian Terhadap Tabungan & Runway",
)
async def simulate_purchase(
    payload: SimulationRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await ForecastService.simulate_purchase(
        session=session,
        user_id=current_user.id,
        req=payload,
    )

