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
    async def get_forecast_summary(
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> ForecastSummaryResponse:
        """
        Engine Prediksi Utama: Menghitung seluruh metrik proyeksi dan runway finansial.
        - Dynamic Daily Runway (Batas Belanja Ideal Hari Ini)
        - Cadangan Tagihan Pasti (Fixed Buffer)
        - Estimasi Daya Tahan Uang (Runway Days)
        - Proyeksi Tabungan Akhir Bulan
        """
        today = date.today()
        plan = await ForecastService.get_or_create_financial_plan(session, user_id)
        start_date, end_date = ForecastService.get_cycle_dates(plan.cycle_start_day, today)

        total_cycle_days = (end_date - start_date).days + 1
        days_elapsed = (today - start_date).days
        days_remaining = max(1, (end_date - today).days + 1)  # Termasuk hari ini

        # 1. Multi-Stream Income: Ambil semua sumber pendapatan aktif
        income_res = await session.exec(
            select(IncomeStream).where(IncomeStream.user_id == user_id, IncomeStream.is_active == True)
        )
        active_streams = income_res.all()

        stream_responses = []
        total_stream_equivalent = Decimal("0.00")
        for s in active_streams:
            equiv = ForecastService.calculate_monthly_equivalent(s, total_cycle_days)
            total_stream_equivalent += equiv
            stream_responses.append(
                IncomeStreamResponse(
                    id=s.id,
                    user_id=s.user_id,
                    name=s.name,
                    amount=s.amount,
                    frequency=s.frequency,
                    receive_day=s.receive_day,
                    is_active=s.is_active,
                    monthly_equivalent=equiv,
                    created_at=s.created_at,
                    updated_at=s.updated_at,
                )
            )

        # Pendapatan efektif: Jika user mendefinisikan income streams, gunakan total setara bulanan; jika tidak, gunakan blueprint lama
        effective_monthly_income = total_stream_equivalent if total_stream_equivalent > 0 else plan.monthly_income

        # 2. Dompet Operasional vs Pool Tabungan vs Pool Tagihan (Subscription)
        wallets_res = await session.exec(select(Wallet).where(Wallet.user_id == user_id))
        wallets = wallets_res.all()
        wallet_map = {w.id: w for w in wallets}

        savings_balance = Decimal("0.00")
        subscription_balance = Decimal("0.00")
        operational_balance = Decimal("0.00")

        for w in wallets:
            w_purpose = getattr(w, "purpose", "operational") or "operational"
            w_name = w.name.lower()
            if w_purpose == "savings" or "saving" in w_name or "anniv" in w_name or "tabung" in w_name:
                savings_balance += w.balance
            elif w_purpose == "subscription" or "subscrip" in w_name or "tagihan" in w_name:
                subscription_balance += w.balance
            else:
                operational_balance += w.balance

        # 3. Tagihan Pasti / Fixed Obligations
        fixed_res = await session.exec(select(FixedExpense).where(FixedExpense.user_id == user_id))
        fixed_items = fixed_res.all()

        total_monthly_fixed = sum((f.amount for f in fixed_items), Decimal("0.00"))
        unpaid_fixed_items = [f for f in fixed_items if not f.is_paid_this_cycle]
        paid_fixed = total_monthly_fixed - sum((f.amount for f in unpaid_fixed_items), Decimal("0.00"))

        # Pisahkan buffer tagihan: apakah ditanggung dompet subscription atau dompet operasional?
        unpaid_sub_buffer = Decimal("0.00")
        unpaid_op_buffer = Decimal("0.00")

        for f in unpaid_fixed_items:
            assigned_wallet = wallet_map.get(f.wallet_id) if f.wallet_id else None
            is_sub_wallet = (
                assigned_wallet
                and (
                    getattr(assigned_wallet, "purpose", "") == "subscription"
                    or "subscrip" in assigned_wallet.name.lower()
                    or "tagihan" in assigned_wallet.name.lower()
                )
            )
            if is_sub_wallet or (f.wallet_id is None and subscription_balance > 0):
                unpaid_sub_buffer += f.amount
            else:
                unpaid_op_buffer += f.amount

        # Jika saldo subscription kurang untuk tagihannya, kekurangannya meluber ke operasional
        sub_deficit = max(Decimal("0.00"), unpaid_sub_buffer - subscription_balance)
        effective_op_unpaid_buffer = unpaid_op_buffer + sub_deficit
        unpaid_fixed_buffer = unpaid_sub_buffer + unpaid_op_buffer

        # Saldo Operasional Bebas (setelah mencadangkan tagihan pasti yang memotong operasional)
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

