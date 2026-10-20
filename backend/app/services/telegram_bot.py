import asyncio
import io
import logging
from typing import Optional

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from sqlmodel import select

from app.core.config import settings
from app.core.database import async_session_maker
from app.core.redis import verify_and_consume_telegram_otp
from app.models.enums import ChatPlatform, TransactionSource
from app.models.user import User
from app.services.ai_service import AIService

logger = logging.getLogger("finai.telegram_bot")

bot_router = Router()
telegram_bot: Optional[Bot] = None
telegram_dp: Optional[Dispatcher] = None
polling_task: Optional[asyncio.Task] = None


# ==============================================================================
# 1. Telegram Bot Handlers
# ==============================================================================

@bot_router.message(CommandStart())
async def handle_start(message: Message):
    """Menangani perintah /start dan deep link /start <kode_otp>."""
    # Cek apakah ada argumen kode OTP dari deep link (/start 123456)
    command_parts = (message.text or "").split()
    if len(command_parts) > 1:
        otp_code = command_parts[1].strip()
        await process_link_account(message, otp_code)
        return

    # Cek apakah user sudah terhubung
    async with async_session_maker() as session:
        stmt = select(User).where(User.telegram_chat_id == message.chat.id)
        user = (await session.exec(stmt)).first()

        if user:
            await message.reply(
                f"👋 Halo kembali, **{user.name}**!\n\n"
                "Akun FinAI Track Anda sudah terhubung. Anda bisa langsung:\n"
                "• Mengetik transaksi: _'Beli kopi 25rb pakai GoPay'_\n"
                "• Mengirim **Voice Note** rekaman suara\n"
                "• Bertanya kondisi saldo / pengeluaran\n\n"
                "Gunakan /help untuk panduan lebih lanjut.",
                parse_mode="Markdown",
            )
            return

    # Pesan petunjuk penautan akun baru
    welcome_msg = (
        "🤖 **Selamat Datang di FinAI Track Bot!**\n\n"
        "Asisten keuangan pribadi cerdas bertenaga AI. Untuk mulai mencatat keuangan via Telegram, "
        "tautkan akun Anda dengan langkah mudah berikut:\n\n"
        "1. Masuk ke **Web FinAI Track**\n"
        "2. Buka menu **Pengaturan** $\\rightarrow$ **Hubungkan ke Telegram**\n"
        "3. Dapatkan 6 digit kode OTP (berlaku 5 menit)\n"
        "4. Kirim perintah berikut ke bot ini:\n"
        "   `/link <kode_otp>`\n"
        "   _(Contoh: `/link 123456`)_\n\n"
        "Setelah terhubung, Anda bebas mencatat transaksi lewat teks kasual maupun suara! 🚀"
    )
    await message.reply(welcome_msg, parse_mode="Markdown")


@bot_router.message(Command("link"))
async def handle_link_command(message: Message):
    """Menangani perintah manual /link <kode_otp>."""
    parts = (message.text or "").split()
    if len(parts) < 2:
        await message.reply(
            "⚠️ Format perintah salah.\n\n"
            "Gunakan format: `/link <kode_otp_6_digit>`\n"
            "Contoh: `/link 123456`\n\n"
            "Dapatkan kode dari menu Pengaturan di Web FinAI Track.",
            parse_mode="Markdown",
        )
        return

    otp_code = parts[1].strip()
    await process_link_account(message, otp_code)


async def process_link_account(message: Message, otp_code: str):
    """Logika verifikasi OTP dari Redis dan penyimpanan telegram_chat_id ke DB."""
    user_id = await verify_and_consume_telegram_otp(otp_code)
    if not user_id:
        await message.reply(
            "❌ **Kode OTP Tidak Valid atau Telah Kedaluwarsa**\n\n"
            "Kode OTP hanya berlaku selama 5 menit. Silakan generate kode baru dari menu "
            "**Pengaturan** di Web FinAI Track lalu coba lagi.",
            parse_mode="Markdown",
        )
        return

    async with async_session_maker() as session:
        user = await session.get(User, user_id)
        if not user:
            await message.reply("❌ Akun pengguna tidak ditemukan di database.")
            return

        # Lepas tautan lama jika telegram_chat_id ini pernah dipakai akun lain
        existing_stmt = select(User).where(User.telegram_chat_id == message.chat.id)
        existing_user = (await session.exec(existing_stmt)).first()
        if existing_user and existing_user.id != user.id:
            existing_user.telegram_chat_id = None
            session.add(existing_user)

        # Simpan telegram_chat_id ke user saat ini
        user.telegram_chat_id = message.chat.id
        session.add(user)
        await session.commit()

        success_msg = (
            f"🎉 **Akun Berhasil Ditautkan!**\n\n"
            f"Halo **{user.name}**, akun FinAI Track Anda (`{user.email}`) kini telah aktif di bot ini.\n\n"
            "Sekarang Anda bisa langsung:\n"
            "• **Catat Pengeluaran:** _'Tadi beli makan 25rb Tunai'_\n"
            "• **Catat Pemasukan:** _'Gaji masuk 5jt ke BCA'_\n"
            "• **Kirim Voice Note:** Rekam suara Anda langsung di obrolan ini\n"
            "• **Tanya Saldo/Grafik:** _'Berapa sisa uangku sekarang?'_\n\n"
            "Semua transaksi otomatis tersinkronisasi ke Web Dashboard secara real-time! ✨"
        )
        await message.reply(success_msg, parse_mode="Markdown")


