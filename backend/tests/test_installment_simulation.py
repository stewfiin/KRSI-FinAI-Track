import os
import sys
import types
import unittest
import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

# Pastikan root backend masuk sys.path saat dijalankan langsung dari root workspace
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Fallback stub jika test dijalankan di Python lokal tanpa email-validator (hanya dipakai oleh schemas/auth.py)
try:
    import email_validator  # noqa: F401
except ImportError:
    import pydantic.networks

    stub = types.ModuleType("email_validator")
    stub.validate_email = lambda email, **kwargs: types.SimpleNamespace(normalized=email, email=email)
    stub.EmailNotValidError = ValueError
    sys.modules["email_validator"] = stub
    pydantic.networks.email_validator = stub
    pydantic.networks.import_email_validator = lambda: None

from app.schemas.forecast import (
    CycleInfo,
    EndOfMonthForecast,
    FixedObligationsSummary,
    ForecastSummaryResponse,
    InstallmentSimulationRequest,
    RunwayPrediction,
    TodayMetrics,
)
from app.services.installment_service import InstallmentService


def _make_mock_summary(
    monthly_income: str = "6000000.00",
    total_fixed: str = "1500000.00",
    target_savings: str = "1000000.00",
    savings_balance: str = "10000000.00",
    safe_to_spend: str = "3000000.00",
    daily_ideal: str = "100000.00",
) -> ForecastSummaryResponse:
    return ForecastSummaryResponse(
        cycle_info=CycleInfo(
            cycle_start_date=date(2026, 11, 1),
            cycle_end_date=date(2026, 11, 30),
            days_elapsed=12,
            days_remaining=18,
            total_days=30,
        ),
        today_metrics=TodayMetrics(
            date=date(2026, 11, 13),
            ideal_spending_today=Decimal(daily_ideal),
            actual_spent_today=Decimal("0.00"),
            daily_variance=Decimal(daily_ideal),
            status="surplus",
            percentage_used=0.0,
        ),
        runway_prediction=RunwayPrediction(
            operational_balance_available=Decimal(safe_to_spend),
            current_burn_rate_daily=Decimal("50000.00"),
            predicted_runway_days=30.0,
            runway_exhaustion_date=date(2026, 12, 13),
            is_runway_safe=True,
            status_label="Aman",
        ),
        fixed_obligations=FixedObligationsSummary(
            total_monthly_fixed=Decimal(total_fixed),
            unpaid_fixed_buffer=Decimal("0.00"),
            paid_fixed=Decimal(total_fixed),
            items=[],
        ),
        end_of_month_forecast=EndOfMonthForecast(
            monthly_income=Decimal(monthly_income),
            target_savings=Decimal(target_savings),
            projected_end_savings=Decimal(savings_balance),
            savings_delta=Decimal("0.00"),
            forecast_status="on_track",
            advice="Aman",
        ),
        savings_pool_balance=Decimal(savings_balance),
        current_savings_balance=Decimal(savings_balance),
        subscription_pool_balance=Decimal("0.00"),
        safe_to_spend_total=Decimal(safe_to_spend),
        income_streams=[],
        total_monthly_income_estimated=Decimal(monthly_income),
    )


