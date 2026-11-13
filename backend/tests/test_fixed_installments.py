import os
import sys
import types
import unittest
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

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

from app.models.financial_plan import FinancialPlan
from app.models.fixed_expense import FixedExpense
from app.models.wallet import Wallet
from app.schemas.forecast import RangeProjectionRequest
from app.services.forecast_service import ForecastService


class FakeResult:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items

    def first(self):
        return self._items[0] if self._items else None


class TestFixedInstallments(unittest.IsolatedAsyncioTestCase):
    def test_resolve_installment_fields_zero_flat_and_effective(self):
        # 1. Tanpa bunga (0%): 12jt / 12 bln = 1jt/bln
        amt, itype, irate, iperiod, tenor, paid = ForecastService.resolve_installment_fields(
            expense_type="INSTALLMENT",
            amount=None,
            principal_amount=Decimal("12000000"),
            interest_type="zero",
            interest_rate=Decimal("0"),
            interest_rate_period="monthly",
            total_tenor=12,
            paid_installments=2,
        )
        self.assertEqual(amt, Decimal("1000000.00"))
        self.assertEqual(itype, "zero")
        self.assertEqual(irate, Decimal("0.00"))
        self.assertEqual(tenor, 12)
        self.assertEqual(paid, 2)

        # 2. Bunga Flat 2% per bulan untuk 10jt, 10 bln -> pokok 1jt + bunga 200rb = 1.2jt
        amt_flat, itype_flat, irate_flat, iperiod_flat, _, _ = ForecastService.resolve_installment_fields(
            expense_type="INSTALLMENT",
            amount=None,
            principal_amount=Decimal("10000000"),
            interest_type="flat",
            interest_rate=Decimal("2"),
            interest_rate_period="monthly",
            total_tenor=10,
            paid_installments=0,
        )
        self.assertEqual(amt_flat, Decimal("1200000.00"))
        self.assertEqual(itype_flat, "flat")
        self.assertEqual(irate_flat, Decimal("2"))
        self.assertEqual(iperiod_flat, "monthly")

        # 3. Bunga Efektif/Anuitas 12% per tahun (1%/bln) > pokok rata-rata (1jt)
        amt_eff, itype_eff, _, _, _, _ = ForecastService.resolve_installment_fields(
            expense_type="INSTALLMENT",
            amount=None,
            principal_amount=Decimal("12000000"),
            interest_type="effective",
            interest_rate=Decimal("12"),
            interest_rate_period="annual",
            total_tenor=12,
            paid_installments=15,  # di-clamp ke 12
        )
        self.assertGreater(amt_eff, Decimal("1000000.00"))
        self.assertLess(amt_eff, Decimal("1120000.00"))
        self.assertEqual(itype_eff, "effective")

    def test_resolve_installment_validation_errors(self):
        with self.assertRaises(HTTPException):
            ForecastService.resolve_installment_fields(
                expense_type="INSTALLMENT",
                amount=None,
                principal_amount=Decimal("0"),
                interest_type="flat",
                interest_rate=Decimal("2"),
                interest_rate_period="monthly",
                total_tenor=6,
                paid_installments=0,
            )

        with self.assertRaises(HTTPException):
            ForecastService.resolve_installment_fields(
                expense_type="INSTALLMENT",
                amount=None,
                principal_amount=Decimal("1000000"),
                interest_type="invalid",
                interest_rate=Decimal("2"),
                interest_rate_period="monthly",
                total_tenor=6,
                paid_installments=0,
            )

    async def test_toggle_paid_updates_paid_installments(self):
        user_id = uuid.uuid4()
        expense_id = uuid.uuid4()
        fe = FixedExpense(
            id=expense_id,
            user_id=user_id,
            name="Cicilan Laptop",
            amount=Decimal("1100000.00"),
            expense_type="INSTALLMENT",
            due_day_of_month=10,
            frequency="monthly",
            principal_amount=Decimal("6000000.00"),
            interest_type="flat",
            interest_rate=Decimal("1.67"),
            interest_rate_period="monthly",
            total_tenor=6,
            paid_installments=1,
            is_paid_this_cycle=False,
            created_at=datetime.now(timezone.utc),
        )

        session = AsyncMock()
        session.get = AsyncMock(return_value=fe)
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        # Check -> paid_installments naik dari 1 ke 2
        res_paid = await ForecastService.toggle_fixed_expense_paid(session, user_id, expense_id)
        self.assertTrue(res_paid.is_paid_this_cycle)
        self.assertEqual(res_paid.paid_installments, 2)
        self.assertEqual(res_paid.remaining_installments, 4)

        # Uncheck -> paid_installments turun kembali ke 1
        res_unpaid = await ForecastService.toggle_fixed_expense_paid(session, user_id, expense_id)
        self.assertFalse(res_unpaid.is_paid_this_cycle)
        self.assertEqual(res_unpaid.paid_installments, 1)
        self.assertEqual(res_unpaid.remaining_installments, 5)

    async def test_summary_and_projection_respect_remaining_tenor(self):
        user_id = uuid.uuid4()
        today = date.today()

        op_wallet = Wallet(
            id=uuid.uuid4(),
            user_id=user_id,
            name="BCA",
            type="BANK",
            purpose="operational",
            balance=Decimal("10000000.00"),
        )
        plan = FinancialPlan(
            id=uuid.uuid4(),
            user_id=user_id,
            monthly_income=Decimal("8000000.00"),
            daily_living_budget=Decimal("0.00"),
            monthly_savings_target=Decimal("0.00"),
            cycle_start_day=1,
            is_active=True,
        )

        # Cicilan aktif sisa 2 bulan (paid 4/6), jatuh tempo tiap tanggal today.day
        active_installment = FixedExpense(
            id=uuid.uuid4(),
            user_id=user_id,
            name="Cicilan HP",
            amount=Decimal("500000.00"),
            expense_type="INSTALLMENT",
            due_day_of_month=today.day,
            frequency="monthly",
            principal_amount=Decimal("3000000.00"),
            interest_type="zero",
            interest_rate=Decimal("0.00"),
            interest_rate_period="monthly",
            total_tenor=6,
            paid_installments=4,
            is_paid_this_cycle=False,
            created_at=datetime.now(timezone.utc),
        )
        # Cicilan sudah lunas total (paid 6/6) -> tidak boleh mengurangi buffer/proyeksi
        completed_installment = FixedExpense(
            id=uuid.uuid4(),
            user_id=user_id,
            name="Cicilan Lunas",
            amount=Decimal("750000.00"),
            expense_type="INSTALLMENT",
            due_day_of_month=today.day,
            frequency="monthly",
            principal_amount=Decimal("4500000.00"),
            interest_type="zero",
            interest_rate=Decimal("0.00"),
            interest_rate_period="monthly",
            total_tenor=6,
            paid_installments=6,
            is_paid_this_cycle=True,
            created_at=datetime.now(timezone.utc),
        )

        # 1. Uji Summary
        summary_session = AsyncMock()
        summary_session.exec = AsyncMock(
            side_effect=[
                FakeResult([plan]),                                    # get_or_create_financial_plan
                FakeResult([op_wallet]),                               # wallets
                FakeResult([]),                                        # income_streams
                FakeResult([active_installment, completed_installment]),  # fixed_expenses
                FakeResult([]),                                        # today transactions
                FakeResult([]),                                        # month transactions
            ]
        )
        summary = await ForecastService.get_forecast_summary(summary_session, user_id)
        self.assertEqual(summary.fixed_obligations.total_monthly_fixed, Decimal("500000.00"))
        self.assertEqual(summary.fixed_obligations.unpaid_fixed_buffer, Decimal("500000.00"))

        # 2. Uji Range Projection selama 150 hari (sekitar 5 bulan) -> Cicilan HP hanya muncul tepat 2x
        proj_session = AsyncMock()
        proj_session.exec = AsyncMock(
            side_effect=[
                FakeResult([plan]),                                    # get_or_create_financial_plan
                FakeResult([op_wallet]),                               # wallets
                FakeResult([]),                                        # income_streams
                FakeResult([active_installment, completed_installment]),  # fixed_expenses
                FakeResult([]),                                        # planned_transactions
                FakeResult([]),                                        # today transactions
            ]
        )
        req = RangeProjectionRequest(
            start_date=today,
            end_date=today + timedelta(days=150),
            wallet_filter="all_operational",
            include_daily_meal=False,
            include_daily_savings=False,
        )
        proj = await ForecastService.calculate_range_projection(proj_session, user_id, req)
        installment_events = [
            ev for day_item in proj.timeline for ev in day_item.events if ev.type == "INSTALLMENT"
        ]
        self.assertEqual(len(installment_events), 2)
        self.assertEqual([ev.name for ev in installment_events], ["Cicilan HP (5/6)", "Cicilan HP (6/6)"])
        self.assertEqual(proj.total_outflow, Decimal("1000000.00"))


if __name__ == "__main__":
    unittest.main()
