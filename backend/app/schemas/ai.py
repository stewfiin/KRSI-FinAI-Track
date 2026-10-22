import uuid
from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from app.models.enums import ChatPlatform, TransactionType, WalletType
from app.schemas.budget import BudgetAlert
from app.schemas.transaction import TransactionResponse


# ==============================================================================
# 1. Schemas untuk Chat & Voice Interaction
# ==============================================================================

class AIChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Pesan teks dari pengguna")
    platform: ChatPlatform = Field(
        default=ChatPlatform.WEB,
        description="Platform asal request: 'web' atau 'telegram'",
    )


class AIChatResponse(BaseModel):
    intent: str = Field(..., description="Niat yang terdeteksi: 'transaction', 'query', atau 'general'")
    reply: str = Field(..., description="Balasan naratif ramah dari asisten AI")
    extracted_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Metadata entitas terstruktur yang diekstrak oleh AI",
    )
    transaction: Optional[TransactionResponse] = Field(
        default=None,
        description="Data transaksi jika AI berhasil mencatat transaksi tunggal baru",
    )
    transactions: Optional[List[TransactionResponse]] = Field(
        default=None,
        description="Daftar transaksi jika AI mencatat banyak transaksi sekaligus",
    )
    budget_alert: Optional[BudgetAlert] = Field(
        default=None,
        description="Peringatan batas anggaran jika transaksi pengeluaran mendekati/melebihi limit",
    )


class AIVoiceResponse(BaseModel):
    transcript: str = Field(..., description="Hasil transkripsi teks dari Groq Whisper")
    chat_result: AIChatResponse = Field(..., description="Hasil pemrosesan intent dari teks transkripsi")


# ==============================================================================
# 2. Schemas untuk Smart AI Dynamic Budgeting
# ==============================================================================

class AIBudgetRequest(BaseModel):
    prompt: str = Field(
        ...,
        min_length=3,
        description="Deskripsi preferensi/batasan anggaran (misal: 'Gaji 6 juta, alokasikan tabungan 1.5jt, hemat makan')",
    )
    month: Optional[int] = Field(None, ge=1, le=12, description="Bulan target (default: bulan berjalan)")
    year: Optional[int] = Field(None, ge=2020, le=2100, description="Tahun target (default: tahun berjalan)")
    apply_to_database: bool = Field(
        default=False,
        description="Jika true, draf alokasi anggaran akan langsung disimpan ke tabel budgets",
    )


class BudgetAllocationItem(BaseModel):
    category_id: uuid.UUID
    category_name: str
    suggested_limit: Decimal
    historical_average: Decimal
    reasoning: str


class AIBudgetResponse(BaseModel):
    total_budget: Decimal
    allocations: List[BudgetAllocationItem]
    strategy_summary: str
    saved_to_database: bool = False


# ==============================================================================
# 3. Pydantic Structured Outputs untuk Gemini LLM
# ==============================================================================

class LLMTransactionExtraction(BaseModel):
    amount: Optional[Decimal] = Field(None, description="Nominal uang dari kalimat user (contoh: 25000 untuk 25rb)")
    type: TransactionType = Field(
        default=TransactionType.EXPENSE,
        description="Tipe transaksi: expense (pengeluaran), income (pemasukan), atau transfer",
    )
    category_name: Optional[str] = Field(
        None,
        description="Nama kategori paling cocok dari daftar kategori yang disediakan",
    )
    wallet_name: Optional[str] = Field(
        None,
        description="Nama dompet/rekening asal paling cocok dari daftar dompet yang disediakan",
    )
    destination_wallet_name: Optional[str] = Field(
        None,
        description="Nama dompet/rekening tujuan jika tipe transaksi adalah transfer (misal: 'gopay')",
    )
    description: Optional[str] = Field(
        None,
        description="Keterangan singkat transaksi (contoh: 'Transfer 100rb dari Tunai ke Gopay', 'Beli kopi', 'Uang saku')",
    )


class LLMWalletCreation(BaseModel):
    name: str = Field(..., description="Nama dompet/rekening (contoh: BCA, OVO, Bank Mandiri, Tunai Cadangan)")
    type: WalletType = Field(default=WalletType.CASH, description="Tipe dompet: cash (tunai), bank (rekening bank), atau ewallet (dompet digital)")
    initial_balance: Decimal = Field(default=Decimal("0.00"), description="Saldo awal dompet jika disebutkan")


class LLMQueryExtraction(BaseModel):
    query_type: Literal[
        "balance_check",
        "total_expense",
        "total_income",
        "category_spending",
        "budget_status",
        "general_summary",
    ] = Field(..., description="Jenis pertanyaan data keuangan")
    target_category: Optional[str] = Field(None, description="Nama kategori jika pertanyaan spesifik ke kategori")
    target_wallet: Optional[str] = Field(None, description="Nama dompet jika pertanyaan spesifik ke saldo dompet")
    time_frame: Literal["this_month", "last_month", "today", "all_time"] = Field(
        default="this_month",
        description="Rentang waktu yang ditanyakan",
    )


class LLMIntentDecision(BaseModel):
    intent: Literal["transaction", "create_wallet", "query", "general"] = Field(
        ...,
        description="Klasifikasi niat user: 'transaction' jika user ingin mencatat mutasi uang, 'create_wallet' jika user ingin menambah dompet baru, 'query' jika user menanyakan informasi/saldo/pengeluaran, 'general' jika sapaan atau percakapan biasa",
    )
    transaction_data: Optional[LLMTransactionExtraction] = Field(
        default=None,
        description="Data transaksi tunggal",
    )
    transactions: Optional[List[LLMTransactionExtraction]] = Field(
        default=None,
        description="Daftar transaksi jika pengguna menyebutkan satu atau beberapa transaksi sekaligus dalam satu kalimat (contoh: 'beli kopi 5rb, dapet uang saku 10rb, makan siang 15rb')",
    )
    wallet_creation_data: Optional[LLMWalletCreation] = Field(
        default=None,
        description="Data pembuatan dompet baru jika intent = 'create_wallet'",
    )
    query_data: Optional[LLMQueryExtraction] = None
    general_reply: Optional[str] = Field(
        None,
        description="Jawaban singkat langsung jika niatnya adalah general (sapaan / percakapan umum)",
    )


class LLMBudgetItem(BaseModel):
    category_name: str
    suggested_limit: Decimal = Field(..., description="Batas nominal anggaran yang disarankan")
    reasoning: str = Field(..., description="Alasan rasional pemilihan nominal ini")


class LLMBudgetPlan(BaseModel):
    total_budget: Decimal
    allocations: List[LLMBudgetItem]
    strategy_summary: str

