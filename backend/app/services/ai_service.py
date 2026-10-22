import asyncio
import io
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from groq import AsyncGroq
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from sqlalchemy import extract, func, or_
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.models.ai_chat_log import AIChatLog
from app.models.budget import Budget
from app.models.category import Category
from app.models.enums import CategoryType, ChatPlatform, ChatRole, TransactionSource, TransactionType, WalletType
from app.models.transaction import Transaction
from app.models.wallet import Wallet
from app.schemas.ai import (
    AIBudgetRequest,
    AIBudgetResponse,
    AIChatResponse,
    AIVoiceResponse,
    BudgetAllocationItem,
    LLMBudgetItem,
    LLMBudgetPlan,
    LLMIntentDecision,
    LLMQueryExtraction,
    LLMTransactionExtraction,
    LLMWalletCreation,
)
from app.schemas.transaction import TransactionCreate, TransactionResponse
from app.services.transaction_service import TransactionService


class AIService:
    @staticmethod
    def _get_llm(temperature: float = 0.1) -> Optional[ChatGoogleGenerativeAI]:
        """Inisialisasi LLM Gemini jika API Key tersedia."""
        if not settings.GEMINI_API_KEY:
            return None
        return ChatGoogleGenerativeAI(
            model="gemini-flash-latest",
            google_api_key=settings.GEMINI_API_KEY,
            temperature=temperature,
            request_timeout=3.0,
        )

    # ==========================================================================
    # 1. Speech-to-Text: Groq Whisper API (whisper-large-v3-turbo)
    # ==========================================================================
    @staticmethod
    async def transcribe_audio(
        file_bytes: bytes,
        filename: str = "audio.webm",
    ) -> str:
        """
        Mengirim file audio ke Groq Whisper API (whisper-large-v3-turbo)
        dengan konfigurasi bahasa Indonesia ('id').
        """
        if not settings.GROQ_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="GROQ_API_KEY belum dikonfigurasi di file .env server.",
            )

        if len(file_bytes) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File audio kosong atau tidak terbaca.",
            )

        client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        audio_buffer = io.BytesIO(file_bytes)
        audio_buffer.name = filename

        try:
            transcription = await client.audio.transcriptions.create(
                file=(filename, audio_buffer.read()),
                model="whisper-large-v3-turbo",
                language="id",
                response_format="json",
            )
            clean_text = transcription.text.strip()
            if not clean_text:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Audio berhasil diproses tetapi tidak ada suara/kata yang terdeteksi.",
                )
            return clean_text
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Gagal melakukan transkripsi suara dengan Groq Whisper: {str(e)}",
            )

    # ==========================================================================
    # 2. Natural Language Processing: Intent Classification & Processing
    # ==========================================================================
    @staticmethod
    async def process_chat_message(
        session: AsyncSession,
        user_id: uuid.UUID,
        message: str,
        platform: ChatPlatform = ChatPlatform.WEB,
        source: TransactionSource = TransactionSource.AI_CHAT,
    ) -> AIChatResponse:
        """
        Memproses teks obrolan pengguna:
        - Catat pesan user ke ai_chat_logs
        - Ambil daftar dompet & kategori aktif milik user
        - Gunakan Gemini Structured Outputs (Pydantic) untuk klasifikasi intent
        - Jalankan aksi: Catat Transaksi (Atomic Ledger) ATAU Kueri Data Finansial (Q&A)
        - Catat balasan AI ke ai_chat_logs dan kembalikan respons terstruktur
        """
        clean_msg = message.strip()

        # 1. Ambil daftar dompet dan kategori milik user
        wallets_query = select(Wallet).where(Wallet.user_id == user_id)
        wallets = (await session.exec(wallets_query)).all()
        wallet_names = [w.name for w in wallets]

        categories_query = select(Category).where(
            or_(Category.user_id == user_id, Category.user_id.is_(None))
        )
        categories = (await session.exec(categories_query)).all()
        category_names = [c.name for c in categories]

        # 2. Klasifikasi Intent: Jalankan Heuristic Cepat Terlebih Dahulu (< 1 ms)!
        decision = AIService._heuristic_fallback_classifier(clean_msg, wallet_names, category_names)

        # Jika bukan transaksi atau pertanyaan yang jelas dari pola heuristik, baru konsultasi ke LLM Gemini
        if decision.intent == "general":
            decision = await AIService._classify_intent_with_llm(
                message=clean_msg,
                wallet_names=wallet_names,
                category_names=category_names,
            )

        # 3. Simpan pesan User ke riwayat chat log (tanpa flush prematur agar koneksi DB tidak terkunci)
        user_log = AIChatLog(
            user_id=user_id,
            platform=platform,
            role=ChatRole.USER,
            message=clean_msg,
        )
        session.add(user_log)

        reply_text = ""
        tx_response: Optional[TransactionResponse] = None
        tx_list_responses: List[TransactionResponse] = []
        budget_alert = None
        extracted_meta = decision.model_dump(mode="json")

        # Kumpulkan daftar transaksi (bisa 1 atau banyak item)
        tx_items: List[LLMTransactionExtraction] = []
        if decision.intent == "transaction":
            if decision.transactions and len(decision.transactions) > 0:
                tx_items = [t for t in decision.transactions if t.amount]
            elif decision.transaction_data and decision.transaction_data.amount:
                tx_items = [decision.transaction_data]

        # 4. Tangani Berdasarkan Niat (Intent)
        if decision.intent == "transaction" and tx_items:
            # === AKSI: PENCATATAN TRANSAKSI OTOMATIS (MENDUKUNG SINGLE / BANYAK TRANSAKSI SEKALIGUS) ===
            recorded_txs: List[TransactionResponse] = []
            alerts: List[str] = []
            summary_lines: List[str] = []

            for tx_data in tx_items:
                matched_wallet = AIService._match_wallet(tx_data.wallet_name, wallets)
                matched_category = AIService._match_category(tx_data.category_name, categories, tx_data.type)

                if not matched_wallet:
                    summary_lines.append(f"❌ Nominal Rp{tx_data.amount:,.0f} gagal dicatat: Anda belum memiliki dompet aktif.")
                    continue
                if not matched_category:
                    summary_lines.append(f"❌ Nominal Rp{tx_data.amount:,.0f} gagal dicatat: Kategori tidak sesuai.")
                    continue

                dest_wallet_id = None
                matched_dest_wallet = None
                if tx_data.type == TransactionType.TRANSFER:
                    if tx_data.destination_wallet_name:
                        matched_dest_wallet = AIService._match_wallet(tx_data.destination_wallet_name, wallets)
                    if not matched_dest_wallet or matched_dest_wallet.id == matched_wallet.id:
                        other_w = [w for w in wallets if w.id != matched_wallet.id]
                        if other_w:
                            matched_dest_wallet = other_w[0]

                    if not matched_dest_wallet:
                        summary_lines.append(f"❌ Transfer Rp{tx_data.amount:,.0f} gagal dicatat: Anda membutuhkan minimal 2 dompet aktif untuk transfer saldo.")
                        continue
                    dest_wallet_id = matched_dest_wallet.id

                # Format deskripsi transaksi yang ringkas & rapi
                if tx_data.type == TransactionType.TRANSFER and matched_dest_wallet:
                    amt = tx_data.amount
                    if amt >= 1000000 and amt % 1000000 == 0:
                        amt_lbl = f"{int(amt // 1000000)}jt"
                    elif amt >= 1000 and amt % 1000 == 0:
                        amt_lbl = f"{int(amt // 1000)}rb"
                    else:
                        amt_lbl = f"Rp{int(amt):,}".replace(",", ".")
                    final_desc = f"Transfer {amt_lbl} dari {matched_wallet.name} ke {matched_dest_wallet.name}"
                else:
                    raw_desc = tx_data.description or clean_msg
                    final_desc = AIService._clean_transaction_description(raw_desc, wallet_names, tx_data.type)

                tx_create_payload = TransactionCreate(
                    wallet_id=matched_wallet.id,
                    destination_wallet_id=dest_wallet_id,
                    category_id=matched_category.id,
                    amount=tx_data.amount,
                    type=tx_data.type,
                    description=final_desc,
                    transaction_date=date.today(),
                    source=source,
                )
                tx_result = await TransactionService.create_transaction(
                    session=session,
                    user_id=user_id,
                    payload=tx_create_payload,
                )
                recorded_txs.append(tx_result.transaction)
                if tx_result.budget_alert:
                    alerts.append(f"*{tx_result.budget_alert.message}*")

                if tx_data.type == TransactionType.TRANSFER and matched_dest_wallet:
                    summary_lines.append(
                        f"🔄 **Transfer** sebesar **Rp{tx_data.amount:,.0f}** dari dompet **{matched_wallet.name}** ke dompet **{matched_dest_wallet.name}**"
                    )
                else:
                    tipe_icon = "📈" if tx_data.type == TransactionType.INCOME else "📉"
                    tipe_str = "Pemasukan" if tx_data.type == TransactionType.INCOME else "Pengeluaran"
                    item_desc = f" ({final_desc})" if final_desc and final_desc.lower() != clean_msg.lower() else ""
                    summary_lines.append(
                        f"{tipe_icon} **{tipe_str}** sebesar **Rp{tx_data.amount:,.0f}** untuk kategori **{matched_category.name}**{item_desc} menggunakan dompet **{matched_wallet.name}**"
                    )

            tx_list_responses = recorded_txs
            if recorded_txs:
                if len(recorded_txs) == 1:
                    tx_response = recorded_txs[0]
                    reply_text = f"✅ Berhasil mencatat {summary_lines[0]}."
                else:
                    tx_response = recorded_txs[0]
                    reply_text = (
                        f"✅ Berhasil mencatat **{len(recorded_txs)} transaksi** sekaligus:\n"
                        + "\n".join([f"• {line}" for line in summary_lines])
                    )

                if alerts:
                    reply_text += "\n\n⚠️ " + "\n⚠️ ".join(alerts)
            else:
                reply_text = "Maaf, transaksi tidak dapat diproses karena tidak ditemukan dompet aktif atau kategori yang sesuai."

        elif decision.intent == "create_wallet" and decision.wallet_creation_data:
            # === AKSI: PENAMBAHAN DOMPET / REKENING BARU ===
            w_data = decision.wallet_creation_data
            wallet_name = w_data.name.strip()

            # Cek apakah dompet dengan nama ini sudah pernah dibuat (case-insensitive)
            existing_wallet = next(
                (w for w in wallets if w.name.strip().lower() == wallet_name.lower()),
                None,
            )
            if existing_wallet:
                reply_text = (
                    f"⚠️ Dompet **{existing_wallet.name}** sudah ada di akun Anda dengan saldo saat ini "
                    f"**Rp{existing_wallet.balance:,.0f}**.\n\n"
                    f"Jika ingin menambah atau memindahkan saldo, Anda bisa mencatat pemasukan atau transfer saldo antar dompet."
                )
            else:
                new_wallet = Wallet(
                    user_id=user_id,
                    name=wallet_name,
                    type=w_data.type,
                    balance=w_data.initial_balance or Decimal("0.00"),
                )
                session.add(new_wallet)
                await session.flush()
                await session.refresh(new_wallet)

                type_label = {
                    WalletType.CASH: "Tunai 💵",
                    WalletType.BANK: "Rekening Bank 🏦",
                    WalletType.EWALLET: "E-Wallet 📱",
                }.get(new_wallet.type, "Dompet")

                bal_str = f"Rp{new_wallet.balance:,.0f}" if new_wallet.balance else "Rp0"
                reply_text = (
                    f"🎉 **Dompet Baru Berhasil Dibuat!**\n\n"
                    f"• **Nama Dompet:** {new_wallet.name}\n"
                    f"• **Tipe:** {type_label}\n"
                    f"• **Saldo Awal:** {bal_str}\n\n"
                    f"Sekarang Anda dapat mencatat transaksi atau mentransfer saldo menggunakan dompet **{new_wallet.name}**! ✨"
                )

        elif decision.intent == "query" and decision.query_data:
            # === AKSI: Q&A DATA KEUANGAN PRIBADI ===
            reply_text = await AIService._execute_financial_query(
                session=session,
                user_id=user_id,
                query_data=decision.query_data,
                user_message=clean_msg,
                wallets=wallets,
                categories=categories,
            )

        else:
            # === AKSI: PERCAKAPAN UMUM / PANDUAN ===
            if decision.general_reply:
                reply_text = decision.general_reply
            else:
                reply_text = (
                    "Halo! Saya asisten keuangan cerdas FinAI Track. Anda bisa langsung mengetik atau mengirim rekaman suara "
                    "untuk mencatat transaksi (contoh: *'Beli nasi padang 25rb pakai Tunai'*) atau bertanya kondisi keuangan "
                    "(contoh: *'Berapa total pengeluaranku bulan ini?'*)."
                )

        # 5. Simpan balasan Asisten ke riwayat chat log
        assistant_log = AIChatLog(
            user_id=user_id,
            platform=platform,
            role=ChatRole.ASSISTANT,
            message=reply_text,
            extracted_metadata=extracted_meta,
        )
        session.add(assistant_log)
        await session.commit()

        return AIChatResponse(
            intent=decision.intent,
            reply=reply_text,
            extracted_data=extracted_meta,
            transaction=tx_response,
            transactions=tx_list_responses if len(tx_list_responses) > 1 else None,
            budget_alert=budget_alert,
        )

    # ==========================================================================
    # 3. AI Dynamic Budgeting: Generator Anggaran Otomatis
    # ==========================================================================
    @staticmethod
    async def generate_auto_budget(
        session: AsyncSession,
        user_id: uuid.UUID,
        payload: AIBudgetRequest,
    ) -> AIBudgetResponse:
        """
        Menghasilkan rekomendasi alokasi anggaran bulanan cerdas:
        - Membaca rata-rata historis pengeluaran user per kategori
        - Menerima constraint batasan/keinginan user via prompt
        - Menggunakan Gemini untuk menghasilkan alokasi seimbang per kategori
        - Opsi otomatis menyimpan langsung ke tabel budgets
        """
        target_month = payload.month or date.today().month
        target_year = payload.year or date.today().year

        # 1. Ambil kategori pengeluaran milik user
        cat_query = select(Category).where(
            or_(Category.user_id == user_id, Category.user_id.is_(None)),
            Category.type == CategoryType.EXPENSE,
        )
        expense_cats = (await session.exec(cat_query)).all()
        if not expense_cats:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Belum ada kategori pengeluaran yang terdaftar.",
            )

        # 2. Hitung rata-rata pengeluaran historis 3 bulan terakhir per kategori
        cat_histories = {}
        three_months_ago = date.today() - timedelta(days=90)
        for cat in expense_cats:
            spent_query = select(func.coalesce(func.sum(Transaction.amount), Decimal("0.00"))).where(
                Transaction.user_id == user_id,
                Transaction.category_id == cat.id,
                Transaction.type == TransactionType.EXPENSE,
                Transaction.transaction_date >= three_months_ago,
            )
            total_past_90d: Decimal = (await session.exec(spent_query)).one()
            # Estimasi pengeluaran per bulan
            monthly_avg = round(total_past_90d / Decimal("3.0"), 2)
            cat_histories[cat.name] = {
                "id": cat.id,
                "monthly_avg": monthly_avg,
            }

        # 3. Hubungi Gemini LLM untuk menyusun draf alokasi anggaran
        budget_plan = await AIService._generate_budget_plan_llm(
            user_prompt=payload.prompt,
            cat_histories=cat_histories,
        )

        # 4. Petakan hasil LLM ke kategori dan siapkan output
        allocations: List[BudgetAllocationItem] = []
        for item in budget_plan.allocations:
            matched_cat = next(
                (c for c in expense_cats if c.name.lower() == item.category_name.lower()),
                None,
            )
            if not matched_cat:
                continue

            hist_avg = cat_histories.get(matched_cat.name, {}).get("monthly_avg", Decimal("0.00"))
            allocations.append(
                BudgetAllocationItem(
                    category_id=matched_cat.id,
                    category_name=matched_cat.name,
                    suggested_limit=item.suggested_limit,
                    historical_average=hist_avg,
                    reasoning=item.reasoning,
                )
            )

        # 5. Jika apply_to_database=True, simpan atau perbarui tabel budgets
        saved = False
        if payload.apply_to_database and allocations:
            for alloc in allocations:
                # Cek existing budget
                b_query = select(Budget).where(
                    Budget.user_id == user_id,
                    Budget.category_id == alloc.category_id,
                    Budget.month == target_month,
                    Budget.year == target_year,
                )
                b_existing = (await session.exec(b_query)).first()
                if b_existing:
                    b_existing.amount_limit = alloc.suggested_limit
                    b_existing.is_ai_generated = True
                    session.add(b_existing)
                else:
                    new_b = Budget(
                        user_id=user_id,
                        category_id=alloc.category_id,
                        amount_limit=alloc.suggested_limit,
                        month=target_month,
                        year=target_year,
                        is_ai_generated=True,
                    )
                    session.add(new_b)
            await session.commit()
            saved = True

        return AIBudgetResponse(
            total_budget=budget_plan.total_budget,
            allocations=allocations,
            strategy_summary=budget_plan.strategy_summary,
            saved_to_database=saved,
        )

    # ==========================================================================
    # Helper Methods: Intent Classification & Entity Matching
    # ==========================================================================
    @staticmethod
    async def _classify_intent_with_llm(
        message: str,
        wallet_names: List[str],
        category_names: List[str],
    ) -> LLMIntentDecision:
        """Memanggil Gemini Structured Outputs untuk membedakan Niat Transaksi vs Pertanyaan Data."""
        llm = AIService._get_llm(temperature=0.0)

        # Fallback jika GEMINI_API_KEY belum dipasang
        if not llm:
            return AIService._heuristic_fallback_classifier(message, wallet_names, category_names)

        system_instruction = f"""
Kamu adalah AI Parsing Engine cerdas untuk aplikasi keuangan 'FinAI Track'.
Analisis pesan bahasa Indonesia dari pengguna secara teliti dan akurat:

1. Jika pengguna berniat MENCATAT TRANSAKSI (Pengeluaran, Pemasukan, atau Pemindahan Saldo):
   - Tetapkan intent = "transaction"
   - CATATAN PENTING: Pengguna dapat menyebutkan SATU atau LEBIH transaksi sekaligus dalam satu kalimat!
     Contoh: "beli kopi 5rb, dapet uang saku 10rb, makan siang 15rb" -> terdapat 3 transaksi!
     Contoh: "ibu kasih 10rb, bapak 10rb lalu saya beli mainan 10rb" -> terdapat 3 transaksi:
       1) "ibu kasih 10rb" -> type: "income", category_name: "Uang Saku", amount: 10000
       2) "bapak 10rb" -> type: "income", category_name: "Uang Saku", amount: 10000
       3) "saya beli mainan 10rb" -> type: "expense", category_name: "Belanja", amount: 10000
   - Ekstrak seluruh transaksi ke dalam daftar `transactions`:
     Untuk setiap item transaksi:
     * amount: nominal angka uang (contoh: '5rb' -> 5000, '10rb' -> 10000, '25rb' -> 25000, '50k' -> 50000, '100rb' -> 100000, '1.5jt' -> 1500000, 'dua puluh ribu' -> 20000).
     * type:
       - 'income' jika konteksnya adalah uang masuk atau pemberian uang saku/nafkah/hadiah dari keluarga atau pihak lain (contoh: dapat/dapet uang saku, sangu, ibu kasih, bapak ngasih, bapak 10rb, dikasih mama, terima gaji, bonus, dapat hadiah, cair, untung penjualan, piutang dibayar, dll). Jika ada penyebutan anggota keluarga memberi uang ("ibu kasih 10rb", "bapak 10rb", "dikasih mama 20rb"), ini adalah PEMASUKAN dengan kategori 'Uang Saku'.
       - 'expense' jika konteksnya uang keluar / belanja / biaya / beli (contoh: beli kopi, makan siang, jajan, mainan, bayar tagihan, pulsa, bensin, belanja baju, parfum, dll).
       - 'transfer' jika memindahkan saldo antar dompet, top up e-wallet, atau tarik tunai (contoh: "transfer 100rb dari tunai ke gopay", "saya mindahin uang tunai 100rb ke dompay gopay", "top up gopay 50rb dari tunai", "mindahin 50rb ke gopay").
     * category_name: pilih nama kategori yang paling relevan dari daftar: {category_names}
       - PERHATIAN KERAS: Jika type = 'income', WAJIB pilih kategori pemasukan (seperti 'Uang Saku', 'Gaji', 'Bonus & Freelance', 'Investasi', atau 'Lain-lain'). JANGAN PERNAH memilih kategori pengeluaran seperti 'Makanan & Minuman' untuk uang masuk!
       - Jika transaksi berasal dari orang tua / keluarga (ibu, bapak, ayah, mama, ortu) atau uang saku / sangu, pilih kategori 'Uang Saku'.
       - Jika type = 'expense', pilih kategori pengeluaran yang tepat ('Makanan & Minuman', 'Transportasi', 'Belanja', 'Tagihan & Utilitas', 'Hiburan', 'Kesehatan', dll). Mainan, pakaian, gadget, parfum masuk ke 'Belanja'.
       - Jika type = 'transfer', pilih kategori 'Lain-lain'.
     * wallet_name: dompet asal / pengirim dari {wallet_names} (default ke 'Tunai' jika tidak disebutkan).
     * destination_wallet_name: khusus transfer, dompet tujuan / penerima dari {wallet_names}.
     * description: deskripsi singkat transaksi yang ringkas dan padat.
       PERHATIAN KERAS: JANGAN mencantumkan nama dompet atau metode pembayaran di description!
       Keterangan dompet sudah otomatis dicatat pada atribut wallet_name.
       Contoh: jika user chat "kopi 50rb dari dompet gopay", description adalah "Kopi 50rb" (BUKAN "Kopi 50rb dari dompet gopay").
       Contoh: "beli bensin 20rb pakai tunai" -> description: "Beli bensin 20rb".
       Contoh: "makan siang 25rb lewat bca" -> description: "Makan siang 25rb".
       KECUALI untuk transfer antar dompet, format deskripsi: "Transfer <nominal> dari <asal> ke <tujuan>".
   - Jika hanya ada 1 transaksi, isi juga `transaction_data` dengan data yang sama persis.

2. Jika pengguna berniat MENAMBAH / MEMBUAT DOMPET ATAU REKENING BARU:
   - Tetapkan intent = "create_wallet"
   - Ekstrak ke `wallet_creation_data`:
     * name: nama dompet atau rekening (contoh: "BCA", "Bank Jago", "OVO", "GoPay", "Tunai Cadangan")
     * type: 'bank' jika rekening bank, 'ewallet' jika dompet digital (gopay, ovo, dana, shopeepay, linkaja), atau 'cash' jika uang tunai.
     * initial_balance: nominal saldo awal angka (contoh: '1jt' -> 1000000, '50rb' -> 50000, default 0 jika tidak ada).

3. Jika pengguna BERTANYA TENTANG DATA KEUANGAN / SALDO / ANGGARAN:
   - Tetapkan intent = "query"
   - Tentukan query_type:
     * 'balance_check' jika menanyakan sisa uang / saldo (misal: "Saldo BCA berapa?", "Total uangku berapa?")
     * 'total_expense' jika menanyakan pengeluaran (misal: "Pengeluaran bulan ini berapa?")
     * 'total_income' jika menanyakan pemasukan (misal: "Pemasukan bulan ini berapa?")
     * 'category_spending' jika menanyakan pengeluaran kategori tertentu (misal: "Habis berapa buat makan?")
     * 'budget_status' jika menanyakan kondisi anggaran (misal: "Budget makan masih aman?")
     * 'general_summary' jika meminta ringkasan menyeluruh keuangan.

4. Jika pesan adalah sapaan umum atau pertanyaan non-keuangan:
   - Tetapkan intent = "general"
   - Buatkan pesan general_reply yang ramah dan membantu.
"""
        structured_llm = llm.with_structured_output(LLMIntentDecision)
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    structured_llm.invoke,
                    [
                        SystemMessage(content=system_instruction),
                        HumanMessage(content=message),
                    ],
                ),
                timeout=5.0,
            )
            return result
        except Exception:
            # Fallback ke pencarian pola heuristik jika terjadi limit kuota atau kesalahan API
            return AIService._heuristic_fallback_classifier(message, wallet_names, category_names)

    @staticmethod
    def _heuristic_fallback_classifier(
        message: str,
        wallet_names: List[str],
        category_names: List[str],
    ) -> LLMIntentDecision:
        """Pencocokan aturan berbasis Regex & Kata Kunci sebagai fallback andal untuk single & multi transaksi."""
        lower = message.lower()

        # 1. Deteksi Buat / Tambah Dompet Baru
        wallet_creation_triggers = [
            "/tambah_dompet", "/tambahdompet", "tambah_dompet",
            "tambah dompet", "buat dompet", "bikin dompet",
            "tambah rekening", "buat rekening", "bikin rekening",
            "tambah akun", "buka rekening", "tambah ewallet", "tambah e-wallet",
        ]
        if any(trig in lower for trig in wallet_creation_triggers):
            amt = Decimal("0.00")
            match_jt = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:jt|juta)", lower)
            match_rb = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:rb|ribu|k)", lower)
            match_num = re.search(r"(?:rp\.?\s*)?(\d{1,3}(?:\.\d{3})+|\d{4,9})", lower)
            if match_jt:
                val = float(match_jt.group(1).replace(",", "."))
                amt = Decimal(str(int(val * 1000000)))
            elif match_rb:
                val = float(match_rb.group(1).replace(",", "."))
                amt = Decimal(str(int(val * 1000)))
            elif match_num:
                raw_n = match_num.group(1).replace(".", "")
                amt = Decimal(raw_n)

            bank_names = ["bca", "mandiri", "bri", "bni", "cimb", "jago", "seabank", "permata", "btn", "bsi", "panin", "jenius", "bank", "rekening"]
            ewallet_names = ["gopay", "ovo", "dana", "shopeepay", "shopee pay", "linkaja", "ewallet", "e-wallet"]

            if any(bn in lower for bn in bank_names):
                w_type = WalletType.BANK
            elif any(en in lower for en in ewallet_names):
                w_type = WalletType.EWALLET
            else:
                w_type = WalletType.CASH

            # Bersihkan nama dompet dari kata perintah, imbuhan saldo, dan nominal
            cleaned_name = re.sub(
                r"^(?:/tambah_dompet|/tambahdompet|tambah_dompet|tambah\s+dompet|buat\s+dompet|bikin\s+dompet|tambah\s+rekening|buat\s+rekening|bikin\s+rekening|buka\s+rekening|tambah\s+akun|tambah\s+ewallet|tambah\s+e-wallet)\s*",
                "",
                message,
                flags=re.IGNORECASE,
            ).strip()

            cleaned_name = re.sub(r"^(?:baru|akun|tipe\s+\w+|rekening|dompet)\s+", "", cleaned_name, flags=re.IGNORECASE)
            cleaned_name = re.sub(
                r"(?:dengan\s+)?(?:saldo\s+(?:awal\s+)?)?(?:sebesar\s+)?(?:rp\.?\s*)?(?:\d+(?:[.,]\d+)?\s*(?:jt|juta|rb|ribu|k)|\d{1,3}(?:\.\d{3})+|\d+)",
                "",
                cleaned_name,
                flags=re.IGNORECASE,
            )
            cleaned_name = re.sub(r"\b(?:saldo|awal|sebesar|dengan|tipe|e-wallet|ewallet|bank)\b", "", cleaned_name, flags=re.IGNORECASE).strip()
            cleaned_name = re.sub(r"\s+", " ", cleaned_name).strip(" :-,.")

            if not cleaned_name:
                for bn in ["BCA", "Mandiri", "BRI", "BNI", "Bank Jago", "SeaBank", "CIMB Niaga", "Permata"]:
                    if bn.lower() in lower:
                        cleaned_name = bn
                        break
                if not cleaned_name:
                    for en in ["GoPay", "OVO", "DANA", "ShopeePay", "LinkAja"]:
                        if en.lower() in lower:
                            cleaned_name = en
                            break
                if not cleaned_name:
                    cleaned_name = "Dompet Baru"

            return LLMIntentDecision(
                intent="create_wallet",
                wallet_creation_data=LLMWalletCreation(
                    name=cleaned_name,
                    type=w_type,
                    initial_balance=amt,
                ),
            )

        # 2. Deteksi pertanyaan (Query)
        query_keywords = ["berapa", "apakah", "gimana", "bagaimana", "sisa saldo", "total", "cek", "aman tidak", "aman ga"]
        if any((kw in lower for kw in query_keywords)) and not re.search(r"\b(tadi|beli|bayar|transfer)\b", lower):
            q_type = "general_summary"
            if "saldo" in lower:
                q_type = "balance_check"
            elif "pengeluaran" in lower or "habis" in lower:
                q_type = "total_expense"
            elif "pemasukan" in lower or "gaji" in lower:
                q_type = "total_income"
            elif "budget" in lower or "anggaran" in lower:
                q_type = "budget_status"

            return LLMIntentDecision(
                intent="query",
                query_data=LLMQueryExtraction(query_type=q_type, time_frame="this_month"),
            )

        # Helper untuk ekstrak 1 klausa transaksi
        def parse_single_clause(clause: str) -> Optional[LLMTransactionExtraction]:
            cl = clause.strip()
            if not cl:
                return None

            match_jt = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:jt|juta)", cl)
            match_rb = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:rb|ribu|k)", cl)
            match_num = re.search(r"(?:rp\.?\s*)?(\d{1,3}(?:\.\d{3})+|\d{4,9})", cl)

            amt = None
            if match_jt:
                val = float(match_jt.group(1).replace(",", "."))
                amt = Decimal(str(int(val * 1000000)))
            elif match_rb:
                val = float(match_rb.group(1).replace(",", "."))
                amt = Decimal(str(int(val * 1000)))
            elif match_num:
                raw_n = match_num.group(1).replace(".", "")
                amt = Decimal(raw_n)

            if not amt:
                return None

            # Format nominal ringkas (100rb, 1jt, dll)
            if amt >= 1000000 and amt % 1000000 == 0:
                amt_label = f"{int(amt // 1000000)}jt"
            elif amt >= 1000 and amt % 1000 == 0:
                amt_label = f"{int(amt // 1000)}rb"
            else:
                amt_label = f"Rp{int(amt):,}".replace(",", ".")

            # 1. Deteksi Transfer Antar Dompet / Top Up Saldo
            transfer_keywords = [
                "transfer", "tf", "mindahin", "pindahin", "pindah", "kirim uang",
                "top up", "topup", "isi saldo", "tarik tunai"
            ]
            is_transfer = any(re.search(r"\b" + tk + r"\b", cl) for tk in transfer_keywords) or any(
                tk in cl for tk in ["mindahin", "pindahin", "top up", "topup", "tarik tunai", "isi saldo"]
            )

            if is_transfer:
                source_w = None
                dest_w = None

                topup_match = re.search(r"\b(?:top\s*up|isi\s+saldo|isi)\b\s+(?:dompet\s+|dompay\s+|rekening\s+)?([a-zA-Z0-9_-]+)", cl)
                if topup_match:
                    target_word = topup_match.group(1).lower()
                    for w in wallet_names:
                        if w.lower() in target_word or target_word in w.lower():
                            dest_w = w
                            break

                ke_match = re.search(r"\bke\b\s+(?:dompet\s+|dompay\s+|rekening\s+)?([a-zA-Z0-9_-]+)", cl)
                if ke_match:
                    target_word = ke_match.group(1).lower()
                    for w in wallet_names:
                        if w.lower() in target_word or target_word in w.lower():
                            dest_w = w
                            break

                dari_match = re.search(r"\b(?:dari|pakai|menggunakan|lewat)\b\s+(?:dompet\s+|dompay\s+|rekening\s+)?([a-zA-Z0-9_-]+)", cl)
                if dari_match:
                    source_word = dari_match.group(1).lower()
                    for w in wallet_names:
                        if w.lower() in source_word or source_word in w.lower():
                            source_w = w
                            break

                if not source_w or not dest_w:
                    found_wallets = []
                    for w in wallet_names:
                        idx = cl.find(w.lower())
                        if idx != -1:
                            found_wallets.append((idx, w))
                    found_wallets.sort(key=lambda x: x[0])

                    if not source_w and not dest_w and len(found_wallets) >= 2:
                        ke_pos = cl.find(" ke ")
                        if ke_pos != -1:
                            source_candidates = [w for idx, w in found_wallets if idx < ke_pos]
                            dest_candidates = [w for idx, w in found_wallets if idx > ke_pos]
                            if source_candidates and dest_candidates:
                                source_w = source_candidates[-1]
                                dest_w = dest_candidates[0]
                        else:
                            source_w = found_wallets[0][1]
                            dest_w = found_wallets[1][1]
                    elif dest_w and not source_w:
                        other = [w for w in wallet_names if w.lower() != dest_w.lower()]
                        source_w = other[0] if other else None
                    elif source_w and not dest_w:
                        other = [w for w in wallet_names if w.lower() != source_w.lower()]
                        dest_w = other[0] if other else None

                src_name = source_w.capitalize() if source_w else (wallet_names[0] if wallet_names else "Tunai")
                dst_name = dest_w.capitalize() if dest_w else (wallet_names[1] if len(wallet_names) > 1 else "E-Wallet")
                desc = f"Transfer {amt_label} dari {src_name} ke {dst_name}"

                return LLMTransactionExtraction(
                    amount=amt,
                    type=TransactionType.TRANSFER,
                    category_name="Lain-lain",
                    wallet_name=source_w or (wallet_names[0] if wallet_names else "Tunai"),
                    destination_wallet_name=dest_w or (wallet_names[1] if len(wallet_names) > 1 else None),
                    description=desc,
                )

            # 2. Deteksi kata kunci keluarga / pemberi uang
            family_words = [
                "ibu", "bapak", "ayah", "mama", "papa", "ortu", "orang tua", "om", "tante",
                "paman", "nenek", "kakek", "kakak", "abang", "mas", "mbak", "umi", "abi"
            ]
            spending_words = [
                "beli", "bayar", "jajan", "ongkos", "belanja", "checkout", "co", "sewa",
                "tagihan", "pulsa", "bensin", "parkir", "traktir", "pesan", "order"
            ]

            # Kata kunci eksplisit pemasukan
            income_keywords = [
                "gaji", "terima", "dapat", "dapet", "bonus", "pemasukan", "saku", "uang saku", "sangu",
                "cair", "dikasih", "kasih", "ngasih", "diberi", "memberi", "tf masuk", "transfer masuk",
                "penjualan", "upah", "untung", "angpao", "hadiah", "hibah", "infaq terima", "kiriman",
                "transferan", "dikirimi", "dikirim", "uang jajan"
            ]

            has_family = any(re.search(r"\b" + fw + r"\b", cl) for fw in family_words)
            has_spending = any(re.search(r"\b" + sw + r"\b", cl) for sw in spending_words)
            has_income_kw = any(ik in cl for ik in income_keywords)

            # Jika klausa menyebutkan keluarga tanpa kata belanja ("ibu kasih 10rb", "bapak 10rb", "dikasih ibu") -> INCOME
            if (has_family and not has_spending) or has_income_kw:
                tx_t = TransactionType.INCOME
            else:
                tx_t = TransactionType.EXPENSE

            # Cocokkan dompet
            matched_w = None
            for w in wallet_names:
                if w.lower() in cl:
                    matched_w = w
                    break

            # Cocokkan kategori
            matched_c = None
            if tx_t == TransactionType.INCOME:
                if has_family or any(k in cl for k in ["saku", "sangu", "jajan", "kasih", "ngasih", "dikasih"]):
                    matched_c = "Uang Saku"
                elif "gaji" in cl or "salary" in cl:
                    matched_c = "Gaji"
                elif any(k in cl for k in ["bonus", "freelance", "proyek", "side job"]):
                    matched_c = "Bonus & Freelance"
                elif any(k in cl for k in ["investasi", "dividen", "saham", "crypto"]):
                    matched_c = "Investasi"
                else:
                    matched_c = "Uang Saku" if "Uang Saku" in category_names else "Lain-lain"
            else:
                if any(w in cl for w in ["kopi", "makan", "minum", "restoran", "kafe", "food", "sarapan", "lunch", "dinner", "jajan", "nasi", "ayam", "mie", "boba"]):
                    matched_c = "Makanan & Minuman"
                elif any(w in cl for w in ["bensin", "ojol", "grab", "gojek", "parkir", "tol", "transport"]):
                    matched_c = "Transportasi"
                elif any(w in cl for w in ["baju", "sepatu", "mainan", "game", "belanja", "shopee", "tokopedia", "beli", "parfum"]):
                    matched_c = "Belanja"
                elif any(w in cl for w in ["listrik", "air", "wifi", "pulsa", "tagihan", "kost", "kontrakan"]):
                    matched_c = "Tagihan & Utilitas"
                elif any(w in cl for w in ["nonton", "bioskop", "hiburan", "spotify", "netflix"]):
                    matched_c = "Hiburan"
                elif any(w in cl for w in ["obat", "dokter", "klinik", "apotek", "kesehatan"]):
                    matched_c = "Kesehatan"
                else:
                    matched_c = "Belanja" if "beli" in cl else "Makanan & Minuman"

            desc = AIService._clean_transaction_description(cl, wallet_names, tx_t)
            if not desc:
                desc = cl.capitalize()

            return LLMTransactionExtraction(
                amount=amt,
                type=tx_t,
                category_name=matched_c,
                wallet_name=matched_w,
                description=desc,
            )

        # Coba pecah berdasarkan koma, kata hubung 'dan', 'terus', 'lalu', atau baris baru
        clauses = re.split(r"[,;\n]|\b(?:dan|terus|lalu|kemudian)\b", lower)
        parsed_items: List[LLMTransactionExtraction] = []
        for clause in clauses:
            item = parse_single_clause(clause)
            if item:
                parsed_items.append(item)

        if not parsed_items:
            # Coba parse pesan penuh secara langsung
            single = parse_single_clause(lower)
            if single:
                parsed_items.append(single)

        if parsed_items:
            return LLMIntentDecision(
                intent="transaction",
                transaction_data=parsed_items[0],
                transactions=parsed_items,
            )

        return LLMIntentDecision(
            intent="general",
            general_reply="Halo! Saya FinAI Track. Anda bisa mencatat pemasukan & pengeluaran sekaligus cukup dengan mengetik: 'beli kopi 5rb, dapet uang saku 10rb, makan siang 15rb' atau rekam suara Anda.",
        )

    @staticmethod
    def _clean_transaction_description(
        raw_desc: str,
        wallet_names: List[str],
        tx_type: TransactionType = TransactionType.EXPENSE,
    ) -> str:
        """Membersihkan frasa dompet/metode pembayaran dan kata pengisi percakapan agar deskripsi transaksi ringkas."""
        if not raw_desc:
            return ""
        d = raw_desc.strip()

        # 1. Hapus conversational prefixes
        d = re.sub(
            r"^(?:tadi\s+|saya\s+|aku\s+|tolong\s+|catat\s+|catatkan\s+|uang\s+nya\s+saya\s+|uangnya\s+saya\s+|uangnya\s+buat\s+|uang\s+buat\s+)",
            "",
            d,
            flags=re.IGNORECASE,
        )

        # 2. Hapus frase dompet / metode pembayaran (e.g. 'dari dompet gopay', 'pakai tunai', 'lewat bca', 'via ovo', 'ke dompet gopay')
        w_escaped = [re.escape(w.lower()) for w in wallet_names if w]
        common_wallets = ["tunai", "cash", "gopay", "ovo", "dana", "bca", "bri", "bni", "mandiri", "shopeepay", "seabank", "jago", "jenius"]
        all_wallets = list(set(w_escaped + common_wallets))
        wallet_pattern = "|".join(all_wallets)

        # Pola preposisi dompet: (dari|ke|pakai|pake|lewat|via|menggunakan|dg|dengan) (dompet|dompay|rekening|akun)? (nama_dompet)
        d = re.sub(
            r"\b(?:dari|ke|pakai|pake|lewat|via|menggunakan|dg|dengan)\s+(?:dompet\s+|dompay\s+|rekening\s+|akun\s+)?(?:" + wallet_pattern + r")\b",
            "",
            d,
            flags=re.IGNORECASE,
        )

        # Pola uang masuk/cair ke dompet: (masuk\s+ke|masuk|ditransfer\s+ke|cair\s+ke) (dompet)? (nama_dompet)
        d = re.sub(
            r"\b(?:masuk\s+ke|masuk|ditransfer\s+ke|cair\s+ke)\s+(?:dompet\s+|dompay\s+|rekening\s+|akun\s+)?(?:" + wallet_pattern + r")\b",
            "",
            d,
            flags=re.IGNORECASE,
        )

        # Pola generik: (dari|ke|pakai|pake|lewat|via|menggunakan|dg|dengan) (dompet|dompay|rekening|akun) <kata_apapun>
        d = re.sub(
            r"\b(?:dari|ke|pakai|pake|lewat|via|menggunakan|dg|dengan)\s+(?:dompet|dompay|rekening|akun)\s+\w+\b",
            "",
            d,
            flags=re.IGNORECASE,
        )

        # 3. Hapus preposisi menggantung di akhir kalimat
        d = re.sub(r"\s+\b(?:dari|ke|pakai|pake|lewat|via|dengan|dg|buat)\b\s*$", "", d, flags=re.IGNORECASE)

        # 4. Normalisasi spasi ganda
        d = re.sub(r"\s+", " ", d).strip()

        return d.capitalize() if d else raw_desc.capitalize()

    @staticmethod
    def _match_wallet(name: Optional[str], wallets: List[Wallet]) -> Optional[Wallet]:
        if not wallets:
            return None
        if not name:
            # Utamakan dompet "Tunai" jika ada, atau dompet pertama
            return next((w for w in wallets if "tunai" in w.name.lower() or "cash" in w.name.lower()), wallets[0])
        name_lower = name.lower()
        return next((w for w in wallets if w.name.lower() in name_lower or name_lower in w.name.lower()), wallets[0])

    @staticmethod
    def _match_category(name: Optional[str], categories: List[Category], tx_type: TransactionType) -> Optional[Category]:
        if not categories:
            return None
        cats_of_type = [c for c in categories if c.type.value == tx_type.value]
        if not cats_of_type:
            cats_of_type = categories

        if not name:
            return cats_of_type[0]

        name_lower = name.lower()
        matched = next((c for c in cats_of_type if c.name.lower() in name_lower or name_lower in c.name.lower()), None)
        if matched:
            return matched

        # Jika nama tidak cocok, pilih default yang sesuai dengan jenis transaksi (bukan Makanan untuk Income)
        if tx_type == TransactionType.INCOME:
            return next((c for c in cats_of_type if "saku" in c.name.lower() or "gaji" in c.name.lower() or "lain" in c.name.lower()), cats_of_type[0])
        else:
            return next((c for c in cats_of_type if "makan" in c.name.lower() or "lain" in c.name.lower()), cats_of_type[0])

    # ==========================================================================
    # Helper Methods: Financial Query Execution
    # ==========================================================================
    @staticmethod
    async def _execute_financial_query(
        session: AsyncSession,
        user_id: uuid.UUID,
        query_data: LLMQueryExtraction,
        user_message: str,
        wallets: List[Wallet],
        categories: List[Category],
    ) -> str:
        """Eksekusi query analitik SQL dan susun jawaban naratif yang kaya informasi."""
        today = date.today()
        month = today.month
        year = today.year

        if query_data.query_type == "balance_check":
            total_bal = sum((w.balance for w in wallets), Decimal("0.00"))
            wallet_details = ", ".join([f"{w.name}: Rp{w.balance:,.0f}" for w in wallets])
            return f"💵 Total saldo gabungan Anda saat ini adalah **Rp{total_bal:,.0f}**.\n\nRincian per dompet: {wallet_details}."

        elif query_data.query_type == "total_expense":
            query = select(func.coalesce(func.sum(Transaction.amount), Decimal("0.00"))).where(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.EXPENSE,
                extract("month", Transaction.transaction_date) == month,
                extract("year", Transaction.transaction_date) == year,
            )
            total = (await session.exec(query)).one()
            return f"📉 Total pengeluaran Anda di bulan ini ({today.strftime('%B %Y')}) adalah sebesar **Rp{total:,.0f}**."

        elif query_data.query_type == "total_income":
            query = select(func.coalesce(func.sum(Transaction.amount), Decimal("0.00"))).where(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.INCOME,
                extract("month", Transaction.transaction_date) == month,
                extract("year", Transaction.transaction_date) == year,
            )
            total = (await session.exec(query)).one()
            return f"📈 Total pemasukan Anda di bulan ini ({today.strftime('%B %Y')}) adalah sebesar **Rp{total:,.0f}**."

        elif query_data.query_type in ["category_spending", "budget_status"]:
            # Cari kategori target jika ada
            target_cat = None
            if query_data.target_category:
                target_cat = next((c for c in categories if c.name.lower() in query_data.target_category.lower()), None)

            if target_cat:
                spent_query = select(func.coalesce(func.sum(Transaction.amount), Decimal("0.00"))).where(
                    Transaction.user_id == user_id,
                    Transaction.category_id == target_cat.id,
                    Transaction.type == TransactionType.EXPENSE,
                    extract("month", Transaction.transaction_date) == month,
                    extract("year", Transaction.transaction_date) == year,
                )
                spent = (await session.exec(spent_query)).one()

                budget_query = select(Budget).where(
                    Budget.user_id == user_id,
                    Budget.category_id == target_cat.id,
                    Budget.month == month,
                    Budget.year == year,
                )
                b_obj = (await session.exec(budget_query)).first()

                if b_obj:
                    pct = float((spent / b_obj.amount_limit) * Decimal("100.0")) if b_obj.amount_limit > 0 else 0.0
                    status_desc = "masih aman" if pct < 80 else ("sudah waspada" if pct < 100 else "sudah melebihi batas anggaran!")
                    return f"📊 Untuk kategori **{target_cat.name}** bulan ini, Anda telah membelanjakan **Rp{spent:,.0f}** dari batas anggaran **Rp{b_obj.amount_limit:,.0f}** ({pct:.1f}%). Kondisi saat ini {status_desc}."
                return f"📊 Total pengeluaran Anda untuk kategori **{target_cat.name}** bulan ini adalah **Rp{spent:,.0f}** (belum ada batas anggaran yang dipasang)."

        # Fallback ke ringkasan komprehensif
        summary = await TransactionService.get_dashboard_summary(session, user_id)
        return (
            f"📊 **Ringkasan Finansial Bulan Ini:**\n"
            f"• Pemasukan: Rp{summary.monthly_income:,.0f}\n"
            f"• Pengeluaran: Rp{summary.monthly_expense:,.0f}\n"
            f"• Arus Kas Bersih (Net): Rp{summary.net_cashflow:,.0f}\n"
            f"• Total Saldo Tersedia: Rp{summary.total_balance:,.0f}"
        )

    # ==========================================================================
    # Helper Methods: Budget Generation via LLM
    # ==========================================================================
    @staticmethod
    async def _generate_budget_plan_llm(
        user_prompt: str,
        cat_histories: Dict[str, Dict[str, Any]],
    ) -> LLMBudgetPlan:
        """Menyusun strategi alokasi anggaran dengan bantuan Gemini Structured Output."""
        llm = AIService._get_llm(temperature=0.2)

        history_context = "\n".join(
            [f"- {cat_name}: Rata-rata pengeluaran historis Rp{data['monthly_avg']:,.0f}/bulan" for cat_name, data in cat_histories.items()]
        )

        if not llm:
            # Fallback jika GEMINI_API_KEY belum disetel
            total_est = Decimal("5000000.00")
            num_cats = max(len(cat_histories), 1)
            allocations = []
            for cat_name, data in cat_histories.items():
                allocations.append(
                    LLMBudgetItem(
                        category_name=cat_name,
                        suggested_limit=data["monthly_avg"] if data["monthly_avg"] > 0 else Decimal("500000"),
                        reasoning="Disarankan berdasarkan pola historis pengeluaran.",
                    )
                )
            return LLMBudgetPlan(
                total_budget=total_est,
                allocations=allocations,
                strategy_summary="Alokasi anggaran dibuat proporsional berdasarkan rata-rata historis (Mode Fallback Offline).",
            )

        system_instruction = f"""
Kamu adalah Perencana Keuangan Pribadi (Certified Financial Planner) AI di 'FinAI Track'.
Tugasmu adalah menyusun alokasi anggaran bulanan per kategori pengeluaran berdasarkan:
1. Keinginan/batasan pengguna yang diuraikan dalam prompt.
2. Data historis rata-rata pengeluaran bulanan pengguna berikut:
{history_context}

Aturan:
- Sertakan seluruh kategori yang terdaftar dalam allocations.
- Berikan suggested_limit yang realistis dan rasional (angka kelipatan 50.000 atau 100.000 agar mudah diingat).
- Sertakan penjelasan reasoning singkat untuk setiap kategori.
- Berikan strategy_summary yang merangkum filosofi alokasi (misal metode 50/30/20 atau pengetatan pos tertentu).
"""
        structured_llm = llm.with_structured_output(LLMBudgetPlan)
        try:
            plan = await asyncio.to_thread(
                structured_llm.invoke,
                [
                    SystemMessage(content=system_instruction),
                    HumanMessage(content=f"Rancang anggaran bulanan dengan preferensi ini: {user_prompt}"),
                ]
            )
            return plan
        except Exception as e:
            # Fallback jika terjadi error pada model
            allocations = []
            for cat_name, data in cat_histories.items():
                allocations.append(
                    LLMBudgetItem(
                        category_name=cat_name,
                        suggested_limit=data["monthly_avg"] if data["monthly_avg"] > 0 else Decimal("500000"),
                        reasoning="Alokasi disesuaikan dengan data historis.",
                    )
                )
            return LLMBudgetPlan(
                total_budget=Decimal("5000000"),
                allocations=allocations,
                strategy_summary=f"Alokasi heuristik: {str(e)}",
            )
