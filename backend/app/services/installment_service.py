import calendar
import uuid
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.planned_transaction import PlannedTransaction
from app.models.wallet import Wallet
from app.schemas.forecast import (
    ForecastSummaryResponse,
    InstallmentAmortizationItem,
    InstallmentApplyRequest,
    InstallmentApplyResponse,
    InstallmentSimulationRequest,
    InstallmentSimulationResponse,
    InstallmentTenorComparison,
)
from app.services.forecast_service import ForecastService

TWO_PLACES = Decimal("1.00")


def _q(val: Decimal) -> Decimal:
    """Bulatkan nominal ke 2 desimal sesuai presisi Numeric(15, 2)."""
    return val.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _add_months(base_date: date, months: int, due_day: Optional[int] = None) -> date:
    """Menambahkan N bulan dengan menjaga tanggal jatuh tempo terhadap batas hari tiap bulan."""
    total_months = (base_date.year * 12 + (base_date.month - 1)) + months
    target_year = total_months // 12
    target_month = (total_months % 12) + 1
    target_day = due_day or base_date.day
    _, last_day = calendar.monthrange(target_year, target_month)
    return date(target_year, target_month, min(target_day, last_day))


class InstallmentService:
    """Engine kalkulasi cicilan (0%, Flat, Efektif/Anuitas) dan analisis kelayakan finansial."""

    @staticmethod
    def validate_and_normalize(req: InstallmentSimulationRequest) -> Tuple[str, str, str]:
        interest_type = (req.interest_type or "flat").strip().lower()
        if interest_type not in ("zero", "flat", "effective"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Skema bunga harus bernilai 'zero', 'flat', atau 'effective'.",
            )

        rate_period = (req.interest_rate_period or "annual").strip().lower()
        if rate_period not in ("monthly", "annual"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Periode suku bunga harus bernilai 'monthly' atau 'annual'.",
            )

        dp_source = (req.dp_source or "savings_pool").strip().lower()
        if dp_source not in ("savings_pool", "operational_wallet"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sumber DP harus bernilai 'savings_pool' atau 'operational_wallet'.",
            )

        if req.down_payment >= req.item_price:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uang muka (DP) harus lebih kecil dari harga barang.",
            )

        return interest_type, rate_period, dp_source

    @staticmethod
    def get_monthly_rate(interest_type: str, interest_rate: Decimal, rate_period: str) -> Decimal:
        """Konversi suku bunga persen menjadi rasio bunga bulanan."""
        if interest_type == "zero" or interest_rate <= 0:
            return Decimal("0")
        pct = interest_rate / Decimal("100")
        if rate_period == "annual":
            return pct / Decimal("12")
        return pct

    @staticmethod
    def compute_schedule(
        principal: Decimal,
        tenor_months: int,
        interest_type: str,
        monthly_rate: Decimal,
        monthly_fee: Decimal,
        start_date: date,
        due_day: Optional[int],
    ) -> Dict:
        """Menghitung rincian angsuran & jadwal amortisasi lengkap."""
        schedule: List[InstallmentAmortizationItem] = []
        remaining = _q(principal)
        total_interest = Decimal("0.00")
        total_fees = Decimal("0.00")
        total_payments = Decimal("0.00")

        effective_due_day = due_day or start_date.day

        if interest_type == "effective" and monthly_rate > 0:
            one_plus_r = Decimal("1") + monthly_rate
            factor = one_plus_r ** tenor_months
            raw_annuity = principal * monthly_rate * factor / (factor - Decimal("1"))
            base_annuity = _q(raw_annuity)

            for idx in range(1, tenor_months + 1):
                due_d = _add_months(start_date, idx, effective_due_day)
                interest_k = _q(remaining * monthly_rate)
                if idx < tenor_months:
                    principal_k = min(remaining, max(Decimal("0.00"), base_annuity - interest_k))
                else:
                    principal_k = remaining

                fee_k = _q(monthly_fee)
                total_k = principal_k + interest_k + fee_k
                remaining = max(Decimal("0.00"), remaining - principal_k)

                total_interest += interest_k
                total_fees += fee_k
                total_payments += total_k

                schedule.append(
                    InstallmentAmortizationItem(
                        month_index=idx,
                        due_date=due_d,
                        principal_amount=principal_k,
                        interest_amount=interest_k,
                        fee_amount=fee_k,
                        total_payment=total_k,
                        remaining_principal=remaining,
                    )
                )
        else:
            # Skema 0% atau Bunga Flat
            base_principal = _q(principal / Decimal(str(tenor_months)))
            fixed_interest = (
                _q(principal * monthly_rate)
                if (interest_type == "flat" and monthly_rate > 0)
                else Decimal("0.00")
            )

            for idx in range(1, tenor_months + 1):
                due_d = _add_months(start_date, idx, effective_due_day)
                if idx < tenor_months:
                    principal_k = min(remaining, base_principal)
                else:
                    principal_k = remaining

                fee_k = _q(monthly_fee)
                total_k = principal_k + fixed_interest + fee_k
                remaining = max(Decimal("0.00"), remaining - principal_k)

                total_interest += fixed_interest
                total_fees += fee_k
                total_payments += total_k

                schedule.append(
                    InstallmentAmortizationItem(
                        month_index=idx,
                        due_date=due_d,
                        principal_amount=principal_k,
                        interest_amount=fixed_interest,
                        fee_amount=fee_k,
                        total_payment=total_k,
                        remaining_principal=remaining,
                    )
                )

        first_payment = schedule[0].total_payment if schedule else Decimal("0.00")
        last_payment = schedule[-1].total_payment if schedule else Decimal("0.00")
        avg_monthly = _q(total_payments / Decimal(str(tenor_months))) if tenor_months > 0 else Decimal("0.00")

        return {
            "monthly_installment": first_payment if interest_type == "effective" else avg_monthly,
            "first_month_installment": first_payment,
            "last_month_installment": last_payment,
            "total_interest": _q(total_interest),
            "total_fees": _q(total_fees),
            "total_installment_payments": _q(total_payments),
            "schedule": schedule,
        }

    @staticmethod
    def evaluate_affordability(
        monthly_installment: Decimal,
        upfront_cash_needed: Decimal,
        dp_source: str,
        summary: ForecastSummaryResponse,
    ) -> Dict:
        """Mengevaluasi dampak DP dan cicilan bulanan terhadap kondisi keuangan pengguna."""
        current_savings = _q(summary.savings_pool_balance)
        current_safe_to_spend = _q(summary.safe_to_spend_total)

        monthly_income = _q(
            summary.total_monthly_income_estimated
            if summary.total_monthly_income_estimated > 0
            else summary.end_of_month_forecast.monthly_income
        )
        monthly_fixed = _q(summary.fixed_obligations.total_monthly_fixed)
        target_savings = _q(summary.end_of_month_forecast.target_savings)

        current_free_cashflow = _q(monthly_income - monthly_fixed - target_savings)
        projected_free_cashflow = _q(current_free_cashflow - monthly_installment)

        if monthly_income > 0:
            dsr_percent = round(float((monthly_installment / monthly_income) * Decimal("100")), 1)
        else:
            dsr_percent = 100.0 if monthly_installment > 0 else 0.0

        # Dampak DP + biaya admin awal
        if dp_source == "savings_pool":
            projected_savings_after_dp = _q(current_savings - upfront_cash_needed)
            projected_safe_to_spend_after_dp = current_safe_to_spend
            is_dp_affordable = projected_savings_after_dp >= Decimal("0.00")
        else:
            projected_savings_after_dp = current_savings
            projected_safe_to_spend_after_dp = _q(current_safe_to_spend - upfront_cash_needed)
            is_dp_affordable = projected_safe_to_spend_after_dp >= Decimal("0.00")

        # Dampak ke jatah belanja harian (Daily Runway)
        total_days = max(1, summary.cycle_info.total_days)
        days_remaining = max(1, summary.cycle_info.days_remaining)
        current_daily_ideal = _q(summary.today_metrics.ideal_spending_today)

        daily_burden = _q(monthly_installment / Decimal(str(total_days)))
        if dp_source == "operational_wallet" and upfront_cash_needed > 0:
            rem_pool = (current_daily_ideal * Decimal(str(days_remaining))) - upfront_cash_needed
            daily_after_dp = max(Decimal("0.00"), rem_pool / Decimal(str(days_remaining)))
            projected_daily_ideal_after = _q(max(Decimal("0.00"), daily_after_dp - daily_burden))
        else:
            projected_daily_ideal_after = _q(max(Decimal("0.00"), current_daily_ideal - daily_burden))

        is_monthly_affordable = (
            projected_free_cashflow >= Decimal("0.00")
            and (monthly_income <= 0 or dsr_percent <= 30.0)
            and projected_daily_ideal_after > Decimal("0.00")
        )

        # Penentuan Vonis (safe | warning | danger)
        dp_depletes_half_savings = (
            dp_source == "savings_pool"
            and upfront_cash_needed > 0
            and current_savings > 0
            and projected_savings_after_dp < (current_savings * Decimal("0.5"))
        )
        daily_becomes_very_tight = (
            current_daily_ideal >= Decimal("15000.00")
            and projected_daily_ideal_after < Decimal("15000.00")
        )
        daily_becomes_tight = (
            current_daily_ideal >= Decimal("30000.00")
            and projected_daily_ideal_after < Decimal("30000.00")
        )

        if (
            not is_dp_affordable
            or (monthly_income > 0 and dsr_percent > 30.0)
            or projected_free_cashflow < Decimal("0.00")
            or daily_becomes_very_tight
        ):
            verdict = "danger"
        elif dp_depletes_half_savings or dsr_percent > 20.0 or daily_becomes_tight:
            verdict = "warning"
        else:
            verdict = "safe"

        return {
            "is_dp_affordable": is_dp_affordable,
            "is_monthly_affordable": is_monthly_affordable,
            "verdict": verdict,
            "current_savings": current_savings,
            "projected_savings_after_dp": projected_savings_after_dp,
            "current_safe_to_spend": current_safe_to_spend,
            "projected_safe_to_spend_after_dp": projected_safe_to_spend_after_dp,
            "current_monthly_income": monthly_income,
            "current_monthly_fixed": monthly_fixed,
            "current_monthly_free_cashflow": current_free_cashflow,
            "projected_monthly_free_cashflow": projected_free_cashflow,
            "installment_to_income_ratio": dsr_percent,
            "current_daily_ideal": current_daily_ideal,
            "projected_daily_ideal_after": projected_daily_ideal_after,
        }

    @staticmethod
    def build_verdict_messages(
        req: InstallmentSimulationRequest,
        dp_source: str,
        upfront_cash: Decimal,
        monthly_installment: Decimal,
        afford: Dict,
        comparisons: List[InstallmentTenorComparison],
    ) -> Tuple[str, str, List[str]]:
        verdict = afford["verdict"]
        dsr = afford["installment_to_income_ratio"]
        proj_daily = afford["projected_daily_ideal_after"]
        proj_free = afford["projected_monthly_free_cashflow"]

        recommendations: List[str] = []

        if verdict == "safe":
            headline = f"✅ Cicilan Aman Diambil ({dsr:.1f}% dari pendapatan)"
            explanation = (
                f"Angsuran Rp{monthly_installment:,.0f}/bulan masih masuk ruang aman arus kas Anda. "
                f"Jatah harian tetap sehat di Rp{proj_daily:,.0f}/hari dan sisa cashflow bulanan masih "
                f"surplus Rp{proj_free:,.0f}."
            )
        elif verdict == "warning":
            headline = f"⚠️ Bisa Diambil, Namun Anggaran Cukup Ketat"
            reasons = []
            if dsr > 20.0:
                reasons.append(f"rasio cicilan mencapai {dsr:.1f}% dari pendapatan")
            if dp_source == "savings_pool" and upfront_cash > 0 and afford["projected_savings_after_dp"] < afford["current_savings"] * Decimal("0.5"):
                reasons.append("DP menggerus lebih dari separuh saldo tabungan")
            if proj_daily < Decimal("30000.00"):
                reasons.append(f"jatah harian turun ke Rp{proj_daily:,.0f}/hari")
            reason_text = ", ".join(reasons) if reasons else "margin keuangan menyempit"
            explanation = (
                f"Cicilan Rp{monthly_installment:,.0f}/bulan masih bisa ditanggung, tetapi {reason_text}. "
                f"Pastikan tidak ada pengeluaran dadakan selama masa tenor."
            )
        else:
            headline = "❌ Risiko Defisit Berat — Sebaiknya Tunda atau Sesuaikan"
            if not afford["is_dp_affordable"]:
                src_label = "Tabungan" if dp_source == "savings_pool" else "Kas Operasional Bebas"
                kurang = abs(
                    afford["projected_savings_after_dp"]
                    if dp_source == "savings_pool"
                    else afford["projected_safe_to_spend_after_dp"]
                )
                explanation = (
                    f"Dana awal (DP + biaya admin) sebesar Rp{upfront_cash:,.0f} melebihi {src_label} Anda "
                    f"(kurang Rp{kurang:,.0f})."
                )
            elif proj_free < Decimal("0.00"):
                explanation = (
                    f"Cicilan Rp{monthly_installment:,.0f}/bulan membuat cashflow bulanan Anda minus "
                    f"Rp{abs(proj_free):,.0f} setelah dikurangi tagihan rutin & target tabungan."
                )
            else:
                explanation = (
                    f"Beban cicilan Rp{monthly_installment:,.0f}/bulan ({dsr:.1f}% dari pendapatan) terlalu berat "
                    f"dan menekan jatah belanja harian menjadi Rp{proj_daily:,.0f}/hari."
                )

        # Saran konkret otomatis
        if not afford["is_dp_affordable"]:
            recommendations.append("Naikkan porsi tabungan atau tunggu hingga dana DP & biaya admin terkumpul penuh.")
        safer_tenor = next(
            (c for c in comparisons if c.tenor_months > req.tenor_months and c.verdict in ("safe", "warning")),
            None,
        )
        if verdict != "safe" and safer_tenor:
            recommendations.append(
                f"Pertimbangkan tenor {safer_tenor.tenor_months} bulan (Rp{safer_tenor.monthly_installment:,.0f}/bln, "
                f"rasio {safer_tenor.income_ratio_percent:.1f}%) agar arus kas lebih lega."
            )
        if req.down_payment == 0 and verdict != "safe":
            recommendations.append("Tambahkan uang muka (DP) minimal 20% untuk menurunkan cicilan bulanan dan total bunga.")
        if not recommendations and verdict == "safe":
            recommendations.append("Anda dapat menjadwalkan DP dan angsuran ini ke Prediksi Saldo untuk memantau dampaknya.")

        return headline, explanation, recommendations

    @staticmethod
    async def simulate_installment(
        session: AsyncSession,
        user_id: uuid.UUID,
        req: InstallmentSimulationRequest,
    ) -> InstallmentSimulationResponse:
        """Menjalankan simulasi cicilan lengkap dengan uji kelayakan terhadap kondisi keuangan pengguna."""
        interest_type, rate_period, dp_source = InstallmentService.validate_and_normalize(req)
        summary = await ForecastService.get_forecast_summary(session, user_id)

        start_d = req.start_date or date.today()
        principal = _q(req.item_price - req.down_payment)
        upfront_cash = _q(req.down_payment + req.admin_fee)
        monthly_rate = InstallmentService.get_monthly_rate(interest_type, req.interest_rate, rate_period)

        main_calc = InstallmentService.compute_schedule(
            principal=principal,
            tenor_months=req.tenor_months,
            interest_type=interest_type,
            monthly_rate=monthly_rate,
            monthly_fee=req.monthly_fee,
            start_date=start_d,
            due_day=req.due_day_of_month,
        )

        total_fees = _q(req.admin_fee + main_calc["total_fees"])
        total_cost = _q(req.down_payment + req.admin_fee + main_calc["total_installment_payments"])
        markup_pct = round(float(((total_cost - req.item_price) / req.item_price) * Decimal("100")), 1)

        afford = InstallmentService.evaluate_affordability(
            monthly_installment=main_calc["monthly_installment"],
            upfront_cash_needed=upfront_cash,
            dp_source=dp_source,
            summary=summary,
        )

        # Perbandingan multi-tenor (3, 6, 12, 24 bulan + tenor pilihan user jika unik)
        preset_tenors = sorted(set([3, 6, 12, 24, req.tenor_months]))
        comparisons: List[InstallmentTenorComparison] = []
        for t in preset_tenors:
            c_calc = InstallmentService.compute_schedule(
                principal=principal,
                tenor_months=t,
                interest_type=interest_type,
                monthly_rate=monthly_rate,
                monthly_fee=req.monthly_fee,
                start_date=start_d,
                due_day=req.due_day_of_month,
            )
            c_afford = InstallmentService.evaluate_affordability(
                monthly_installment=c_calc["monthly_installment"],
                upfront_cash_needed=upfront_cash,
                dp_source=dp_source,
                summary=summary,
            )
            c_total_interest_fees = _q(req.admin_fee + c_calc["total_interest"] + c_calc["total_fees"])
            c_total_payment = _q(req.down_payment + req.admin_fee + c_calc["total_installment_payments"])
            comparisons.append(
                InstallmentTenorComparison(
                    tenor_months=t,
                    monthly_installment=c_calc["monthly_installment"],
                    total_interest_and_fees=c_total_interest_fees,
                    total_payment=c_total_payment,
                    income_ratio_percent=c_afford["installment_to_income_ratio"],
                    projected_daily_ideal_after=c_afford["projected_daily_ideal_after"],
                    verdict=c_afford["verdict"],
                )
            )

        headline, explanation, recommendations = InstallmentService.build_verdict_messages(
            req=req,
            dp_source=dp_source,
            upfront_cash=upfront_cash,
            monthly_installment=main_calc["monthly_installment"],
            afford=afford,
            comparisons=comparisons,
        )

        return InstallmentSimulationResponse(
            item_name=req.item_name.strip(),
            item_price=_q(req.item_price),
            down_payment=_q(req.down_payment),
            dp_source=dp_source,
            tenor_months=req.tenor_months,
            interest_type=interest_type,
            interest_rate=req.interest_rate,
            interest_rate_period=rate_period,
            admin_fee=_q(req.admin_fee),
            monthly_fee=_q(req.monthly_fee),
            principal_amount=principal,
            upfront_cash_needed=upfront_cash,
            monthly_installment=main_calc["monthly_installment"],
            first_month_installment=main_calc["first_month_installment"],
            last_month_installment=main_calc["last_month_installment"],
            total_interest=main_calc["total_interest"],
            total_fees=total_fees,
            total_installment_payments=main_calc["total_installment_payments"],
            total_cost=total_cost,
            effective_markup_percent=max(0.0, markup_pct),
            is_dp_affordable=afford["is_dp_affordable"],
            is_monthly_affordable=afford["is_monthly_affordable"],
            verdict=afford["verdict"],
            headline=headline,
            explanation=explanation,
            recommendations=recommendations,
            current_savings=afford["current_savings"],
            projected_savings_after_dp=afford["projected_savings_after_dp"],
            current_safe_to_spend=afford["current_safe_to_spend"],
            projected_safe_to_spend_after_dp=afford["projected_safe_to_spend_after_dp"],
            current_monthly_income=afford["current_monthly_income"],
            current_monthly_fixed=afford["current_monthly_fixed"],
            current_monthly_free_cashflow=afford["current_monthly_free_cashflow"],
            projected_monthly_free_cashflow=afford["projected_monthly_free_cashflow"],
            installment_to_income_ratio=afford["installment_to_income_ratio"],
            current_daily_ideal=afford["current_daily_ideal"],
            projected_daily_ideal_after=afford["projected_daily_ideal_after"],
            amortization_schedule=main_calc["schedule"],
            tenor_comparisons=comparisons,
        )

    @staticmethod
    async def apply_to_planned_transactions(
        session: AsyncSession,
        user_id: uuid.UUID,
        req: InstallmentApplyRequest,
    ) -> InstallmentApplyResponse:
        """Mengonversi jadwal cicilan menjadi PlannedTransaction agar langsung masuk ke Time-Series Projection."""
        interest_type, rate_period, dp_source = InstallmentService.validate_and_normalize(req)
        start_d = req.start_date or date.today()
        principal = _q(req.item_price - req.down_payment)
        upfront_cash = _q(req.down_payment + req.admin_fee)
        monthly_rate = InstallmentService.get_monthly_rate(interest_type, req.interest_rate, rate_period)

        calc = InstallmentService.compute_schedule(
            principal=principal,
            tenor_months=req.tenor_months,
            interest_type=interest_type,
            monthly_rate=monthly_rate,
            monthly_fee=req.monthly_fee,
            start_date=start_d,
            due_day=req.due_day_of_month,
        )

        # Resolusi dompet default jika wallet_id tidak dispesifikasikan
        wallets = (await session.exec(select(Wallet).where(Wallet.user_id == user_id))).all()
        op_wallet = next((w for w in wallets if getattr(w, "purpose", "operational") == "operational"), None)
        sav_wallet = next((w for w in wallets if getattr(w, "purpose", None) == "savings"), None)

        installment_wallet_id = req.wallet_id or (op_wallet.id if op_wallet else None)
        dp_wallet_id = req.wallet_id or (
            sav_wallet.id if (dp_source == "savings_pool" and sav_wallet) else (op_wallet.id if op_wallet else None)
        )

        created_items: List[PlannedTransaction] = []
        clean_name = req.item_name.strip()

        if req.include_down_payment and upfront_cash > 0:
            dp_item = PlannedTransaction(
                user_id=user_id,
                name=f"DP Cicilan: {clean_name}"[:150],
                amount=upfront_cash,
                type="EXPENSE",
                wallet_id=dp_wallet_id,
                planned_date=start_d,
                is_completed=False,
                notes=f"DP Rp{req.down_payment:,.0f} + Admin Rp{req.admin_fee:,.0f}",
            )
            created_items.append(dp_item)

        for row in calc["schedule"]:
            pt = PlannedTransaction(
                user_id=user_id,
                name=f"Cicilan {row.month_index}/{req.tenor_months}: {clean_name}"[:150],
                amount=row.total_payment,
                type="EXPENSE",
                wallet_id=installment_wallet_id,
                planned_date=row.due_date,
                is_completed=False,
                notes=f"Pokok Rp{row.principal_amount:,.0f} + Bunga/Biaya Rp{(row.interest_amount + row.fee_amount):,.0f}",
            )
            created_items.append(pt)

        session.add_all(created_items)
        await session.commit()
        for item in created_items:
            await session.refresh(item)

        return InstallmentApplyResponse(
            created_count=len(created_items),
            item_name=clean_name,
            planned_ids=[item.id for item in created_items],
            message=f"Berhasil menjadwalkan {len(created_items)} rencana pembayaran '{clean_name}' ke Prediksi Saldo.",
        )
