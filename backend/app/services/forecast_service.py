import uuid
import calendar
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import extract, func
from sqlmodel import and_, desc, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.category import Category
from app.models.enums import TransactionType
from app.models.financial_plan import FinancialPlan
from app.models.fixed_expense import FixedExpense
from app.models.income_stream import IncomeStream
from app.models.planned_transaction import PlannedTransaction
from app.models.transaction import Transaction
from app.models.wallet import Wallet
from app.models.wishlist import Wishlist
from app.schemas.forecast import (
    CycleInfo,
    DailyLedgerItem,
    DailyLedgerResponse,
    EndOfMonthForecast,
    FixedExpenseCreate,
    FixedExpenseResponse,
    FixedExpenseUpdate,
    FixedObligationsSummary,
    ForecastSummaryResponse,
    IncomeStreamCreate,
    IncomeStreamResponse,
    IncomeStreamUpdate,
    PlannedTransactionCreate,
    PlannedTransactionResponse,
    PlannedTransactionUpdate,
    ProjectedDayEvent,
    ProjectedDayItem,
    RangeProjectionRequest,
    RangeProjectionResponse,
    RunwayPrediction,
    SimulationRequest,
    SimulationResponse,
    TodayMetrics,
    WishlistCreate,
    WishlistResponse,
    WishlistUpdate,
)


