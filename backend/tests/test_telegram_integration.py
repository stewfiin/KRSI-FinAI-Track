import asyncio
import json
import os
import sys
import urllib.error
import urllib.request
import uuid

# Pastikan root backend ada di sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from aiogram.types import Chat, Message, User as TgUser
from sqlmodel import select

from app.core.database import async_session_maker
from app.core.redis import get_redis
from app.models.ai_chat_log import AIChatLog
from app.models.enums import ChatPlatform, TransactionSource
from app.models.transaction import Transaction
from app.models.user import User
from app.services.telegram_bot import handle_link_command, handle_text_message


def request(url, method="GET", data=None, token=None):
    req_data = json.dumps(data).encode() if data else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        f"http://127.0.0.1:8000{url}", data=req_data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return (
                resp.status,
                json.loads(resp.read().decode()) if resp.status != 204 else None,
            )
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


async def run_telegram_tests():
    # 1. Login Web User
    status, res = request(
        "/api/v1/auth/login",
        "POST",
        {"email": "test@example.com", "password": "password123"},
    )
    assert status == 200, f"Login failed: {res}"
    token = res["access_token"]
    user_id = uuid.UUID(res["user"]["id"])
    print("[1] Auth Web OK")

    # 2. Check initial Telegram Status (Unlinked)
    status, stat_res = request("/api/v1/telegram/status", "GET", token=token)
    assert status == 200
    print(f"[2] Initial Telegram Status: is_linked={stat_res['is_linked']}")

    # 3. Generate 6-digit OTP pairing code via Web API
    status, otp_res = request("/api/v1/telegram/pairing-code", "POST", token=token)
    assert status == 201
    pairing_code = otp_res["pairing_code"]
    assert len(pairing_code) == 6
    print(f"[3] Generated OTP from Web API: {pairing_code}")

    # Check in Redis
    r = get_redis()
    stored_uid = await r.get(f"tg_otp:{pairing_code}")
    ttl = await r.ttl(f"tg_otp:{pairing_code}")
    assert stored_uid == str(user_id)
    assert 0 < ttl <= 300
    print(f"    -> Verified in Redis (TTL: {ttl}s)")

    # 4. Simulate Telegram User sending /link <pairing_code>
    simulated_chat_id = 998877665
    mock_msg = MagicMock(spec=Message)
    mock_msg.chat = MagicMock(spec=Chat)
    mock_msg.chat.id = simulated_chat_id
    mock_msg.from_user = MagicMock(spec=TgUser)
    mock_msg.from_user.id = simulated_chat_id
    mock_msg.from_user.first_name = "Dimas"
    mock_msg.text = f"/link {pairing_code}"
    mock_msg.reply = AsyncMock()

    await handle_link_command(mock_msg)
    assert mock_msg.reply.called
    reply_call = mock_msg.reply.call_args[0][0]
    print(f"[4] Telegram /link Command Executed.")
    assert "Akun Berhasil Ditautkan" in reply_call
    print("    -> Link Confirmation sent to Telegram user!")

    # Verify user in database has telegram_chat_id saved
    async with async_session_maker() as session:
        db_user = await session.get(User, user_id)
        assert db_user.telegram_chat_id == simulated_chat_id
        print(f"    -> PostgreSQL updated: telegram_chat_id = {db_user.telegram_chat_id}")

    # Verify OTP single-use consumption from Redis
    consumed = await r.get(f"tg_otp:{pairing_code}")
    assert consumed is None
    print("    -> OTP consumed and removed from Redis successfully.")

    # 5. Check Telegram Status API again (Linked)
    status, stat_res2 = request("/api/v1/telegram/status", "GET", token=token)
    assert status == 200
    assert stat_res2["is_linked"] is True
    assert stat_res2["telegram_chat_id"] == simulated_chat_id
    print(f"[5] Web API /telegram/status updated: is_linked={stat_res2['is_linked']}")

    # 6. Simulate Telegram User sending Casual Transaction Text: "Beli bensin 50rb pakai Tunai"
    mock_tx_msg = MagicMock(spec=Message)
    mock_tx_msg.chat = MagicMock(spec=Chat)
    mock_tx_msg.chat.id = simulated_chat_id
    mock_tx_msg.text = "Beli bensin 50rb pakai Tunai"
    mock_tx_msg.bot = MagicMock()
    mock_tx_msg.bot.send_chat_action = AsyncMock()
    mock_tx_msg.reply = AsyncMock()

    await handle_text_message(mock_tx_msg)
    assert mock_tx_msg.reply.called
    tx_reply = mock_tx_msg.reply.call_args[0][0]
    print(f"[6] Telegram Transaction Message Executed.")
    print(f"    Bot Reply: {tx_reply}")
    assert "Berhasil mencatat" in tx_reply or "Rp50,000" in tx_reply or "Tunai" in tx_reply

    # Verify transaction in DB has source == 'telegram_bot'
    async with async_session_maker() as session:
        tx_stmt = (
            select(Transaction)
            .where(
                Transaction.user_id == user_id,
                Transaction.source == TransactionSource.TELEGRAM_BOT,
            )
            .order_by(Transaction.created_at.desc())
        )
        saved_tx = (await session.exec(tx_stmt)).first()
        assert saved_tx is not None
        assert saved_tx.amount == Decimal("50000.00")
        print(f"    -> Transaction saved in PostgreSQL: Amount={saved_tx.amount}, Source={saved_tx.source.value}")

    # 7. Simulate Telegram Query Message: "Berapa total pengeluaranku bulan ini?"
    mock_q_msg = MagicMock(spec=Message)
    mock_q_msg.chat = MagicMock(spec=Chat)
    mock_q_msg.chat.id = simulated_chat_id
    mock_q_msg.text = "Berapa total pengeluaranku bulan ini?"
    mock_q_msg.bot = MagicMock()
    mock_q_msg.bot.send_chat_action = AsyncMock()
    mock_q_msg.reply = AsyncMock()

    await handle_text_message(mock_q_msg)
    assert mock_q_msg.reply.called
    q_reply = mock_q_msg.reply.call_args[0][0]
    print(f"[7] Telegram Q&A Message Executed.")
    print(f"    Bot Reply: {q_reply}")
    assert "pengeluaran" in q_reply.lower()

    # 8. Verify AI Chat Log records for Telegram platform
    async with async_session_maker() as session:
        log_stmt = (
            select(AIChatLog)
            .where(
                AIChatLog.user_id == user_id,
                AIChatLog.platform == ChatPlatform.TELEGRAM,
            )
        )
        tg_logs = (await session.exec(log_stmt)).all()
        assert len(tg_logs) >= 2
        print(f"[8] AI Chat Logs verified: {len(tg_logs)} entries recorded for Telegram.")

    print("\n>>> ALL TELEGRAM BOT INTEGRATION TESTS PASSED! <<<")


if __name__ == "__main__":
    asyncio.run(run_telegram_tests())
