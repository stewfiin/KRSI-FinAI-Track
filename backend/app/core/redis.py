import secrets
import uuid
from typing import Optional
import redis.asyncio as aioredis

from app.core.config import settings

# Inisialisasi pool koneksi Redis asynchronous
redis_client: Optional[aioredis.Redis] = None


def get_redis() -> aioredis.Redis:
    """Mengambil atau menginisialisasi instance Redis client singleton."""
    global redis_client
    if redis_client is None:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )
    return redis_client


async def create_telegram_otp(user_id: uuid.UUID, ttl_seconds: int = 300) -> str:
    """
    Menghasilkan 6 digit kode OTP unik untuk pairing akun Telegram
    dan menyimpannya di Redis dengan masa berlaku 5 menit (300 detik).
    """
    r = get_redis()
    # Hasilkan 6 digit angka acak (100000 - 999999)
    code = str(secrets.randbelow(900000) + 100000)

    # Key format: tg_otp:<code> -> user_id
    key = f"tg_otp:{code}"
    await r.set(key, str(user_id), ex=ttl_seconds)

    # Simpan juga reverse key untuk tracking OTP aktif pengguna
    user_key = f"user_active_otp:{user_id}"
    await r.set(user_key, code, ex=ttl_seconds)

    return code


async def verify_and_consume_telegram_otp(code: str) -> Optional[uuid.UUID]:
    """
    Memvalidasi kode OTP Telegram dari Redis.
    Jika valid, kode langsung dihapus (single-use OTP) dan user_id dikembalikan.
    """
    r = get_redis()
    clean_code = code.strip()
    key = f"tg_otp:{clean_code}"

    user_id_str = await r.get(key)
    if not user_id_str:
        return None

    # Hapus OTP agar tidak bisa digunakan kembali
    await r.delete(key)
    await r.delete(f"user_active_otp:{user_id_str}")

    try:
        return uuid.UUID(user_id_str)
    except ValueError:
        return None