@bot_router.message(Command("unlink"))
async def handle_unlink(message: Message):
    """Menangani pemutusan tautan Telegram."""
    async with async_session_maker() as session:
        stmt = select(User).where(User.telegram_chat_id == message.chat.id)
        user = (await session.exec(stmt)).first()
        if not user:
            await message.reply("ℹ️ Akun Telegram ini belum terhubung dengan akun FinAI Track manapun.")
            return

        user.telegram_chat_id = None
        session.add(user)
        await session.commit()
        await message.reply("✅ Tautan akun Telegram berhasil diputus.")


@bot_router.message(F.voice | F.audio)
async def handle_voice_message(message: Message):
    """Menangani pesan Voice Note: unduh audio -> transcribe -> process AI -> balas ke Telegram."""
    async with async_session_maker() as session:
        # 1. Validasi Akun Terhubung
        stmt = select(User).where(User.telegram_chat_id == message.chat.id)
        user = (await session.exec(stmt)).first()
        if not user:
            await message.reply(
                "⚠️ Akun Telegram Anda belum terhubung.\n"
                "Kirim `/link <kode_otp>` terlebih dahulu untuk menautkan akun.",
                parse_mode="Markdown",
            )
            return

        # 2. Kirim indikator 'sedang merekam/mengetik'
        if message.bot:
            await message.bot.send_chat_action(chat_id=message.chat.id, action="record_voice")

        # 3. Unduh file audio dari Telegram
        voice = message.voice or message.audio
        if not voice or not message.bot:
            await message.reply("❌ Gagal membaca file suara.")
            return

        file_info = await message.bot.get_file(voice.file_id)
        if not file_info.file_path:
            await message.reply("❌ Gagal mengambil lokasi file suara dari server Telegram.")
            return

        audio_buffer = io.BytesIO()
        await message.bot.download_file(file_info.file_path, destination=audio_buffer)
        audio_bytes = audio_buffer.getvalue()

        # 4. Transkripsi suara dengan Groq Whisper API
        try:
            transcript = await AIService.transcribe_audio(
                file_bytes=audio_bytes,
                filename="voice.ogg",
            )
        except Exception as e:
            await message.reply(f"❌ Gagal memproses suara: {str(e)}")
            return

        # 5. Teruskan teks transkripsi ke AI Orchestrator
        if message.bot:
            await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

        chat_res = await AIService.process_chat_message(
            session=session,
            user_id=user.id,
            message=transcript,
            platform=ChatPlatform.TELEGRAM,
            source=TransactionSource.TELEGRAM_BOT,
        )

        response_text = (
            f"🎙️ *Transkripsi Suara:*\n_{transcript}_\n\n"
            f"{chat_res.reply}"
        )
        try:
            await message.reply(response_text, parse_mode="Markdown")
        except Exception:
            await message.reply(response_text)


@bot_router.message(F.text)
async def handle_text_message(message: Message):
    """Menangani pesan teks: teruskan ke AI Orchestrator -> balas ke Telegram."""
    clean_text = (message.text or "").strip()
    if not clean_text or clean_text.startswith("/"):
        return

    async with async_session_maker() as session:
        # 1. Validasi Akun Terhubung
        stmt = select(User).where(User.telegram_chat_id == message.chat.id)
        user = (await session.exec(stmt)).first()
        if not user:
            await message.reply(
                "⚠️ **Akun Anda belum terhubung.**\n\n"
                "Silakan buka Web FinAI Track, klik **Hubungkan ke Telegram** di menu Pengaturan, "
                "lalu kirim perintah:\n"
                "`/link <kode_otp_6_digit>`",
                parse_mode="Markdown",
            )
            return

        # 2. Indikator mengetik
        if message.bot:
            await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

        # 3. Proses pesan via AIService
        chat_res = await AIService.process_chat_message(
            session=session,
            user_id=user.id,
            message=clean_text,
            platform=ChatPlatform.TELEGRAM,
            source=TransactionSource.TELEGRAM_BOT,
        )

        try:
            await message.reply(chat_res.reply, parse_mode="Markdown")
        except Exception:
            await message.reply(chat_res.reply)


# ==============================================================================
# 2. Lifecycle Management (FastAPI Lifespan Integration)
# ==============================================================================

async def start_telegram_bot():
    """Memulai bot Telegram di background task dengan auto-reconnect tahan banting."""
    global telegram_bot, telegram_dp, polling_task

    token = settings.TELEGRAM_BOT_TOKEN
    if not token or token.strip() == "":
        logger.info("TELEGRAM_BOT_TOKEN belum disetel. Layanan bot Telegram dilewati.")
        return

    async def _polling_worker():
        global telegram_bot, telegram_dp
        while True:
            try:
                telegram_bot = Bot(token=token.strip())
                telegram_dp = Dispatcher()
                telegram_dp.include_router(bot_router)

                # Hapus webhook sebelumnya agar tidak bentrok dengan polling
                await telegram_bot.delete_webhook(drop_pending_updates=True)

                bot_info = await telegram_bot.get_me()
                print(f"🚀 [FinAI Bot] Berhasil aktif & polling: @{bot_info.username} (ID: {bot_info.id})", flush=True)
                logger.info(f"Bot Telegram berhasil aktif: @{bot_info.username} (ID: {bot_info.id})")

                await telegram_dp.start_polling(telegram_bot)
                break
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"⚠️ [FinAI Bot] Gagal inisialisasi ({e}), mencoba kembali dalam 5 detik...", flush=True)
                logger.warning(f"Koneksi Telegram bot gagal ({e}), retry dalam 5 detik...")
                await asyncio.sleep(5)

    polling_task = asyncio.create_task(_polling_worker())


async def stop_telegram_bot():
    """Menghentikan bot Telegram saat server FastAPI shutdown."""
    global telegram_bot, telegram_dp, polling_task

    if polling_task and not polling_task.done():
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass

    if telegram_bot:
        await telegram_bot.session.close()
        logger.info("Koneksi Bot Telegram ditutup dengan aman.")