class ForecastService:
    @staticmethod
    async def get_or_create_financial_plan(
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> FinancialPlan:
        """Mengambil blueprint rencana keuangan user atau membuat default blueprint jika belum ada."""
        query = (
            select(FinancialPlan)
            .where(FinancialPlan.user_id == user_id, FinancialPlan.is_active == True)
            .order_by(desc(FinancialPlan.created_at))
        )
        res = await session.exec(query)
        plan = res.first()

        if not plan:
            # Default blueprint sesuai struktur dasar finansial sehat (merujuk ke Spreadsheet Pengguna: Rp2.6jt)
            plan = FinancialPlan(
                user_id=user_id,
                monthly_income=Decimal("2600000.00"),
                daily_living_budget=Decimal("45000.00"),
                monthly_savings_target=Decimal("695000.00"),
                cycle_start_day=1,
                weekly_allowance=Decimal("415258.00"),
                is_active=True,
            )
            session.add(plan)
            await session.commit()
            await session.refresh(plan)

        return plan

    @staticmethod
    def get_cycle_dates(cycle_start_day: int, target_date: Optional[date] = None) -> Tuple[date, date]:
        """Menghitung rentang tanggal mulai dan akhir siklus berdasarkan cycle_start_day."""
        t = target_date or date.today()
        year = t.year
        month = t.month

        if cycle_start_day <= 1:
            # Siklus standar tanggal 1 sampai akhir bulan
            start_date = date(year, month, 1)
            _, last_day = calendar.monthrange(year, month)
            end_date = date(year, month, last_day)
        else:
            # Siklus kustom (misal gajian tanggal 25)
            if t.day >= cycle_start_day:
                start_date = date(year, month, cycle_start_day)
                # Next month
                if month == 12:
                    end_month = 1
                    end_year = year + 1
                else:
                    end_month = month + 1
                    end_year = year
                end_date = date(end_year, end_month, cycle_start_day) - timedelta(days=1)
            else:
                # Previous month start
                if month == 1:
                    prev_month = 12
                    prev_year = year - 1
                else:
                    prev_month = month - 1
                    prev_year = year
                start_date = date(prev_year, prev_month, cycle_start_day)
                end_date = date(year, month, cycle_start_day) - timedelta(days=1)

        return start_date, end_date

    @staticmethod
    def calculate_monthly_equivalent(stream: IncomeStream, total_cycle_days: int = 30) -> Decimal:
        """Konversi nominal penerimaan berbagai frekuensi ke ekuivalen 1 siklus bulanan penuh."""
        freq = (stream.frequency or "monthly").lower()
        amt = stream.amount or Decimal("0.00")
        days = Decimal(str(max(1, total_cycle_days)))

        if freq == "daily":
            return (amt * days).quantize(Decimal("1.00"))
        elif freq == "weekly":
            # Rata-rata minggu dalam siklus: total_hari / 7
            return (amt * (days / Decimal("7.0"))).quantize(Decimal("1.00"))
        elif freq == "biweekly":
            # Rata-rata 2-mingguan: total_hari / 14
            return (amt * (days / Decimal("14.0"))).quantize(Decimal("1.00"))
        else:
            # monthly
            return amt.quantize(Decimal("1.00"))

    @staticmethod
    def is_income_due_on_date(stream: IncomeStream, target_date: date, cycle_start_day: int = 1) -> bool:
        """Menentukan apakah sumber pendapatan cair pada tanggal target tertentu."""
        freq = (stream.frequency or "monthly").lower()
        if freq == "daily":
            return True
        elif freq == "weekly":
            rec_day = stream.receive_day if stream.receive_day is not None else 0  # 0=Senin, 6=Minggu
            return target_date.weekday() == rec_day
        elif freq == "biweekly":
            anchor = stream.created_at.date() if stream.created_at else date(2026, 1, 1)
            diff = (target_date - anchor).days
            return diff >= 0 and (diff % 14 == 0)
        elif freq == "monthly":
            rec_day = stream.receive_day if stream.receive_day is not None else cycle_start_day
            _, last_day = calendar.monthrange(target_date.year, target_date.month)
            return target_date.day == min(rec_day, last_day)
        return False

    @staticmethod
    def is_fixed_expense_due_on_date(expense: FixedExpense, target_date: date) -> bool:
        """Menentukan apakah tagihan bulanan atau siklus biaya berkala jatuh tempo pada tanggal target tertentu."""
        freq = (expense.frequency or "monthly").lower()
        if freq == "daily":
            return True
        elif freq == "monthly":
            due_day = expense.due_day_of_month or 1
            _, last_day = calendar.monthrange(target_date.year, target_date.month)
            return target_date.day == min(due_day, last_day)
        elif freq == "weekly":
            day_idx = expense.interval_value if expense.interval_value is not None else 5  # default Sabtu (5)
            return target_date.weekday() == day_idx
        elif freq == "biweekly":
            anchor = expense.anchor_date.date() if expense.anchor_date else (
                expense.created_at.date() if expense.created_at else date(2026, 1, 1)
            )
            diff = (target_date - anchor).days
            return diff >= 0 and (diff % 14 == 0)
        elif freq == "every_n_days":
            interval = max(1, expense.interval_value or 1)
            anchor = expense.anchor_date.date() if expense.anchor_date else (
                expense.created_at.date() if expense.created_at else target_date
            )
            diff = (target_date - anchor).days
            return diff >= 0 and (diff % interval == 0)
        return False

    @staticmethod
    async def get_forecast_summary(
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> ForecastSummaryResponse:
        """
        Engine Prediksi Utama: Menghitung seluruh metrik proyeksi dan runway finansial.
        - Dynamic Daily Runway (Batas Belanja Ideal Hari Ini)
        - Cadangan Tagihan Pasti (Fixed Buffer) & Cadangan Siklus Berkala (Cyclical Buffer)
        - Estimasi Daya Tahan Uang (Runway Days)
        - Proyeksi Tabungan Akhir Bulan
        """
        today = date.today()
        plan = await ForecastService.get_or_create_financial_plan(session, user_id)
        start_date, end_date = ForecastService.get_cycle_dates(plan.cycle_start_day, today)

        total_cycle_days = (end_date - start_date).days + 1
        days_elapsed = (today - start_date).days
        days_remaining = max(1, (end_date - today).days + 1)  # Termasuk hari ini

        # 1. Dompet Pengguna (Operasional vs Tabungan vs Tagihan)
        wallets_res = await session.exec(select(Wallet).where(Wallet.user_id == user_id))
        wallets = wallets_res.all()
        wallet_map = {w.id: w for w in wallets}

        savings_balance = Decimal("0.00")
        subscription_balance = Decimal("0.00")
        operational_balance = Decimal("0.00")

        for w in wallets:
            w_purpose = getattr(w, "purpose", None)
            if w_purpose in ("savings", "subscription", "operational"):
                if w_purpose == "savings":
                    savings_balance += w.balance
                elif w_purpose == "subscription":
                    subscription_balance += w.balance
                else:
                    operational_balance += w.balance
            else:
                w_name = (w.name or "").lower()
                if "saving" in w_name or "anniv" in w_name or "tabung" in w_name:
                    savings_balance += w.balance
                elif "subscrip" in w_name or "tagihan" in w_name:
                    subscription_balance += w.balance
                else:
                    operational_balance += w.balance

        # 2. Multi-Stream Income: Ambil semua sumber pendapatan aktif
        income_res = await session.exec(
            select(IncomeStream).where(IncomeStream.user_id == user_id, IncomeStream.is_active == True)
        )
        active_streams = income_res.all()

        stream_responses = []
        total_stream_equivalent = Decimal("0.00")
        for s in active_streams:
            equiv = ForecastService.calculate_monthly_equivalent(s, total_cycle_days)
            total_stream_equivalent += equiv
            w_obj = wallet_map.get(s.wallet_id) if s.wallet_id else None
            stream_responses.append(
                IncomeStreamResponse(
                    id=s.id,
                    user_id=s.user_id,
                    name=s.name,
                    amount=s.amount,
                    frequency=s.frequency,
                    receive_day=s.receive_day,
                    wallet_id=s.wallet_id,
                    wallet_name=w_obj.name if w_obj else None,
                    is_active=s.is_active,
                    monthly_equivalent=equiv,
                    created_at=s.created_at,
                    updated_at=s.updated_at,
                )
            )

        # Pendapatan efektif: Jika user mendefinisikan income streams, gunakan total setara bulanan; jika tidak, gunakan blueprint lama
        effective_monthly_income = total_stream_equivalent if total_stream_equivalent > 0 else plan.monthly_income

        # 3. Tagihan Pasti Bulanan & Siklus Biaya Hidup Berkala (Cyclical Expenses)
        fixed_res = await session.exec(select(FixedExpense).where(FixedExpense.user_id == user_id))
        fixed_items = fixed_res.all()

        monthly_bills = [f for f in fixed_items if (f.frequency or "monthly").lower() == "monthly"]
        cyclical_expenses = [
            f for f in fixed_items if (f.frequency or "monthly").lower() in ("weekly", "biweekly", "every_n_days")
        ]

        total_monthly_fixed = sum((f.amount for f in fixed_items), Decimal("0.00"))
        unpaid_monthly_items = [f for f in monthly_bills if not f.is_paid_this_cycle]
        paid_fixed = total_monthly_fixed - sum((f.amount for f in unpaid_monthly_items), Decimal("0.00"))

        # Pisahkan buffer tagihan bulanan
        unpaid_sub_buffer = Decimal("0.00")
        unpaid_op_buffer = Decimal("0.00")

        for f in unpaid_monthly_items:
            assigned_wallet = wallet_map.get(f.wallet_id) if f.wallet_id else None
            is_sub_wallet = False
            if assigned_wallet:
                p = getattr(assigned_wallet, "purpose", None)
                if p:
                    is_sub_wallet = (p == "subscription")
                else:
                    w_name = (assigned_wallet.name or "").lower()
                    is_sub_wallet = ("subscrip" in w_name or "tagihan" in w_name)

            if is_sub_wallet or (f.wallet_id is None and subscription_balance > 0):
                unpaid_sub_buffer += f.amount
            else:
                unpaid_op_buffer += f.amount

        # Hitung estimasi pengeluaran siklus berkala untuk sisa hari dalam siklus (dari today s/d end_date)
        cyclical_op_buffer = Decimal("0.00")
        cyclical_sub_buffer = Decimal("0.00")

        curr_d = today
        while curr_d <= end_date:
            for ce in cyclical_expenses:
                if ForecastService.is_fixed_expense_due_on_date(ce, curr_d):
                    assigned_wallet = wallet_map.get(ce.wallet_id) if ce.wallet_id else None
                    is_sub = False
                    if assigned_wallet:
                        p = getattr(assigned_wallet, "purpose", None)
                        is_sub = (p == "subscription")
                    if is_sub or (ce.wallet_id is None and subscription_balance > 0):
                        cyclical_sub_buffer += ce.amount
                    else:
                        cyclical_op_buffer += ce.amount
            curr_d += timedelta(days=1)

        # Jika saldo subscription kurang untuk total tagihan & siklusnya, kekurangan meluber ke operasional
        total_sub_obligations = unpaid_sub_buffer + cyclical_sub_buffer
        sub_deficit = max(Decimal("0.00"), total_sub_obligations - subscription_balance)
        effective_op_unpaid_buffer = unpaid_op_buffer + cyclical_op_buffer + sub_deficit
        unpaid_fixed_buffer = unpaid_sub_buffer + unpaid_op_buffer + cyclical_sub_buffer + cyclical_op_buffer

        # Saldo Operasional Bebas (Safe-to-Spend Murni setelah mencadangkan tagihan bulanan + siklus berkala sisa bulan)
        safe_to_spend_total = max(Decimal("0.00"), operational_balance - effective_op_unpaid_buffer)

        # 4. Transaksi Pengeluaran Siklus Berjalan
        tx_query = select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.type == TransactionType.EXPENSE,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
        )
        tx_rows = (await session.exec(tx_query)).all()

        spent_today = sum((tx.amount for tx in tx_rows if tx.transaction_date == today), Decimal("0.00"))
        spent_past = sum((tx.amount for tx in tx_rows if tx.transaction_date < today), Decimal("0.00"))
        total_spent_cycle = spent_past + spent_today

        # 5. Perhitungan Plafon Pengeluaran Ideal Hari Ini (Adaptive Daily Runway)
        # Anggaran hidup operasional per siklus = Pendapatan - Tagihan Pasti - Target Tabungan
        total_operational_budget = effective_monthly_income - total_monthly_fixed - plan.monthly_savings_target

        # Sisa jatah belanja operasional yang tersisa dari budget blueprint
        remaining_cycle_allowance = total_operational_budget - spent_past

        # Hitung ideal spending per hari berbasis dompet operasional riil & blueprint
        if safe_to_spend_total > 0 and days_remaining > 0:
            daily_cash_runway = safe_to_spend_total / Decimal(str(days_remaining))
            if plan.daily_living_budget > 0:
                ideal_spending_today = min(plan.daily_living_budget, daily_cash_runway)
            else:
                ideal_spending_today = daily_cash_runway
        elif remaining_cycle_allowance > 0 and days_remaining > 0:
            ideal_spending_today = remaining_cycle_allowance / Decimal(str(days_remaining))
        elif plan.daily_living_budget > 0:
            ideal_spending_today = plan.daily_living_budget
        else:
            ideal_spending_today = Decimal("0.00")

        # Pembulatan ideal ke integer terdekat
        ideal_spending_today = ideal_spending_today.quantize(Decimal("1.00"))
        daily_variance = ideal_spending_today - spent_today

        if spent_today == 0:
            today_status = "surplus"
            pct_used = 0.0
        elif ideal_spending_today > 0:
            pct_used = float((spent_today / ideal_spending_today) * Decimal("100.0"))
            if pct_used > 100.0:
                today_status = "deficit"
            elif pct_used >= 80.0:
                today_status = "warning"
            else:
                today_status = "surplus"
        else:
            pct_used = 100.0
            today_status = "deficit"

        # 5. Burn Rate & Runway Days Prediction
        # Rata-rata laju pengeluaran harian
        seven_days_ago = today - timedelta(days=6)
        recent_tx_sum = sum(
            (tx.amount for tx in tx_rows if tx.transaction_date >= seven_days_ago and tx.transaction_date <= today),
            Decimal("0.00"),
        )
        recent_days_count = max(1, (today - max(seven_days_ago, start_date)).days + 1)
        current_burn_rate_daily = (recent_tx_sum / Decimal(str(recent_days_count))).quantize(Decimal("1.00"))

        if current_burn_rate_daily <= 0:
            current_burn_rate_daily = (
                ideal_spending_today if ideal_spending_today > 0 else Decimal("30000.00")
            )

        # Berapa hari uang operasional bertahan jika burn rate dipertahankan?
        if current_burn_rate_daily > 0:
            predicted_runway_days = float(safe_to_spend_total / current_burn_rate_daily)
        else:
            predicted_runway_days = float(days_remaining)

        runway_exhaustion_date = today + timedelta(days=int(predicted_runway_days))
        is_runway_safe = predicted_runway_days >= float(days_remaining)

        if is_runway_safe:
            status_label = f"Aman! Bertahan {predicted_runway_days:.0f} hari (sampai akhir siklus)"
        else:
            days_short = float(days_remaining) - predicted_runway_days
            status_label = f"Waspada! Uang diprediksi habis {days_short:.0f} hari sebelum akhir siklus"

        # 6. End of Month Forecast (Proyeksi Tabungan & Saldo Akhir Berbasis Dompet Tabungan Nyata)
        # Tabungan tersimpan nyata saat ini di dompet savings
        operational_remaining = max(
            Decimal("0.00"),
            safe_to_spend_total - (current_burn_rate_daily * Decimal(str(days_remaining))),
        )
        # Proyeksi tabungan akhir = Saldo Tabungan Nyata + Sisa Operasional (jika ada surplus)
        projected_end_savings = savings_balance + operational_remaining
        savings_delta = projected_end_savings - plan.monthly_savings_target

        if projected_end_savings >= plan.monthly_savings_target:
            forecast_status = "on_track"
            advice = (
                f"Laju tabungan Anda aman! Tabungan Anda saat ini Rp{savings_balance:,.0f} dan diproyeksikan "
                f"mencapai Rp{projected_end_savings:,.0f} di akhir bulan."
            )
        elif projected_end_savings >= (plan.monthly_savings_target * Decimal("0.7")):
            forecast_status = "warning"
            advice = (
                f"Tabungan saat ini Rp{savings_balance:,.0f} dari target Rp{plan.monthly_savings_target:,.0f}. "
                f"Perketat belanja operasional agar target tabungan tercapai penuh."
            )
        else:
            forecast_status = "deficit"
            advice = (
                f"Tabungan saat ini Rp{savings_balance:,.0f} dari target Rp{plan.monthly_savings_target:,.0f}. "
                f"Sisihkan lebih awal begitu pemasukan tiba."
            )

        # 7. Format Fixed Expense Responses
        cat_map = {}
        for f in fixed_items:
            if f.category_id and f.category_id not in cat_map:
                cat_obj = await session.get(Category, f.category_id)
                cat_map[f.category_id] = cat_obj.name if cat_obj else None

        fixed_responses = [
            FixedExpenseResponse(
                id=f.id,
                user_id=f.user_id,
                name=f.name,
                amount=f.amount,
                category_id=f.category_id,
                category_name=cat_map.get(f.category_id),
                wallet_id=f.wallet_id,
                wallet_name=wallet_map[f.wallet_id].name if f.wallet_id and f.wallet_id in wallet_map else None,
                due_day_of_month=f.due_day_of_month,
                frequency=f.frequency,
                interval_value=f.interval_value,
                anchor_date=f.anchor_date,
                is_paid_this_cycle=f.is_paid_this_cycle,
                last_paid_at=f.last_paid_at,
                created_at=f.created_at,
            )
            for f in fixed_items
        ]

        return ForecastSummaryResponse(
            cycle_info=CycleInfo(
                cycle_start_date=start_date,
                cycle_end_date=end_date,
                days_elapsed=days_elapsed,
                days_remaining=days_remaining,
                total_days=total_cycle_days,
            ),
            today_metrics=TodayMetrics(
                date=today,
                ideal_spending_today=ideal_spending_today,
                actual_spent_today=spent_today,
                daily_variance=daily_variance,
                status=today_status,
                percentage_used=round(pct_used, 1),
            ),
            runway_prediction=RunwayPrediction(
                operational_balance_available=operational_balance,
                current_burn_rate_daily=current_burn_rate_daily,
                predicted_runway_days=round(predicted_runway_days, 1),
                runway_exhaustion_date=runway_exhaustion_date,
                is_runway_safe=is_runway_safe,
                status_label=status_label,
            ),
            fixed_obligations=FixedObligationsSummary(
                total_monthly_fixed=total_monthly_fixed,
                unpaid_fixed_buffer=unpaid_fixed_buffer,
                paid_fixed=paid_fixed,
                items=fixed_responses,
            ),
            end_of_month_forecast=EndOfMonthForecast(
                monthly_income=effective_monthly_income,
                target_savings=plan.monthly_savings_target,
                projected_end_savings=projected_end_savings.quantize(Decimal("1.00")),
                savings_delta=savings_delta.quantize(Decimal("1.00")),
                forecast_status=forecast_status,
                advice=advice,
            ),
            savings_pool_balance=savings_balance,
            current_savings_balance=savings_balance,
            subscription_pool_balance=subscription_balance,
            safe_to_spend_total=safe_to_spend_total,
            income_streams=stream_responses,
            total_monthly_income_estimated=effective_monthly_income,
        )

    @staticmethod
    async def get_daily_ledger(
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> DailyLedgerResponse:
        """
        Menghasilkan rekap harian aktual vs ideal persis seperti Spreadsheet Pengguna (Gambar 1 Tabel Kanan):
        - Tanggal
        - Total Pengeluaran
        - Pengeluaran Ideal
        - Sisa Pengeluaran Harian (+/-)
        """
        today = date.today()
        plan = await ForecastService.get_or_create_financial_plan(session, user_id)
        start_date, end_date = ForecastService.get_cycle_dates(plan.cycle_start_day, today)

        # Ambil seluruh pengeluaran siklus ini
        tx_query = select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.type == TransactionType.EXPENSE,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
        )
        tx_rows = (await session.exec(tx_query)).all()

        # Group per tanggal
        daily_spent_map = {}
        for tx in tx_rows:
            d = tx.transaction_date
            daily_spent_map[d] = daily_spent_map.get(d, Decimal("0.00")) + tx.amount

        # Hitung fixed dan budget operasional
        fixed_res = await session.exec(select(FixedExpense).where(FixedExpense.user_id == user_id))
        total_fixed = sum((f.amount for f in fixed_res.all()), Decimal("0.00"))

        total_cycle_days = (end_date - start_date).days + 1

        # Ambil sumber pendapatan aktif
        income_res = await session.exec(
            select(IncomeStream).where(IncomeStream.user_id == user_id, IncomeStream.is_active == True)
        )
        active_streams = income_res.all()
        total_stream_equiv = sum(
            (ForecastService.calculate_monthly_equivalent(s, total_cycle_days) for s in active_streams),
            Decimal("0.00"),
        )
        effective_income = total_stream_equiv if total_stream_equiv > 0 else plan.monthly_income

        total_op_budget = effective_income - total_fixed - plan.monthly_savings_target
        base_ideal = total_op_budget / Decimal(str(total_cycle_days)) if total_op_budget > 0 else plan.daily_living_budget

        day_names = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]

        items: List[DailyLedgerItem] = []
        running_spent = Decimal("0.00")
        total_spent_cycle = Decimal("0.00")
        total_ideal_cycle = Decimal("0.00")

        # Iterasi dari start_date sampai today (hari yang sudah berlalu & hari ini)
        curr = start_date
        while curr <= today:
            spent = daily_spent_map.get(curr, Decimal("0.00"))

            # Dinamika ideal: Budget tersisa / sisa hari
            days_left = (end_date - curr).days + 1
            rem_budget = total_op_budget - running_spent
            if rem_budget > 0 and days_left > 0:
                current_day_ideal = (rem_budget / Decimal(str(days_left))).quantize(Decimal("1.00"))
            else:
                current_day_ideal = base_ideal.quantize(Decimal("1.00"))

            variance = current_day_ideal - spent

            if spent == 0:
                st = "neutral"
            elif variance >= 0:
                st = "surplus"
            else:
                st = "deficit"

            # Periksa apakah ada jadwal pemasukan di tanggal ini
            sched_amt = Decimal("0.00")
            sched_names = []
            for s in active_streams:
                freq = (s.frequency or "monthly").lower()
                if freq == "daily":
                    sched_amt += s.amount
                    sched_names.append(s.name)
                elif freq == "weekly":
                    rec_day = s.receive_day if s.receive_day is not None else 0  # Default 0=Senin
                    if curr.weekday() == rec_day:
                        sched_amt += s.amount
                        sched_names.append(s.name)
                elif freq == "biweekly":
                    if (curr - start_date).days % 14 == 0:
                        sched_amt += s.amount
                        sched_names.append(s.name)
                elif freq == "monthly":
                    rec_day = s.receive_day if s.receive_day is not None else plan.cycle_start_day
                    if curr.day == rec_day:
                        sched_amt += s.amount
                        sched_names.append(s.name)

            items.append(
                DailyLedgerItem(
                    date=curr,
                    day_name=day_names[curr.weekday()],
                    total_spent=spent,
                    ideal_spending=current_day_ideal,
                    daily_variance=variance,
                    status=st,
                    scheduled_income=sched_amt if sched_amt > 0 else None,
                    scheduled_income_names=sched_names if sched_names else None,
                )
            )

            running_spent += spent
            total_spent_cycle += spent
            total_ideal_cycle += current_day_ideal
            curr += timedelta(days=1)

        net_variance = total_ideal_cycle - total_spent_cycle

        # Balik urutan agar hari terbaru muncul paling atas di mobile UI
        items.reverse()

        return DailyLedgerResponse(
            cycle_start_date=start_date,
            cycle_end_date=end_date,
            items=items,
            total_spent_cycle=total_spent_cycle,
            total_ideal_cycle=total_ideal_cycle,
            net_variance=net_variance,
        )

    @staticmethod
    async def simulate_purchase(
        session: AsyncSession,
        user_id: uuid.UUID,
        req: SimulationRequest,
    ) -> SimulationResponse:
        """
        Simulasi Belanja What-If ("Bisa Beli Nggak?") Sesuai Spreadsheet 3.
        Menguji dampak pembelian terhadap tabungan atau jatah operasional harian.
        """
        summary = await ForecastService.get_forecast_summary(session, user_id)

        current_savings = summary.savings_pool_balance
        current_daily_ideal = summary.today_metrics.ideal_spending_today

        if req.source == "savings_pool":
            projected_savings_after = current_savings - req.amount
            projected_daily_ideal_after = current_daily_ideal  # Tabungan tidak memotong uang makan harian

            # Ambang batas aman tabungan darurat (misal minimal 30% dari tabungan harus tersisa)
            is_affordable = projected_savings_after >= 0
            if projected_savings_after >= (current_savings * Decimal("0.5")):
                verdict = "safe"
                headline = f"✅ Aman Dibeli dari Tabungan!"
                explanation = (
                    f"Saldo tabungan Anda tersisa Rp{projected_savings_after:,.0f}. "
                    f"Pembelian ini tidak mengganggu jatah belanja harian Rp{current_daily_ideal:,.0f}/hari Anda sama sekali."
                )
            elif projected_savings_after >= 0:
                verdict = "warning"
                headline = f"⚠️ Cukup, Namun Menipiskan Tabungan"
                explanation = (
                    f"Saldo tabungan Anda akan tersisa Rp{projected_savings_after:,.0f}. "
                    f"Bisa dibeli, namun sisakan ruang untuk dana darurat tak terduga."
                )
            else:
                verdict = "danger"
                headline = f"❌ Tabungan Kurang Rp{abs(projected_savings_after):,.0f}"
                explanation = (
                    f"Tabungan Anda saat ini Rp{current_savings:,.0f}. Belum mencukupi untuk membeli {req.item_name} "
                    f"seharga Rp{req.amount:,.0f}."
                )
        else:
            # Dibeli dari jatah operasional harian
            days_left = summary.cycle_info.days_remaining
            rem_allowance = (summary.today_metrics.ideal_spending_today * Decimal(str(days_left))) - req.amount
            if rem_allowance > 0 and days_left > 0:
                projected_daily_ideal_after = (rem_allowance / Decimal(str(days_left))).quantize(Decimal("1.00"))
            else:
                projected_daily_ideal_after = Decimal("0.00")

            projected_savings_after = current_savings
            is_affordable = rem_allowance >= 0

            if projected_daily_ideal_after >= Decimal("30000.00"):
                verdict = "safe"
                headline = f"✅ Aman Dibeli dari Uang Jajan"
                explanation = (
                    f"Setelah pembelian ini, jatah harian Anda tersisa Rp{projected_daily_ideal_after:,.0f}/hari "
                    f"untuk {days_left} hari ke depan."
                )
            elif projected_daily_ideal_after > 0:
                verdict = "warning"
                headline = f"⚠️ Jatah Harian Menjadi Sangat Ketat"
                explanation = (
                    f"Jatah makan/belanja harian Anda akan turun dari Rp{current_daily_ideal:,.0f}/hari menjadi "
                    f"hanya Rp{projected_daily_ideal_after:,.0f}/hari hingga akhir bulan!"
                )
            else:
                verdict = "danger"
                headline = f"❌ Jangan Beli dari Uang Operasional!"
                explanation = (
                    f"Pembelian ini akan langsung menghabiskan jatah hidup Anda bulan ini "
                    f"dan membuat Anda boncos sebelum gajian berikutnya."
                )

        return SimulationResponse(
            item_name=req.item_name,
            amount=req.amount,
            source=req.source,
            is_affordable=is_affordable,
            verdict=verdict,
            headline=headline,
            explanation=explanation,
            current_savings=current_savings,
            projected_savings_after=projected_savings_after,
            current_daily_ideal=current_daily_ideal,
            projected_daily_ideal_after=projected_daily_ideal_after,
        )

    @staticmethod
    async def toggle_fixed_expense_paid(
        session: AsyncSession,
        user_id: uuid.UUID,
        expense_id: uuid.UUID,
    ) -> FixedExpenseResponse:
        """1-Tap Toggle status lunas tagihan pasti bulanan dengan debit dompet & pencatatan transaksi otomatis."""
        expense = await session.get(FixedExpense, expense_id)
        if not expense or expense.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tagihan tidak ditemukan.")

        expense.is_paid_this_cycle = not expense.is_paid_this_cycle

        target_wallet = None
        if expense.wallet_id:
            target_wallet = await session.get(Wallet, expense.wallet_id)

        if expense.is_paid_this_cycle:
            expense.last_paid_at = datetime.now(timezone.utc)
            # Jika terikat ke dompet, potong saldo dompet dan catat transaksi pengeluaran
            if target_wallet:
                target_wallet.balance -= expense.amount
                session.add(target_wallet)

                # Pastikan category_id tidak null untuk constraint tabel transactions
                cat_id = expense.category_id
                if not cat_id:
                    default_cat = (await session.exec(
                        select(Category).where(
                            Category.user_id == user_id,
                            Category.type == "expense"
                        )
                    )).first()
                    if not default_cat:
                        default_cat = Category(
                            user_id=user_id,
                            name="Tagihan & Langganan",
                            type="expense",
                            color="#F4AE52",
                        )
                        session.add(default_cat)
                        await session.flush()
                    cat_id = default_cat.id
                    expense.category_id = cat_id

                tx = Transaction(
                    user_id=user_id,
                    wallet_id=target_wallet.id,
                    category_id=cat_id,
                    amount=expense.amount,
                    type=TransactionType.EXPENSE,
                    description=f"Pembayaran tagihan: {expense.name}",
                    transaction_date=date.today(),
                )
                session.add(tx)
                await session.flush()
                expense.paid_transaction_id = tx.id
        else:
            expense.last_paid_at = None
            # Jika sebelumnya ada transaksi otomatis yang tercatat, refund saldo dompet & hapus transaksi
            if expense.paid_transaction_id:
                tx = await session.get(Transaction, expense.paid_transaction_id)
                if tx:
                    if tx.wallet_id:
                        tx_wallet = await session.get(Wallet, tx.wallet_id)
                        if tx_wallet:
                            tx_wallet.balance += tx.amount
                            session.add(tx_wallet)
                    await session.delete(tx)
                expense.paid_transaction_id = None

        session.add(expense)
        await session.commit()
        await session.refresh(expense)

        cat_name = None
        if expense.category_id:
            cat = await session.get(Category, expense.category_id)
            cat_name = cat.name if cat else None

        wallet_name = None
        if expense.wallet_id:
            w = await session.get(Wallet, expense.wallet_id)
            wallet_name = w.name if w else None

        return FixedExpenseResponse(
            id=expense.id,
            user_id=expense.user_id,
            name=expense.name,
            amount=expense.amount,
            category_id=expense.category_id,
            category_name=cat_name,
            wallet_id=expense.wallet_id,
            wallet_name=wallet_name,
            due_day_of_month=expense.due_day_of_month,
            frequency=expense.frequency,
            is_paid_this_cycle=expense.is_paid_this_cycle,
            last_paid_at=expense.last_paid_at,
            created_at=expense.created_at,
        )

    @staticmethod
    async def sync_financial_plan_income(session: AsyncSession, user_id: uuid.UUID) -> Decimal:
        """Menghitung total setara bulanan dari semua stream aktif dan menyinkronkan ke FinancialPlan."""
        plan = await ForecastService.get_or_create_financial_plan(session, user_id)
        start_date, end_date = ForecastService.get_cycle_dates(plan.cycle_start_day)
        total_cycle_days = (end_date - start_date).days + 1

        income_res = await session.exec(
            select(IncomeStream).where(IncomeStream.user_id == user_id, IncomeStream.is_active == True)
        )
        active_streams = income_res.all()
        if active_streams:
            total_monthly = sum(
                (ForecastService.calculate_monthly_equivalent(s, total_cycle_days) for s in active_streams),
                Decimal("0.00"),
            )
            plan.monthly_income = total_monthly
            plan.updated_at = datetime.now(timezone.utc)
            session.add(plan)
            await session.commit()
            await session.refresh(plan)
            return total_monthly
        return plan.monthly_income

    @staticmethod
    async def calculate_range_projection(
        session: AsyncSession,
        user_id: uuid.UUID,
        req: RangeProjectionRequest,
    ) -> RangeProjectionResponse:
        """
        Mesin Simulasi Buku Besar Masa Depan (Forward-Looking Time-Series Ledger).
        Menghitung mutasi harian dan rolling balance per tanggal dari start_date s/d end_date
        berdasarkan filter dompet (operasional, savings, spesifik, atau saldo bayangan simulasi).
        """
        today = date.today()
        plan = await ForecastService.get_or_create_financial_plan(session, user_id)
        start_date, end_cycle_date = ForecastService.get_cycle_dates(plan.cycle_start_day, today)

        start_d = req.start_date or today
        end_d = req.end_date or end_cycle_date
        if end_d < start_d:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tanggal akhir prediksi tidak boleh lebih awal dari tanggal mulai.",
            )

        # Batasi rentang maksimal 365 hari (1 tahun) demi efisiensi komputasi & performa browser
        MAX_PROJECTION_DAYS = 365
        is_clamped = False
        if (end_d - start_d).days > MAX_PROJECTION_DAYS:
            end_d = start_d + timedelta(days=MAX_PROJECTION_DAYS)
            is_clamped = True

        # 1. Ambil data dompet user
        wallets_res = await session.exec(select(Wallet).where(Wallet.user_id == user_id))
        wallets = wallets_res.all()
        wallet_map = {w.id: w for w in wallets}

        filter_type = req.wallet_filter or "all_operational"
        initial_balance = Decimal("0.00")
        filter_label = "Semua Dompet Operasional"

        if filter_type == "all_operational":
            initial_balance = sum(
                (w.balance for w in wallets if getattr(w, "purpose", "operational") == "operational"),
                Decimal("0.00"),
            )
            filter_label = "Semua Dompet Operasional"
        elif filter_type == "all_savings":
            initial_balance = sum(
                (w.balance for w in wallets if getattr(w, "purpose", None) == "savings"),
                Decimal("0.00"),
            )
            filter_label = "Semua Tabungan (Savings)"
        elif filter_type == "all_wallets":
            initial_balance = sum((w.balance for w in wallets), Decimal("0.00"))
            filter_label = "Seluruh Dompet (Konsolidasi)"
        elif filter_type == "custom_balance":
            initial_balance = req.custom_initial_balance or Decimal("0.00")
            filter_label = f"Simulasi Saldo Kustom (Rp{initial_balance:,.0f})"
        else:
            # Asumsi UUID dompet spesifik
            try:
                target_uuid = uuid.UUID(filter_type)
                target_w = wallet_map.get(target_uuid)
                if target_w:
                    initial_balance = target_w.balance
                    filter_label = f"Dompet: {target_w.name}"
                else:
                    filter_label = "Dompet Tidak Dikenal"
            except ValueError:
                filter_label = "Dompet Kustom"

        # 2. Patokan Jatah Makan Harian Dasar
        daily_meal = Decimal("0.00")
        if req.include_daily_meal and filter_type != "all_savings":
            if req.custom_daily_meal is not None:
                daily_meal = max(Decimal("0.00"), req.custom_daily_meal)
            else:
                daily_meal = max(Decimal("0.00"), plan.daily_living_budget)

        # 3. Ambil Sumber Pendapatan Aktif
        income_res = await session.exec(
            select(IncomeStream).where(IncomeStream.user_id == user_id, IncomeStream.is_active == True)
        )
        active_streams = income_res.all()

        # 4. Ambil Pengeluaran Pasti & Siklus Berkala
        fixed_res = await session.exec(select(FixedExpense).where(FixedExpense.user_id == user_id))
        fixed_items = fixed_res.all()

        # 5. Ambil Rencana Transaksi Belum Selesai dalam rentang
        pt_res = await session.exec(
            select(PlannedTransaction).where(
                PlannedTransaction.user_id == user_id,
                PlannedTransaction.is_completed == False,
                PlannedTransaction.planned_date >= start_d,
                PlannedTransaction.planned_date <= end_d,
            )
        )
        planned_txs = pt_res.all()

        # 6. Pengeluaran aktual hari ini (jika start_d <= today <= end_d) untuk mencegah double-deduction (Koreksi 4)
        today_spent_operational = Decimal("0.00")
        if start_d <= today <= end_d:
            tx_res = await session.exec(
                select(Transaction).where(
                    Transaction.user_id == user_id,
                    Transaction.type == TransactionType.EXPENSE,
                    Transaction.transaction_date == today,
                )
            )
            today_spent_operational = sum((t.amount for t in tx_res.all()), Decimal("0.00"))

        day_names = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]

        # Inisialisasi pelacak saldo tabungan berjalan (savings pool)
        initial_savings_balance = sum(
            (w.balance for w in wallets if getattr(w, "purpose", None) == "savings"),
            Decimal("0.00"),
        )
        running_savings_balance = initial_savings_balance
        total_saved_in_range = Decimal("0.00")

        timeline: List[ProjectedDayItem] = []
        running_balance = initial_balance
        total_inflow = Decimal("0.00")
        total_outflow = Decimal("0.00")
        lowest_balance = initial_balance
        lowest_balance_date = start_d
        critical_deficit_date = None

        curr = start_d
        while curr <= end_d:
            day_inflow = Decimal("0.00")
            day_outflow = Decimal("0.00")
            day_saved = Decimal("0.00")
            events: List[ProjectedDayEvent] = []

            # --- A. Inflow Check ---
            # 1. Income Streams
            for s in active_streams:
                stream_matches = False
                if filter_type in ("all_wallets", "custom_balance"):
                    stream_matches = True
                elif filter_type == "all_operational":
                    if s.wallet_id:
                        w = wallet_map.get(s.wallet_id)
                        stream_matches = (getattr(w, "purpose", "operational") == "operational")
                    else:
                        stream_matches = True
                elif filter_type == "all_savings":
                    if s.wallet_id:
                        w = wallet_map.get(s.wallet_id)
                        stream_matches = (getattr(w, "purpose", None) == "savings")
                else:
                    stream_matches = (str(s.wallet_id) == filter_type)

                if stream_matches and ForecastService.is_income_due_on_date(s, curr, plan.cycle_start_day):
                    day_inflow += s.amount
                    w_name = wallet_map[s.wallet_id].name if s.wallet_id and s.wallet_id in wallet_map else None
                    events.append(
                        ProjectedDayEvent(
                            type="INCOME",
                            name=f"Pemasukan: {s.name}",
                            amount=s.amount,
                            direction="INFLOW",
                            wallet_id=s.wallet_id,
                            wallet_name=w_name,
                        )
                    )

            # 2. Planned Transactions (INCOME / TRANSFER IN)
            for pt in planned_txs:
                if pt.planned_date == curr:
                    if pt.type == "INCOME":
                        pt_matches = False
                        if filter_type in ("all_wallets", "custom_balance"):
                            pt_matches = True
                        elif filter_type == "all_operational":
                            w = wallet_map.get(pt.wallet_id) if pt.wallet_id else None
                            pt_matches = (not w or getattr(w, "purpose", "operational") == "operational")
                        elif filter_type == "all_savings":
                            w = wallet_map.get(pt.wallet_id) if pt.wallet_id else None
                            pt_matches = (w and getattr(w, "purpose", None) == "savings")
                        else:
                            pt_matches = (str(pt.wallet_id) == filter_type)

                        if pt_matches:
                            day_inflow += pt.amount
                            w_name = wallet_map[pt.wallet_id].name if pt.wallet_id and pt.wallet_id in wallet_map else None
                            events.append(
                                ProjectedDayEvent(
                                    type="PLANNED",
                                    name=f"[Rencana Masuk] {pt.name}",
                                    amount=pt.amount,
                                    direction="INFLOW",
                                    wallet_id=pt.wallet_id,
                                    wallet_name=w_name,
                                )
                            )

                    elif pt.type == "TRANSFER":
                        pt_matches = False
                        if filter_type in ("all_wallets", "custom_balance"):
                            pt_matches = False
                        elif filter_type == "all_operational":
                            to_w = wallet_map.get(pt.to_wallet_id) if pt.to_wallet_id else None
                            from_w = wallet_map.get(pt.wallet_id) if pt.wallet_id else None
                            pt_matches = (
                                to_w and getattr(to_w, "purpose", "operational") == "operational" and
                                from_w and getattr(from_w, "purpose", "operational") != "operational"
                            )
                        elif filter_type == "all_savings":
                            to_w = wallet_map.get(pt.to_wallet_id) if pt.to_wallet_id else None
                            from_w = wallet_map.get(pt.wallet_id) if pt.wallet_id else None
                            pt_matches = (
                                to_w and getattr(to_w, "purpose", None) == "savings" and
                                from_w and getattr(from_w, "purpose", None) != "savings"
                            )
                        else:
                            pt_matches = (str(pt.to_wallet_id) == filter_type)

                        if pt_matches:
                            day_inflow += pt.amount
                            w_name = wallet_map[pt.to_wallet_id].name if pt.to_wallet_id and pt.to_wallet_id in wallet_map else None
                            events.append(
                                ProjectedDayEvent(
                                    type="PLANNED",
                                    name=f"[Transfer Masuk] {pt.name}",
                                    amount=pt.amount,
                                    direction="INFLOW",
                                    wallet_id=pt.to_wallet_id,
                                    wallet_name=w_name,
                                )
                            )

            # --- B. Outflow Check ---
            # 1. Patokan Makan Harian Dasar (Koreksi 4: sisa jatah hari ini jika curr == today)
            if daily_meal > 0:
                meal_cost = daily_meal
                if curr == today:
                    meal_cost = max(Decimal("0.00"), daily_meal - today_spent_operational)

                if meal_cost > 0:
                    day_outflow += meal_cost
                    events.append(
                        ProjectedDayEvent(
                            type="MEAL",
                            name="Patokan Makan & Jajan Harian",
                            amount=meal_cost,
                            direction="OUTFLOW",
                            wallet_id=None,
                            wallet_name=None,
                        )
                    )

            # 1b. Simulasi Alokasi Tabungan Harian (jika diaktifkan di filter proyeksi)
            if req.include_daily_savings:
                daily_savings_amount = Decimal("0.00")
                if req.custom_daily_savings is not None:
                    daily_savings_amount = max(Decimal("0.00"), req.custom_daily_savings)
                elif plan.monthly_savings_target > 0:
                    daily_savings_amount = max(
                        Decimal("0.00"), (plan.monthly_savings_target / Decimal("30.0")).quantize(Decimal("1.00"))
                    )

                if daily_savings_amount > 0:
                    if filter_type == "all_operational":
                        day_outflow += daily_savings_amount
                    elif filter_type == "all_savings":
                        day_inflow += daily_savings_amount
                    elif filter_type not in ("all_wallets", "custom_balance"):
                        # Jika memilih 1 dompet spesifik
                        try:
                            w = wallet_map.get(uuid.UUID(filter_type))
                            if w and getattr(w, "purpose", "operational") == "operational":
                                day_outflow += daily_savings_amount
                        except Exception:
                            pass

                    running_savings_balance += daily_savings_amount
                    day_saved += daily_savings_amount
                    total_saved_in_range += daily_savings_amount

                    primary_savings = next((w for w in wallets if getattr(w, "purpose", None) == "savings"), None)
                    events.append(
                        ProjectedDayEvent(
                            type="SAVINGS",
                            name="Simulasi Alokasi Tabungan",
                            amount=daily_savings_amount,
                            direction="OUTFLOW" if filter_type == "all_operational" else "INFLOW",
                            wallet_name="Kas Operasional",
                            to_wallet_name=primary_savings.name if primary_savings else "Tabungan",
                        )
                    )

            # 2. Tagihan Pasti Bulanan & Siklus Biaya Berkala / Transfer Tabungan Rutin
            for fe in fixed_items:
                if ForecastService.is_fixed_expense_due_on_date(fe, curr):
                    freq = (fe.frequency or "monthly").lower()
                    if freq == "monthly" and curr == today and fe.is_paid_this_cycle:
                        continue  # Sudah lunas hari ini/sebelumnya pada siklus ini

                    from_w = wallet_map.get(fe.wallet_id) if fe.wallet_id else None
                    to_w = wallet_map.get(fe.to_wallet_id) if fe.to_wallet_id else None

                    # Smart Auto-Detection untuk siklus tabungan
                    name_lower = (fe.name or "").lower()
                    has_savings_keyword = any(kw in name_lower for kw in ["tabung", "saving", "invest", "celengan", "nabung"])

                    is_savings_transfer = (
                        (getattr(fe, "expense_type", "EXPENSE") == "SAVINGS_TRANSFER")
                        or (to_w and getattr(to_w, "purpose", None) == "savings")
                        or has_savings_keyword
                    )

                    # Auto-fallback ke dompet tabungan utama jika belum dispesifikasikan
                    if is_savings_transfer and not to_w:
                        primary_savings = next((w for w in wallets if getattr(w, "purpose", None) == "savings"), None)
                        if primary_savings:
                            to_w = primary_savings

                    if is_savings_transfer:
                        # Mutasi transfer tabungan rutin
                        if filter_type in ("all_wallets", "custom_balance"):
                            pass  # Internal transfer antar dompet
                        elif filter_type == "all_operational":
                            if not from_w or getattr(from_w, "purpose", "operational") == "operational":
                                day_outflow += fe.amount
                        elif filter_type == "all_savings":
                            if to_w and getattr(to_w, "purpose", None) == "savings":
                                day_inflow += fe.amount
                        else:
                            if str(fe.wallet_id) == filter_type:
                                day_outflow += fe.amount
                            elif to_w and str(to_w.id) == filter_type:
                                day_inflow += fe.amount

                        running_savings_balance += fe.amount
                        day_saved += fe.amount
                        total_saved_in_range += fe.amount

                        events.append(
                            ProjectedDayEvent(
                                type="SAVINGS",
                                name=f"Setor Tabungan: {fe.name}",
                                amount=fe.amount,
                                direction="OUTFLOW" if filter_type == "all_operational" else "INFLOW",
                                wallet_id=fe.wallet_id,
                                wallet_name=from_w.name if from_w else None,
                                to_wallet_id=to_w.id if to_w else fe.to_wallet_id,
                                to_wallet_name=to_w.name if to_w else "Tabungan",
                            )
                        )
                    else:
                        # Pengeluaran rutin biasa (EXPENSE)
                        fe_matches = False
                        if filter_type in ("all_wallets", "custom_balance"):
                            fe_matches = True
                        elif filter_type == "all_operational":
                            fe_matches = (not from_w or getattr(from_w, "purpose", "operational") == "operational")
                        elif filter_type == "all_savings":
                            fe_matches = (from_w and getattr(from_w, "purpose", None) == "savings")
                        else:
                            fe_matches = (str(fe.wallet_id) == filter_type)

                        if fe_matches:
                            day_outflow += fe.amount
                            w_name = from_w.name if from_w else None
                            ev_type = "CYCLICAL" if freq in ("daily", "weekly", "biweekly", "every_n_days") else "FIXED_BILL"
                            events.append(
                                ProjectedDayEvent(
                                    type=ev_type,
                                    name=fe.name,
                                    amount=fe.amount,
                                    direction="OUTFLOW",
                                    wallet_id=fe.wallet_id,
                                    wallet_name=w_name,
                                )
                            )

            # 3. Planned Transactions (EXPENSE / TRANSFER / SAVINGS)
            for pt in planned_txs:
                if pt.planned_date == curr:
                    from_w = wallet_map.get(pt.wallet_id) if pt.wallet_id else None
                    to_w = wallet_map.get(pt.to_wallet_id) if pt.to_wallet_id else None
                    is_pt_savings = (pt.type == "SAVINGS") or (
                        pt.type == "TRANSFER" and to_w and getattr(to_w, "purpose", None) == "savings"
                    )

                    if is_pt_savings:
                        if filter_type in ("all_wallets", "custom_balance"):
                            pass
                        elif filter_type == "all_operational":
                            if not from_w or getattr(from_w, "purpose", "operational") == "operational":
                                day_outflow += pt.amount
                        elif filter_type == "all_savings":
                            if to_w and getattr(to_w, "purpose", None) == "savings":
                                day_inflow += pt.amount
                        else:
                            if str(pt.wallet_id) == filter_type:
                                day_outflow += pt.amount
                            elif str(pt.to_wallet_id) == filter_type:
                                day_inflow += pt.amount

                        running_savings_balance += pt.amount
                        day_saved += pt.amount
                        total_saved_in_range += pt.amount

                        events.append(
                            ProjectedDayEvent(
                                type="SAVINGS",
                                name=f"[Rencana Tabungan] {pt.name}",
                                amount=pt.amount,
                                direction="OUTFLOW" if filter_type == "all_operational" else "INFLOW",
                                wallet_id=pt.wallet_id,
                                wallet_name=from_w.name if from_w else None,
                                to_wallet_id=pt.to_wallet_id,
                                to_wallet_name=to_w.name if to_w else None,
                            )
                        )

                    elif pt.type == "EXPENSE":
                        if from_w and getattr(from_w, "purpose", None) == "savings":
                            running_savings_balance = max(Decimal("0.00"), running_savings_balance - pt.amount)

                        pt_matches = False
                        if filter_type in ("all_wallets", "custom_balance"):
                            pt_matches = True
                        elif filter_type == "all_operational":
                            pt_matches = (not from_w or getattr(from_w, "purpose", "operational") == "operational")
                        elif filter_type == "all_savings":
                            pt_matches = (from_w and getattr(from_w, "purpose", None) == "savings")
                        else:
                            pt_matches = (str(pt.wallet_id) == filter_type)

                        if pt_matches:
                            day_outflow += pt.amount
                            w_name = from_w.name if from_w else None
                            events.append(
                                ProjectedDayEvent(
                                    type="PLANNED",
                                    name=f"[Rencana Keluar] {pt.name}",
                                    amount=pt.amount,
                                    direction="OUTFLOW",
                                    wallet_id=pt.wallet_id,
                                    wallet_name=w_name,
                                )
                            )

                    elif pt.type == "TRANSFER":
                        # Transfer umum antar dompet (bukan ke savings)
                        if from_w and getattr(from_w, "purpose", None) == "savings" and (not to_w or getattr(to_w, "purpose", None) != "savings"):
                            running_savings_balance = max(Decimal("0.00"), running_savings_balance - pt.amount)

                        pt_matches = False
                        if filter_type in ("all_wallets", "custom_balance"):
                            pt_matches = False
                        elif filter_type == "all_operational":
                            pt_matches = (
                                from_w and getattr(from_w, "purpose", "operational") == "operational" and
                                to_w and getattr(to_w, "purpose", "operational") != "operational"
                            )
                        elif filter_type == "all_savings":
                            pt_matches = (
                                from_w and getattr(from_w, "purpose", None) == "savings" and
                                to_w and getattr(to_w, "purpose", None) != "savings"
                            )
                        else:
                            pt_matches = (str(pt.wallet_id) == filter_type)

                        if pt_matches:
                            day_outflow += pt.amount
                            w_name = from_w.name if from_w else None
                            events.append(
                                ProjectedDayEvent(
                                    type="PLANNED",
                                    name=f"[Transfer Keluar] {pt.name}",
                                    amount=pt.amount,
                                    direction="OUTFLOW",
                                    wallet_id=pt.wallet_id,
                                    wallet_name=w_name,
                                )
                            )

            closing_balance = running_balance + day_inflow - day_outflow
            is_def = closing_balance < 0
            if is_def and critical_deficit_date is None:
                critical_deficit_date = curr

            if closing_balance < lowest_balance:
                lowest_balance = closing_balance
                lowest_balance_date = curr

            timeline.append(
                ProjectedDayItem(
                    date=curr,
                    day_name=day_names[curr.weekday()],
                    is_today=(curr == today),
                    initial_balance=running_balance,
                    total_inflow=day_inflow,
                    total_outflow=day_outflow,
                    closing_balance=closing_balance,
                    running_savings_balance=running_savings_balance,
                    day_saved=day_saved,
                    is_deficit=is_def,
                    events=events,
                )
            )

            total_inflow += day_inflow
            total_outflow += day_outflow
            running_balance = closing_balance
            curr += timedelta(days=1)

        total_days = (end_d - start_d).days + 1
        is_safe = (critical_deficit_date is None) and (running_balance >= 0)

        target_savings = plan.monthly_savings_target or Decimal("0.00")
        savings_rate = (total_saved_in_range / target_savings * Decimal("100.00")) if target_savings > 0 else Decimal("0.00")

        return RangeProjectionResponse(
            start_date=start_d,
            end_date=end_d,
            total_days=total_days,
            wallet_filter=filter_type,
            wallet_filter_label=filter_label,
            initial_balance=initial_balance,
            total_inflow=total_inflow,
            total_outflow=total_outflow,
            final_balance=running_balance,
            lowest_balance=lowest_balance,
            lowest_balance_date=lowest_balance_date,
            critical_deficit_date=critical_deficit_date,
            is_safe=is_safe,
            is_clamped=is_clamped,
            max_allowed_days=MAX_PROJECTION_DAYS,
            initial_savings_balance=initial_savings_balance,
            total_saved_in_range=total_saved_in_range,
            final_savings_balance=running_savings_balance,
            target_savings=target_savings,
            savings_achievement_rate=min(Decimal("100.00"), savings_rate).quantize(Decimal("1.00")),
            timeline=timeline,
        )

    @staticmethod
    async def get_planned_transactions(
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> List[PlannedTransactionResponse]:
        """Ambil seluruh daftar rencana transaksi masa depan user."""
        wallets_res = await session.exec(select(Wallet).where(Wallet.user_id == user_id))
        wallet_map = {w.id: w.name for w in wallets_res.all()}

        cat_res = await session.exec(select(Category).where(Category.user_id == user_id))
        cat_map = {c.id: c.name for c in cat_res.all()}

        query = (
            select(PlannedTransaction)
            .where(PlannedTransaction.user_id == user_id)
            .order_by(PlannedTransaction.planned_date, PlannedTransaction.created_at)
        )
        items = (await session.exec(query)).all()

        return [
            PlannedTransactionResponse(
                id=item.id,
                user_id=item.user_id,
                name=item.name,
                amount=item.amount,
                type=item.type,
                wallet_id=item.wallet_id,
                wallet_name=wallet_map.get(item.wallet_id),
                to_wallet_id=item.to_wallet_id,
                to_wallet_name=wallet_map.get(item.to_wallet_id),
                category_id=item.category_id,
                category_name=cat_map.get(item.category_id),
                planned_date=item.planned_date,
                is_completed=item.is_completed,
                notes=item.notes,
                created_at=item.created_at,
            )
            for item in items
        ]

    @staticmethod
    async def create_planned_transaction(
        session: AsyncSession,
        user_id: uuid.UUID,
        payload: PlannedTransactionCreate,
    ) -> PlannedTransactionResponse:
        """Tambah rencana transaksi masa depan baru."""
        item = PlannedTransaction(
            user_id=user_id,
            name=payload.name,
            amount=payload.amount,
            type=payload.type.upper(),
            wallet_id=payload.wallet_id,
            to_wallet_id=payload.to_wallet_id,
            category_id=payload.category_id,
            planned_date=payload.planned_date,
            is_completed=payload.is_completed,
            notes=payload.notes,
        )
        session.add(item)
        await session.commit()
        await session.refresh(item)

        w_name = None
        if item.wallet_id:
            w = await session.get(Wallet, item.wallet_id)
            w_name = w.name if w else None

        to_w_name = None
        if item.to_wallet_id:
            to_w = await session.get(Wallet, item.to_wallet_id)
            to_w_name = to_w.name if to_w else None

        c_name = None
        if item.category_id:
            c = await session.get(Category, item.category_id)
            c_name = c.name if c else None

        return PlannedTransactionResponse(
            id=item.id,
            user_id=item.user_id,
            name=item.name,
            amount=item.amount,
            type=item.type,
            wallet_id=item.wallet_id,
            wallet_name=w_name,
            to_wallet_id=item.to_wallet_id,
            to_wallet_name=to_w_name,
            category_id=item.category_id,
            category_name=c_name,
            planned_date=item.planned_date,
            is_completed=item.is_completed,
            notes=item.notes,
            created_at=item.created_at,
        )

    @staticmethod
    async def update_planned_transaction(
        session: AsyncSession,
        user_id: uuid.UUID,
        planned_id: uuid.UUID,
        payload: PlannedTransactionUpdate,
    ) -> PlannedTransactionResponse:
        """Perbarui rencana transaksi masa depan."""
        item = await session.get(PlannedTransaction, planned_id)
        if not item or item.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rencana transaksi tidak ditemukan.")

        update_data = payload.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if key == "type" and value:
                setattr(item, key, value.upper())
            else:
                setattr(item, key, value)

        session.add(item)
        await session.commit()
        await session.refresh(item)

        w_name = None
        if item.wallet_id:
            w = await session.get(Wallet, item.wallet_id)
            w_name = w.name if w else None

        to_w_name = None
        if item.to_wallet_id:
            to_w = await session.get(Wallet, item.to_wallet_id)
            to_w_name = to_w.name if to_w else None

        c_name = None
        if item.category_id:
            c = await session.get(Category, item.category_id)
            c_name = c.name if c else None

        return PlannedTransactionResponse(
            id=item.id,
            user_id=item.user_id,
            name=item.name,
            amount=item.amount,
            type=item.type,
            wallet_id=item.wallet_id,
            wallet_name=w_name,
            to_wallet_id=item.to_wallet_id,
            to_wallet_name=to_w_name,
            category_id=item.category_id,
            category_name=c_name,
            planned_date=item.planned_date,
            is_completed=item.is_completed,
            notes=item.notes,
            created_at=item.created_at,
        )

    @staticmethod
    async def delete_planned_transaction(
        session: AsyncSession,
        user_id: uuid.UUID,
        planned_id: uuid.UUID,
    ) -> bool:
        """Hapus rencana transaksi masa depan."""
        item = await session.get(PlannedTransaction, planned_id)
        if not item or item.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rencana transaksi tidak ditemukan.")

        await session.delete(item)
        await session.commit()
        return True

    @staticmethod
    async def execute_planned_transaction(
        session: AsyncSession,
        user_id: uuid.UUID,
        planned_id: uuid.UUID,
    ) -> PlannedTransactionResponse:
        """Eksekusi rencana transaksi menjadi mutasi riil (Transaction & Wallet Balance)."""
        item = await session.get(PlannedTransaction, planned_id)
        if not item or item.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rencana transaksi tidak ditemukan.")

        if item.is_completed:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rencana transaksi ini sudah pernah dieksekusi.")

        # Ambil atau buat kategori default jika kosong
        cat_id = item.category_id
        if not cat_id:
            cat_type = "income" if item.type == "INCOME" else "expense"
            cat = (await session.exec(select(Category).where(Category.user_id == user_id, Category.type == cat_type))).first()
            if not cat:
                cat = Category(
                    user_id=user_id,
                    name="Lain-lain",
                    type=cat_type,
                    color="#4E7B6D" if cat_type == "income" else "#D96B43",
                )
                session.add(cat)
                await session.flush()
            cat_id = cat.id

        if item.type == "EXPENSE":
            if item.wallet_id:
                w = await session.get(Wallet, item.wallet_id)
                if w:
                    w.balance -= item.amount
                    session.add(w)

            tx = Transaction(
                user_id=user_id,
                wallet_id=item.wallet_id,
                category_id=cat_id,
                amount=item.amount,
                type=TransactionType.EXPENSE,
                description=f"[Eksekusi Rencana] {item.name}",
                transaction_date=date.today(),
            )
            session.add(tx)

        elif item.type == "INCOME":
            if item.wallet_id:
                w = await session.get(Wallet, item.wallet_id)
                if w:
                    w.balance += item.amount
                    session.add(w)

            tx = Transaction(
                user_id=user_id,
                wallet_id=item.wallet_id,
                category_id=cat_id,
                amount=item.amount,
                type=TransactionType.INCOME,
                description=f"[Eksekusi Rencana] {item.name}",
                transaction_date=date.today(),
            )
            session.add(tx)

        elif item.type in ("TRANSFER", "SAVINGS"):
            if item.wallet_id:
                from_w = await session.get(Wallet, item.wallet_id)
                if from_w:
                    from_w.balance -= item.amount
                    session.add(from_w)
            if item.to_wallet_id:
                to_w = await session.get(Wallet, item.to_wallet_id)
                if to_w:
                    to_w.balance += item.amount
                    session.add(to_w)

            desc_label = f"[Eksekusi Tabungan] {item.name}" if item.type == "SAVINGS" else f"[Eksekusi Transfer Rencana] {item.name}"
            tx = Transaction(
                user_id=user_id,
                wallet_id=item.wallet_id,
                to_wallet_id=item.to_wallet_id,
                category_id=cat_id,
                amount=item.amount,
                type=TransactionType.TRANSFER,
                description=desc_label,
                transaction_date=date.today(),
            )
            session.add(tx)

        item.is_completed = True
        session.add(item)
        await session.commit()
        await session.refresh(item)

        w_name = None
        if item.wallet_id:
            w = await session.get(Wallet, item.wallet_id)
            w_name = w.name if w else None

        to_w_name = None
        if item.to_wallet_id:
            to_w = await session.get(Wallet, item.to_wallet_id)
            to_w_name = to_w.name if to_w else None

        c_name = None
        if item.category_id:
            c = await session.get(Category, item.category_id)
            c_name = c.name if c else None

        return PlannedTransactionResponse(
            id=item.id,
            user_id=item.user_id,
            name=item.name,
            amount=item.amount,
            type=item.type,
            wallet_id=item.wallet_id,
            wallet_name=w_name,
            to_wallet_id=item.to_wallet_id,
            to_wallet_name=to_w_name,
            category_id=item.category_id,
            category_name=c_name,
            planned_date=item.planned_date,
            is_completed=item.is_completed,
            notes=item.notes,
            created_at=item.created_at,
        )

