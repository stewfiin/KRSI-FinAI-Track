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
from app.models.enums import CategoryType, ChatPlatform, ChatRole, TransactionSource, TransactionType
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
            model="gemini-2.5-flash",
            google_api_key=settings.GEMINI_API_KEY,
            temperature=temperature,
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

        # 1. Simpan pesan User ke riwayat chat log
        user_log = AIChatLog(
            user_id=user_id,
            platform=platform,
            role=ChatRole.USER,
            message=clean_msg,
        )
        session.add(user_log)
        await session.flush()

        # 2. Ambil daftar dompet dan kategori milik user
        wallets_query = select(Wallet).where(Wallet.user_id == user_id)
        wallets = (await session.exec(wallets_query)).all()
        wallet_names = [w.name for w in wallets]

        categories_query = select(Category).where(
            or_(Category.user_id == user_id, Category.user_id.is_(None))
        )
        categories = (await session.exec(categories_query)).all()
        category_names = [c.name for c in categories]

        # 3. Klasifikasi Intent menggunakan Gemini Structured Outputs
        decision = await AIService._classify_intent_with_llm(
            message=clean_msg,
            wallet_names=wallet_names,
            category_names=category_names,
        )

        reply_text = ""
        tx_response: Optional[TransactionResponse] = None
        budget_alert = None
        extracted_meta = decision.model_dump(mode="json")

        # 4. Tangani Berdasarkan Niat (Intent)
        if decision.intent == "transaction" and decision.transaction_data and decision.transaction_data.amount:
            # === AKSI: PENCATATAN TRANSAKSI OTOMATIS ===
            tx_data = decision.transaction_data
            matched_wallet = AIService._match_wallet(tx_data.wallet_name, wallets)
            matched_category = AIService._match_category(tx_data.category_name, categories, tx_data.type)

            if not matched_wallet:
                reply_text = "Saya memahami nominal transaksi Anda, namun Anda belum memiliki dompet aktif untuk mencatatnya."
            elif not matched_category:
                reply_text = "Saya memahami nominal transaksi Anda, namun tidak menemukan kategori yang sesuai."
            else:
                # Panggil TransactionService secara atomic
                tx_create_payload = TransactionCreate(
                    wallet_id=matched_wallet.id,
                    category_id=matched_category.id,
                    amount=tx_data.amount,
                    type=tx_data.type,
                    description=tx_data.description or clean_msg,
                    transaction_date=date.today(),
                    source=source,
                )
                tx_result = await TransactionService.create_transaction(
                    session=session,
                    user_id=user_id,
                    payload=tx_create_payload,
                )
                tx_response = tx_result.transaction
                budget_alert = tx_result.budget_alert

                tipe_str = "pengeluaran" if tx_data.type == TransactionType.EXPENSE else ("pemasukan" if tx_data.type == TransactionType.INCOME else "transfer")
                reply_text = f"✅ Berhasil mencatat {tipe_str} sebesar **Rp{tx_data.amount:,.0f}** untuk kategori **{matched_category.name}** menggunakan dompet **{matched_wallet.name}**."

                # Sisipkan alert jika mendekati atau melebihi anggaran
                if budget_alert:
                    reply_text += f"\n\n⚠️ *{budget_alert.message}*"

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
Kamu adalah AI Parsing Engine untuk aplikasi keuangan 'FinAI Track'.
Analisis pesan bahasa Indonesia dari pengguna secara cermat:

1. Jika pengguna berniat MENCATAT PENGELUARAN/PEMASUKAN/MUTASI:
   - Tetapkan intent = "transaction"
   - Ekstrak amount (konversi ekspresi seperti '25rb' -> 25000, '50k' -> 50000, '1.5jt' -> 1500000, 'dua puluh ribu' -> 20000).
   - Tentukan type ('expense', 'income', atau 'transfer'). Default adalah 'expense'.
   - Pilih category_name yang paling relevan dari daftar: {category_names}
   - Pilih wallet_name yang paling relevan dari daftar: {wallet_names} (default ke 'Tunai' jika tidak disebutkan).
   - Ekstrak description singkat barang/jasa yang dibeli.

2. Jika pengguna BERTANYA TENTANG DATA KEUANGAN / SALDO / ANGGARAN:
   - Tetapkan intent = "query"
   - Tentukan query_type:
     * 'balance_check' jika menanyakan sisa uang / saldo (misal: "Saldo BCA berapa?", "Total uangku berapa?")
     * 'total_expense' jika menanyakan pengeluaran (misal: "Pengeluaran bulan ini berapa?")
     * 'total_income' jika menanyakan pemasukan (misal: "Pemasukan bulan ini berapa?")
     * 'category_spending' jika menanyakan pengeluaran kategori tertentu (misal: "Habis berapa buat makan?")
     * 'budget_status' jika menanyakan kondisi anggaran (misal: "Budget makan masih aman?")
     * 'general_summary' jika meminta ringkasan menyeluruh keuangan.

3. Jika pesan adalah sapaan umum atau pertanyaan non-keuangan:
   - Tetapkan intent = "general"
   - Buatkan pesan general_reply yang ramah dan membantu.
"""
        structured_llm = llm.with_structured_output(LLMIntentDecision)
        try:
            result = await structured_llm.ainvoke(
                [
                    SystemMessage(content=system_instruction),
                    HumanMessage(content=message),
                ]
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
        """Pencocokan aturan berbasis Regex & Kata Kunci sebagai fallback andal."""
        lower = message.lower()

        # Deteksi pertanyaan (Query)
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

        # Deteksi transaksi (Ekstraksi Angka Nominal)
        match_jt = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:jt|juta)", lower)
        match_rb = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:rb|ribu|k)", lower)
        match_num = re.search(r"(?:rp\.?\s*)?(\d{4,9})", lower)

        amount = None
        if match_jt:
            val = float(match_jt.group(1).replace(",", "."))
            amount = Decimal(str(int(val * 1000000)))
        elif match_rb:
            val = float(match_rb.group(1).replace(",", "."))
            amount = Decimal(str(int(val * 1000)))
        elif match_num:
            amount = Decimal(match_num.group(1))

        if amount:
            # Tentukan tipe transaksi
            tx_type = TransactionType.EXPENSE
            if any((w in lower for w in ["gaji", "terima", "dapat", "bonus", "pemasukan"])):
                tx_type = TransactionType.INCOME

            # Cocokkan dompet
            matched_w = None
            for w in wallet_names:
                if w.lower() in lower:
                    matched_w = w
                    break

            # Cocokkan kategori
            matched_c = None
            for c in category_names:
                if c.lower() in lower:
                    matched_c = c
                    break

            return LLMIntentDecision(
                intent="transaction",
                transaction_data=LLMTransactionExtraction(
                    amount=amount,
                    type=tx_type,
                    category_name=matched_c,
                    wallet_name=matched_w,
                    description=message,
                ),
            )

        return LLMIntentDecision(
            intent="general",
            general_reply="Halo! Saya FinAI. Catat pengeluaran Anda cukup dengan mengetik seperti: 'Makan siang 25rb pakai BCA' atau rekam suara Anda.",
        )

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
        cats_of_type = [c for c in categories if c.type.value == tx_type.value] or categories
        if not name:
            return cats_of_type[0]
        name_lower = name.lower()
        matched = next((c for c in cats_of_type if c.name.lower() in name_lower or name_lower in c.name.lower()), None)
        return matched or cats_of_type[0]

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
            plan = await structured_llm.ainvoke(
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