class TestInstallmentMath(unittest.TestCase):
    def test_zero_percent_installment(self):
        calc = InstallmentService.compute_schedule(
            principal=Decimal("12000000.00"),
            tenor_months=12,
            interest_type="zero",
            monthly_rate=Decimal("0"),
            monthly_fee=Decimal("0.00"),
            start_date=date(2026, 11, 13),
            due_day=13,
        )
        self.assertEqual(calc["monthly_installment"], Decimal("1000000.00"))
        self.assertEqual(calc["total_interest"], Decimal("0.00"))
        self.assertEqual(calc["total_installment_payments"], Decimal("12000000.00"))
        self.assertEqual(len(calc["schedule"]), 12)
        self.assertEqual(calc["schedule"][-1].remaining_principal, Decimal("0.00"))

    def test_flat_interest_installment(self):
        # Pokok 10jt, bunga 1%/bulan, tenor 10 bulan => pokok 1jt/bln + bunga 100rb/bln
        rate = InstallmentService.get_monthly_rate("flat", Decimal("1"), "monthly")
        calc = InstallmentService.compute_schedule(
            principal=Decimal("10000000.00"),
            tenor_months=10,
            interest_type="flat",
            monthly_rate=rate,
            monthly_fee=Decimal("5000.00"),
            start_date=date(2026, 11, 1),
            due_day=1,
        )
        self.assertEqual(calc["monthly_installment"], Decimal("1105000.00"))
        self.assertEqual(calc["total_interest"], Decimal("1000000.00"))
        self.assertEqual(calc["total_fees"], Decimal("50000.00"))
        self.assertEqual(calc["schedule"][-1].remaining_principal, Decimal("0.00"))

    def test_effective_annuity_installment(self):
        # Pokok 12jt, bunga 12%/tahun (1%/bulan), tenor 12 bulan
        rate = InstallmentService.get_monthly_rate("effective", Decimal("12"), "annual")
        calc = InstallmentService.compute_schedule(
            principal=Decimal("12000000.00"),
            tenor_months=12,
            interest_type="effective",
            monthly_rate=rate,
            monthly_fee=Decimal("0.00"),
            start_date=date(2026, 11, 15),
            due_day=15,
        )
        schedule = calc["schedule"]
        self.assertEqual(len(schedule), 12)
        self.assertEqual(schedule[0].total_payment, Decimal("1066185.46"))
        self.assertEqual(schedule[-1].remaining_principal, Decimal("0.00"))
        self.assertEqual(
            sum(row.principal_amount for row in schedule),
            Decimal("12000000.00"),
        )
        # Bunga bulan terakhir lebih kecil daripada bulan pertama
        self.assertGreater(schedule[0].interest_amount, schedule[-1].interest_amount)

    def test_due_date_clamped_for_february(self):
        calc = InstallmentService.compute_schedule(
            principal=Decimal("3000000.00"),
            tenor_months=3,
            interest_type="zero",
            monthly_rate=Decimal("0"),
            monthly_fee=Decimal("0.00"),
            start_date=date(2026, 1, 31),
            due_day=31,
        )
        self.assertEqual(calc["schedule"][0].due_date, date(2026, 2, 28))
        self.assertEqual(calc["schedule"][1].due_date, date(2026, 3, 31))
        self.assertEqual(calc["schedule"][2].due_date, date(2026, 4, 30))

    def test_validation_rejects_dp_gte_price(self):
        req = InstallmentSimulationRequest(
            item_name="HP",
            item_price=Decimal("5000000"),
            down_payment=Decimal("5000000"),
            tenor_months=6,
            interest_type="zero",
        )
        with self.assertRaises(HTTPException) as ctx:
            InstallmentService.validate_and_normalize(req)
        self.assertEqual(ctx.exception.status_code, 400)


class TestInstallmentAffordabilityAsync(unittest.IsolatedAsyncioTestCase):
    async def test_safe_verdict_and_tenor_comparisons(self):
        summary = _make_mock_summary()
        req = InstallmentSimulationRequest(
            item_name="Laptop Kerja",
            item_price=Decimal("10000000"),
            down_payment=Decimal("2000000"),
            dp_source="savings_pool",
            tenor_months=12,
            interest_type="zero",
            interest_rate=Decimal("0"),
            admin_fee=Decimal("0"),
            monthly_fee=Decimal("0"),
            start_date=date(2026, 11, 13),
        )
        with patch(
            "app.services.installment_service.ForecastService.get_forecast_summary",
            new=AsyncMock(return_value=summary),
        ):
            res = await InstallmentService.simulate_installment(
                session=MagicMock(),
                user_id=uuid.uuid4(),
                req=req,
            )

        self.assertEqual(res.verdict, "safe")
        self.assertTrue(res.is_dp_affordable)
        self.assertTrue(res.is_monthly_affordable)
        self.assertEqual(res.principal_amount, Decimal("8000000.00"))
        self.assertEqual(res.projected_savings_after_dp, Decimal("8000000.00"))
        self.assertEqual([c.tenor_months for c in res.tenor_comparisons], [3, 6, 12, 24])

    async def test_danger_verdict_when_dp_exceeds_savings(self):
        summary = _make_mock_summary(savings_balance="500000.00")
        req = InstallmentSimulationRequest(
            item_name="Motor",
            item_price=Decimal("20000000"),
            down_payment=Decimal("4000000"),
            dp_source="savings_pool",
            tenor_months=24,
            interest_type="flat",
            interest_rate=Decimal("1.5"),
            interest_rate_period="monthly",
            start_date=date(2026, 11, 13),
        )
        with patch(
            "app.services.installment_service.ForecastService.get_forecast_summary",
            new=AsyncMock(return_value=summary),
        ):
            res = await InstallmentService.simulate_installment(
                session=MagicMock(),
                user_id=uuid.uuid4(),
                req=req,
            )

        self.assertEqual(res.verdict, "danger")
        self.assertFalse(res.is_dp_affordable)
        self.assertEqual(res.projected_savings_after_dp, Decimal("-3500000.00"))
        self.assertGreater(len(res.recommendations), 0)


if __name__ == "__main__":
    unittest.main()
