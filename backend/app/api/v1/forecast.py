import uuid
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select, desc
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_session
from app.models.category import Category
from app.models.financial_plan import FinancialPlan
from app.models.fixed_expense import FixedExpense
from app.models.income_stream import IncomeStream
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
    IncomeStreamCreate,
    IncomeStreamResponse,
    IncomeStreamUpdate,
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


# ==============================================================================
# 6. Income Streams (Multi-Sumber Pendapatan & Siklus Harian/Mingguan/Bulanan)
# ==============================================================================
@router.get(
    "/income-streams",
    response_model=List[IncomeStreamResponse],
    summary="Daftar Sumber Pendapatan Pengguna",
)
async def list_income_streams(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    plan = await ForecastService.get_or_create_financial_plan(session, current_user.id)
    start_date, end_date = ForecastService.get_cycle_dates(plan.cycle_start_day)
    total_cycle_days = (end_date - start_date).days + 1

    query = select(IncomeStream).where(IncomeStream.user_id == current_user.id).order_by(IncomeStream.created_at)
    res = (await session.exec(query)).all()

    return [
        IncomeStreamResponse(
            id=s.id,
            user_id=s.user_id,
            name=s.name,
            amount=s.amount,
            frequency=s.frequency,
            receive_day=s.receive_day,
            is_active=s.is_active,
            monthly_equivalent=ForecastService.calculate_monthly_equivalent(s, total_cycle_days),
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in res
    ]


@router.post(
    "/income-streams",
    response_model=IncomeStreamResponse,
    summary="Tambah Sumber Pendapatan Baru",
)
async def create_income_stream(
    payload: IncomeStreamCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    item = IncomeStream(
        user_id=current_user.id,
        name=payload.name,
        amount=payload.amount,
        frequency=payload.frequency,
        receive_day=payload.receive_day,
        is_active=payload.is_active,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)

    # Sinkronisasi ke blueprint
    await ForecastService.sync_financial_plan_income(session, current_user.id)

    plan = await ForecastService.get_or_create_financial_plan(session, current_user.id)
    start_date, end_date = ForecastService.get_cycle_dates(plan.cycle_start_day)
    total_cycle_days = (end_date - start_date).days + 1

    return IncomeStreamResponse(
        id=item.id,
        user_id=item.user_id,
        name=item.name,
        amount=item.amount,
        frequency=item.frequency,
        receive_day=item.receive_day,
        is_active=item.is_active,
        monthly_equivalent=ForecastService.calculate_monthly_equivalent(item, total_cycle_days),
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.put(
    "/income-streams/{stream_id}",
    response_model=IncomeStreamResponse,
    summary="Perbarui Sumber Pendapatan",
)
async def update_income_stream(
    stream_id: uuid.UUID,
    payload: IncomeStreamUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    item = await session.get(IncomeStream, stream_id)
    if not item or item.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sumber pendapatan tidak ditemukan.")

    if payload.name is not None:
        item.name = payload.name
    if payload.amount is not None:
        item.amount = payload.amount
    if payload.frequency is not None:
        item.frequency = payload.frequency
    if payload.receive_day is not None:
        item.receive_day = payload.receive_day
    if payload.is_active is not None:
        item.is_active = payload.is_active

    item.updated_at = datetime.now(timezone.utc)
    session.add(item)
    await session.commit()
    await session.refresh(item)

    # Sinkronisasi ke blueprint
    await ForecastService.sync_financial_plan_income(session, current_user.id)

    plan = await ForecastService.get_or_create_financial_plan(session, current_user.id)
    start_date, end_date = ForecastService.get_cycle_dates(plan.cycle_start_day)
    total_cycle_days = (end_date - start_date).days + 1

    return IncomeStreamResponse(
        id=item.id,
        user_id=item.user_id,
        name=item.name,
        amount=item.amount,
        frequency=item.frequency,
        receive_day=item.receive_day,
        is_active=item.is_active,
        monthly_equivalent=ForecastService.calculate_monthly_equivalent(item, total_cycle_days),
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.delete(
    "/income-streams/{stream_id}",
    summary="Hapus Sumber Pendapatan",
)
async def delete_income_stream(
    stream_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    item = await session.get(IncomeStream, stream_id)
    if not item or item.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sumber pendapatan tidak ditemukan.")

    await session.delete(item)
    await session.commit()

    # Sinkronisasi ulang blueprint
    await ForecastService.sync_financial_plan_income(session, current_user.id)
    return {"ok": True}

