import calendar
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple

from app.schemas.forecast import InstallmentAmortizationItem

TWO_PLACES = Decimal("1.00")


def quantize_money(val: Decimal) -> Decimal:
    """Bulatkan nominal ke 2 desimal sesuai presisi Numeric(15, 2)."""
    return val.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def add_months(base_date: date, months: int, due_day: Optional[int] = None) -> date:
    """Menambahkan N bulan dengan menjaga tanggal jatuh tempo terhadap batas hari tiap bulan."""
    total_months = (base_date.year * 12 + (base_date.month - 1)) + months
    target_year = total_months // 12
    target_month = (total_months % 12) + 1
    target_day = due_day or base_date.day
    _, last_day = calendar.monthrange(target_year, target_month)
    return date(target_year, target_month, min(target_day, last_day))


def get_monthly_rate(interest_type: str, interest_rate: Decimal, rate_period: str) -> Decimal:
    """Konversi suku bunga persen menjadi rasio bunga bulanan."""
    if interest_type == "zero" or interest_rate <= 0:
        return Decimal("0")
    pct = interest_rate / Decimal("100")
    if rate_period == "annual":
        return pct / Decimal("12")
    return pct


def compute_installment_schedule(
    principal: Decimal,
    tenor_months: int,
    interest_type: str,
    monthly_rate: Decimal,
    monthly_fee: Decimal,
    start_date: date,
    due_day: Optional[int],
) -> Dict:
    """Menghitung rincian angsuran & jadwal amortisasi lengkap (0%, Flat, atau Efektif)."""
    schedule: List[InstallmentAmortizationItem] = []
    remaining = quantize_money(principal)
    total_interest = Decimal("0.00")
    total_fees = Decimal("0.00")
    total_payments = Decimal("0.00")

    effective_due_day = due_day or start_date.day

    if interest_type == "effective" and monthly_rate > 0:
        one_plus_r = Decimal("1") + monthly_rate
        factor = one_plus_r ** tenor_months
        raw_annuity = principal * monthly_rate * factor / (factor - Decimal("1"))
        base_annuity = quantize_money(raw_annuity)

        for idx in range(1, tenor_months + 1):
            due_d = add_months(start_date, idx, effective_due_day)
            interest_k = quantize_money(remaining * monthly_rate)
            if idx < tenor_months:
                principal_k = min(remaining, max(Decimal("0.00"), base_annuity - interest_k))
            else:
                principal_k = remaining

            fee_k = quantize_money(monthly_fee)
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
        base_principal = quantize_money(principal / Decimal(str(tenor_months)))
        fixed_interest = (
            quantize_money(principal * monthly_rate)
            if (interest_type == "flat" and monthly_rate > 0)
            else Decimal("0.00")
        )

        for idx in range(1, tenor_months + 1):
            due_d = add_months(start_date, idx, effective_due_day)
            if idx < tenor_months:
                principal_k = min(remaining, base_principal)
            else:
                principal_k = remaining

            fee_k = quantize_money(monthly_fee)
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
    avg_monthly = quantize_money(total_payments / Decimal(str(tenor_months))) if tenor_months > 0 else Decimal("0.00")

    return {
        "monthly_installment": first_payment if interest_type == "effective" else avg_monthly,
        "first_month_installment": first_payment,
        "last_month_installment": last_payment,
        "total_interest": quantize_money(total_interest),
        "total_fees": quantize_money(total_fees),
        "total_installment_payments": quantize_money(total_payments),
        "schedule": schedule,
    }


def compute_installment_breakdown(
    principal: Decimal,
    tenor_months: int,
    interest_type: Optional[str],
    interest_rate: Optional[Decimal],
    interest_rate_period: Optional[str],
) -> Tuple[Decimal, Decimal, Decimal]:
    """Menghitung (angsuran_bulanan, total_bunga, total_bayar) untuk tagihan cicilan."""
    norm_type = (interest_type or "zero").strip().lower()
    if norm_type not in ("zero", "flat", "effective"):
        norm_type = "flat"
    norm_period = (interest_rate_period or "monthly").strip().lower()
    if norm_period not in ("monthly", "annual"):
        norm_period = "monthly"
    rate = interest_rate if interest_rate is not None else Decimal("0.00")
    if rate <= 0:
        norm_type = "zero"

    monthly_rate = get_monthly_rate(norm_type, rate, norm_period)
    calc = compute_installment_schedule(
        principal=principal,
        tenor_months=tenor_months,
        interest_type=norm_type,
        monthly_rate=monthly_rate,
        monthly_fee=Decimal("0.00"),
        start_date=date.today(),
        due_day=None,
    )
    return (
        calc["monthly_installment"],
        calc["total_interest"],
        calc["total_installment_payments"],
    )
