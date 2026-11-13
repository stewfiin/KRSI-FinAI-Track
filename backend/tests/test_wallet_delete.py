import os
import sys
import types
import unittest
import uuid
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

from app.api.v1.wallets import delete_wallet
from app.models.enums import WalletType
from app.models.user import User
from app.models.wallet import Wallet


class _FakeExecResult:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class TestDeleteWalletRule(unittest.IsolatedAsyncioTestCase):
    async def test_cannot_delete_primary_tunai_wallet(self):
        user_id = uuid.uuid4()
        tunai = Wallet(id=uuid.uuid4(), user_id=user_id, name="Tunai", type=WalletType.CASH, balance=Decimal("100000.00"))
        bca = Wallet(id=uuid.uuid4(), user_id=user_id, name="BCA", type=WalletType.BANK, balance=Decimal("500000.00"))

        session = MagicMock()
        session.get = AsyncMock(return_value=tunai)
        session.exec = AsyncMock(return_value=_FakeExecResult([tunai, bca]))
        session.delete = AsyncMock()
        session.commit = AsyncMock()

        user = User(id=user_id, name="Tester", email="t@example.com", password_hash="x")

        with self.assertRaises(HTTPException) as ctx:
            await delete_wallet(wallet_id=tunai.id, current_user=user, session=session)

        self.assertEqual(ctx.exception.status_code, 400)
        session.delete.assert_not_called()

    async def test_cannot_delete_only_cash_wallet_even_if_renamed(self):
        user_id = uuid.uuid4()
        cash_w = Wallet(id=uuid.uuid4(), user_id=user_id, name="Dompet Saku", type=WalletType.CASH, balance=Decimal("50000.00"))
        bca = Wallet(id=uuid.uuid4(), user_id=user_id, name="BCA", type=WalletType.BANK, balance=Decimal("500000.00"))

        session = MagicMock()
        session.get = AsyncMock(return_value=cash_w)
        session.exec = AsyncMock(return_value=_FakeExecResult([cash_w, bca]))
        session.delete = AsyncMock()

        user = User(id=user_id, name="Tester", email="t@example.com", password_hash="x")

        with self.assertRaises(HTTPException) as ctx:
            await delete_wallet(wallet_id=cash_w.id, current_user=user, session=session)

        self.assertEqual(ctx.exception.status_code, 400)
        session.delete.assert_not_called()

    async def test_delete_bank_wallet_transfers_balance_to_tunai(self):
        user_id = uuid.uuid4()
        tunai = Wallet(id=uuid.uuid4(), user_id=user_id, name="Tunai", type=WalletType.CASH, balance=Decimal("100000.00"))
        bca = Wallet(id=uuid.uuid4(), user_id=user_id, name="BCA", type=WalletType.BANK, balance=Decimal("500000.00"))

        session = MagicMock()
        session.get = AsyncMock(return_value=bca)
        session.exec = AsyncMock(return_value=_FakeExecResult([tunai, bca]))
        session.add = MagicMock()
        session.delete = AsyncMock()
        session.commit = AsyncMock()

        user = User(id=user_id, name="Tester", email="t@example.com", password_hash="x")

        await delete_wallet(wallet_id=bca.id, current_user=user, session=session)

        self.assertEqual(tunai.balance, Decimal("600000.00"))
        session.delete.assert_awaited_once_with(bca)
        session.commit.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
