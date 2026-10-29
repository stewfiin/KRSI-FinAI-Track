"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Settings as SettingsIcon,
  Bot,
  Wallet as WalletIcon,
  Tag,
  CheckCircle2,
  ExternalLink,
  Plus,
  Trash2,
  Loader2,
  Copy,
  Clock,
  LogOut,
  AlertTriangle,
  RotateCcw,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { useRouter } from "next/navigation";

export default function SettingsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user, clearAuth } = useAuthStore();

  // Telegram Integration State
  const [isOtpModalOpen, setIsOtpModalOpen] = useState(false);
  const [pairingCode, setPairingCode] = useState<string | null>(null);
  const [isGeneratingOtp, setIsGeneratingOtp] = useState(false);
  const [copied, setCopied] = useState(false);

  // New Wallet Modal State
  const [isWalletModalOpen, setIsWalletModalOpen] = useState(false);
  const [walletName, setWalletName] = useState("");
  const [walletType, setWalletType] = useState<"cash" | "bank" | "ewallet">("bank");
  const [walletPurpose, setWalletPurpose] = useState<"operational" | "savings" | "subscription">("operational");
  const [walletBalance, setWalletBalance] = useState("0");

  // New Category Modal State
  const [isCategoryModalOpen, setIsCategoryModalOpen] = useState(false);
  const [catName, setCatName] = useState("");
  const [catType, setCatType] = useState<"expense" | "income">("expense");

  // Reset Account State
  const [isResetModalOpen, setIsResetModalOpen] = useState(false);
  const [confirmResetText, setConfirmResetText] = useState("");
  const [isResetting, setIsResetting] = useState(false);

  // 1. Fetch Telegram Status
  const {
    data: tgStatus,
    isLoading: isTgLoading,
    refetch: refetchTg,
  } = useQuery({
    queryKey: ["telegram-status"],
    queryFn: async () => (await api.get("/api/v1/telegram/status")).data,
  });

  // 2. Fetch Wallets
  const {
    data: wallets,
    isLoading: isWalletsLoading,
    refetch: refetchWallets,
  } = useQuery({
    queryKey: ["wallets"],
    queryFn: async () => (await api.get("/api/v1/wallets")).data,
  });

  // 3. Fetch Categories
  const {
    data: categories,
    isLoading: isCategoriesLoading,
    refetch: refetchCategories,
  } = useQuery({
    queryKey: ["categories"],
    queryFn: async () => (await api.get("/api/v1/categories")).data,
  });

  // Action: Generate Telegram OTP Code
  const handleGenerateTelegramOtp = async () => {
    setIsGeneratingOtp(true);
    try {
      const res = await api.post("/api/v1/telegram/pairing-code");
      setPairingCode(res.data.pairing_code);
      setIsOtpModalOpen(true);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Gagal membuat kode OTP.");
    } finally {
      setIsGeneratingOtp(false);
    }
  };

  // Action: Unlink Telegram
  const handleUnlinkTelegram = async () => {
    if (!confirm("Putus tautan bot Telegram dari akun Anda?")) return;
    try {
      await api.delete("/api/v1/telegram/unlink");
      refetchTg();
    } catch (err) {
      alert("Gagal memutus tautan Telegram.");
    }
  };

  // Action: Create Wallet
  const handleCreateWallet = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!walletName.trim()) return;
    try {
      await api.post("/api/v1/wallets", {
        name: walletName.trim(),
        type: walletType,
        purpose: walletPurpose,
        balance: parseFloat(walletBalance) || 0,
      });
      setIsWalletModalOpen(false);
      setWalletName("");
      setWalletBalance("0");
      setWalletPurpose("operational");
      refetchWallets();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Gagal menambah dompet.");
    }
  };

  // Action: Create Category
  const handleCreateCategory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!catName.trim()) return;
    try {
      await api.post("/api/v1/categories", {
        name: catName.trim(),
        type: catType,
      });
      setIsCategoryModalOpen(false);
      setCatName("");
      refetchCategories();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Gagal menambah kategori.");
    }
  };

  // Action: Reset All Financial Data (Akun Baru)
  const handleResetData = async (e: React.FormEvent) => {
    e.preventDefault();
    if (confirmResetText.trim().toUpperCase() !== "RESET") return;
    setIsResetting(true);
    try {
      await api.post("/api/v1/auth/reset-data");
      queryClient.clear();
      setIsResetModalOpen(false);
      setConfirmResetText("");
      alert("Seluruh data keuangan berhasil di-reset. Akun Anda kembali bersih seperti baru!");
      window.location.href = "/dashboard";
    } catch (err: any) {
      alert(err.response?.data?.detail || "Gagal mereset data akun.");
    } finally {
      setIsResetting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold tracking-tight text-espresso flex items-center gap-2">
          <SettingsIcon className="h-5 w-5 text-terracotta" />
          Pengaturan & Integrasi
        </h1>
        <p className="text-xs text-espresso-muted">
          Kelola profil pengguna, integrasi bot Telegram, dompet, dan kategori.
        </p>
      </div>

      {/* ===================================================================== */}
      {/* KARTU 1: INTEGRASI BOT TELEGRAM */}
      {/* ===================================================================== */}
      <div className="rounded-3xl border border-amber/40 bg-surface p-6 shadow-sm relative overflow-hidden">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-amber/20 text-terracotta border border-amber/30">
              <Bot className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-espresso">Bot Telegram FinAI</h3>
                {tgStatus?.is_linked ? (
                  <span className="flex items-center gap-1 rounded-md bg-income/15 border border-income/30 px-2 py-0.5 text-[10px] font-bold text-income">
                    <CheckCircle2 className="h-3 w-3" />
                    TERHUBUNG
                  </span>
                ) : (
                  <span className="rounded-md bg-amber/20 border border-amber/40 px-2 py-0.5 text-[10px] font-bold text-terracotta">
                    BELUM TERHUBUNG
                  </span>
                )}
              </div>
              <p className="text-xs text-espresso-muted mt-0.5">
                {tgStatus?.is_linked
                  ? `Akun Anda terhubung dengan Chat ID: ${tgStatus.telegram_chat_id}. Kirim teks atau Voice Note ke bot kapan saja!`
                  : "Catat pengeluaran lewat chat & voice note di Telegram sambil beraktivitas."}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {tgStatus?.is_linked ? (
              <>
                <a
                  href="https://t.me/FinAi_track_bot"
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-1.5 rounded-xl bg-terracotta px-4 py-2.5 text-xs font-semibold text-white hover:bg-terracotta-hover transition shadow-md shadow-terracotta/20"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                  Buka Chat Bot
                </a>
                <button
                  type="button"
                  onClick={handleUnlinkTelegram}
                  className="rounded-xl border border-terracotta/30 bg-terracotta/10 px-3 py-2.5 text-xs font-semibold text-terracotta hover:bg-terracotta/20 transition"
                >
                  Putus
                </button>
              </>
            ) : (
              <button
                type="button"
                onClick={handleGenerateTelegramOtp}
                disabled={isGeneratingOtp}
                className="flex items-center gap-2 rounded-xl bg-terracotta px-5 py-2.5 text-xs font-bold text-white shadow-md shadow-terracotta/20 hover:bg-terracotta-hover transition disabled:opacity-50"
              >
                {isGeneratingOtp ? <Loader2 className="h-4 w-4 animate-spin" /> : <Bot className="h-4 w-4" />}
                Hubungkan ke Telegram
              </button>
            )}
          </div>
        </div>
      </div>

      {/* ===================================================================== */}
      {/* KARTU 2: MANAJEMEN DOMPET */}
      {/* ===================================================================== */}
      <div className="rounded-3xl border border-surface-border bg-surface p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-surface-border pb-3">
          <div className="flex items-center gap-2">
            <WalletIcon className="h-4 w-4 text-terracotta" />
            <h3 className="text-sm font-bold text-espresso">Daftar Dompet / Rekening</h3>
          </div>
          <button
            type="button"
            onClick={() => setIsWalletModalOpen(true)}
            className="flex items-center gap-1 text-xs font-semibold text-terracotta hover:text-terracotta-hover"
          >
            <Plus className="h-3.5 w-3.5" />
            Tambah Dompet
          </button>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {wallets?.map((w: any) => (
            <div
              key={w.id}
              className="rounded-2xl border border-surface-border bg-surface-card p-3.5 flex items-center justify-between"
            >
              <div>
                <span className="text-xs font-bold text-espresso block">{w.name}</span>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <span className="text-[10px] text-espresso-muted uppercase">{w.type}</span>
                  <span
                    className={`rounded-md px-1.5 py-0.2 text-[9px] font-bold border ${
                      w.purpose === "savings"
                        ? "bg-income/15 text-income border-income/30"
                        : w.purpose === "subscription"
                        ? "bg-amber/20 text-terracotta border-amber/40"
                        : "bg-surface text-espresso-muted border-surface-border"
                    }`}
                  >
                    {w.purpose === "savings" ? "Tabungan" : w.purpose === "subscription" ? "Tagihan" : "Operasional"}
                  </span>
                </div>
              </div>
              <span className="text-xs font-bold text-espresso">
                Rp{parseFloat(w.balance).toLocaleString("id-ID")}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* ===================================================================== */}
      {/* KARTU 3: MANAJEMEN KATEGORI */}
      {/* ===================================================================== */}
      <div className="rounded-3xl border border-surface-border bg-surface p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-surface-border pb-3">
          <div className="flex items-center gap-2">
            <Tag className="h-4 w-4 text-income" />
            <h3 className="text-sm font-bold text-espresso">Kategori Pemasukan & Pengeluaran</h3>
          </div>
          <button
            type="button"
            onClick={() => setIsCategoryModalOpen(true)}
            className="flex items-center gap-1 text-xs font-semibold text-income hover:text-income-hover"
          >
            <Plus className="h-3.5 w-3.5" />
            Tambah Kategori
          </button>
        </div>

        <div className="flex flex-wrap gap-2">
          {categories?.map((c: any) => (
            <span
              key={c.id}
              className="rounded-xl border border-surface-border bg-surface-card px-3 py-1.5 text-xs text-espresso font-medium flex items-center gap-1.5"
            >
              <span
                className="h-2 w-2 rounded-full"
                style={{ backgroundColor: c.color || (c.type === "expense" ? "#D4621A" : "#588157") }}
              />
              {c.name}
              <span className="text-[10px] text-espresso-muted uppercase ml-1">({c.type})</span>
            </span>
          ))}
        </div>
      </div>

      {/* ===================================================================== */}
      {/* KARTU 4: DANGER ZONE - RESET DATA AKUN SEPERTI BARU                   */}
      {/* ===================================================================== */}
      <div className="rounded-3xl border border-expense/30 bg-expense-bg/30 p-6 shadow-sm space-y-3">
        <div className="flex items-center gap-2 text-expense">
          <AlertTriangle className="h-5 w-5 shrink-0" />
          <h3 className="text-sm font-bold text-espresso">Reset Seluruh Data Finansial</h3>
        </div>
        <p className="text-xs text-espresso-muted leading-relaxed">
          Hapus seluruh nominal saldo, riwayat transaksi, dompet tambahan, tagihan rutin, wishlist, dan blueprint keuangan. Akun Anda akan kembali bersih seperti baru dengan 1 dompet Tunai standar (Rp0).
        </p>
        <div className="pt-1">
          <button
            type="button"
            onClick={() => {
              setConfirmResetText("");
              setIsResetModalOpen(true);
            }}
            className="flex items-center gap-2 rounded-xl bg-expense px-4 py-2.5 text-xs font-bold text-white shadow-sm hover:bg-expense/90 transition active:scale-95"
          >
            <RotateCcw className="h-4 w-4" />
            <span>Reset Seluruh Data Akun</span>
          </button>
        </div>
      </div>

      {/* ===================================================================== */}
      {/* MODAL 1: OTP KODE TELEGRAM */}
      {/* ===================================================================== */}
      {isOtpModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="w-full max-w-sm rounded-3xl border border-amber/40 bg-surface p-6 text-center shadow-2xl space-y-5">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-amber/20 text-terracotta">
              <Bot className="h-7 w-7" />
            </div>

            <div>
              <h3 className="text-lg font-bold text-espresso">Tautkan ke Bot Telegram</h3>
              <p className="text-xs text-espresso-muted mt-1">
                Kirim kode 6 digit berikut ke bot <strong>@FinAi_track_bot</strong> di Telegram.
              </p>
            </div>

            {/* OTP Code Display Box */}
            <div className="flex items-center justify-center gap-3 rounded-2xl border border-amber/40 bg-amber/15 py-3 px-4">
              <span className="text-3xl font-extrabold tracking-widest text-terracotta font-mono">
                {pairingCode}
              </span>
              <button
                type="button"
                onClick={() => {
                  navigator.clipboard.writeText(pairingCode || "");
                  setCopied(true);
                  setTimeout(() => setCopied(false), 2000);
                }}
                className="rounded-lg bg-amber/20 p-2 text-terracotta hover:bg-amber/30 transition"
                title="Salin Kode"
              >
                {copied ? <CheckCircle2 className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
              </button>
            </div>

            <div className="flex items-center justify-center gap-1.5 text-[11px] text-terracotta font-semibold">
              <Clock className="h-3.5 w-3.5" />
              <span>Kode ini berlaku selama 5 menit.</span>
            </div>

            <div className="space-y-2 pt-2">
              <a
                href={`https://t.me/FinAi_track_bot?start=${pairingCode}`}
                target="_blank"
                rel="noreferrer"
                className="flex w-full items-center justify-center gap-2 rounded-xl bg-terracotta py-2.5 text-xs font-bold text-white shadow-md shadow-terracotta/20 hover:bg-terracotta-hover transition"
              >
                <ExternalLink className="h-4 w-4" />
                Buka Bot Telegram Langsung
              </a>

              <button
                type="button"
                onClick={() => {
                  setIsOtpModalOpen(false);
                  refetchTg();
                }}
                className="w-full rounded-xl bg-surface-card py-2 text-xs font-semibold text-espresso-muted hover:text-espresso"
              >
                Tutup
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* MODAL 2: TAMBAH DOMPET */}
      {/* ===================================================================== */}
      {isWalletModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="w-full max-w-sm rounded-3xl border border-surface-border bg-surface p-6 shadow-2xl">
            <h3 className="text-base font-bold text-espresso mb-4">Tambah Dompet / Rekening</h3>
            <form onSubmit={handleCreateWallet} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-espresso mb-1">Nama Dompet</label>
                <input
                  type="text"
                  required
                  value={walletName}
                  onChange={(e) => setWalletName(e.target.value)}
                  placeholder="Misal: Bank Mandiri / GoPay"
                  className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-xs text-espresso placeholder:text-espresso-muted/40 focus:outline-none focus:border-terracotta"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-espresso mb-1">Tipe</label>
                <select
                  value={walletType}
                  onChange={(e: any) => setWalletType(e.target.value)}
                  className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-xs font-medium text-espresso focus:outline-none"
                >
                  <option value="cash">Tunai (Cash)</option>
                  <option value="bank">Bank</option>
                  <option value="ewallet">E-Wallet</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-espresso mb-1">
                  Peruntukan Dompet (Amplop / Pocket)
                </label>
                <select
                  value={walletPurpose}
                  onChange={(e: any) => setWalletPurpose(e.target.value)}
                  className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-xs font-medium text-espresso focus:outline-none focus:border-terracotta"
                >
                  <option value="operational">Operasional (Uang jajan / belanja harian bebas)</option>
                  <option value="savings">Tabungan (Disimpan khusus / dana darurat / impian)</option>
                  <option value="subscription">Tagihan / Langganan (Khusus bayar cicilan / tagihan rutin)</option>
                </select>
                <span className="text-[10px] text-espresso-muted mt-1 block leading-tight">
                  Sistem proyeksi akan memisahkan saldo tabungan nyata & tagihan agar tidak tercampur ke batas jajan harian.
                </span>
              </div>

              <div>
                <label className="block text-xs font-semibold text-espresso mb-1">Saldo Awal (Rp)</label>
                <input
                  type="number"
                  min="0"
                  value={walletBalance}
                  onChange={(e) => setWalletBalance(e.target.value)}
                  placeholder="0"
                  className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-xs font-semibold text-espresso focus:outline-none focus:border-terracotta"
                />
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsWalletModalOpen(false)}
                  className="flex-1 rounded-xl bg-surface-card py-2 text-xs font-semibold text-espresso-muted hover:text-espresso"
                >
                  Batal
                </button>
                <button
                  type="submit"
                  className="flex-1 rounded-xl bg-terracotta py-2 text-xs font-semibold text-white hover:bg-terracotta-hover"
                >
                  Simpan
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* MODAL 3: TAMBAH KATEGORI */}
      {/* ===================================================================== */}
      {isCategoryModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="w-full max-w-sm rounded-3xl border border-surface-border bg-surface p-6 shadow-2xl">
            <h3 className="text-base font-bold text-espresso mb-4">Tambah Kategori</h3>
            <form onSubmit={handleCreateCategory} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-espresso mb-1">Nama Kategori</label>
                <input
                  type="text"
                  required
                  value={catName}
                  onChange={(e) => setCatName(e.target.value)}
                  placeholder="Misal: Tagihan Listrik"
                  className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-xs text-espresso placeholder:text-espresso-muted/40 focus:outline-none focus:border-income"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-espresso mb-1">Tipe</label>
                <select
                  value={catType}
                  onChange={(e: any) => setCatType(e.target.value)}
                  className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-xs font-medium text-espresso focus:outline-none"
                >
                  <option value="expense">Pengeluaran (Expense)</option>
                  <option value="income">Pemasukan (Income)</option>
                </select>
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsCategoryModalOpen(false)}
                  className="flex-1 rounded-xl bg-surface-card py-2 text-xs font-semibold text-espresso-muted hover:text-espresso"
                >
                  Batal
                </button>
                <button
                  type="submit"
                  className="flex-1 rounded-xl bg-income py-2 text-xs font-semibold text-white hover:bg-income-hover"
                >
                  Simpan
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* MODAL 4: KONFIRMASI RESET DATA                                        */}
      {/* ===================================================================== */}
      {isResetModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="w-full max-w-sm rounded-3xl border border-expense/40 bg-surface p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-2.5 text-expense border-b border-surface-border pb-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-expense/15 text-expense">
                <AlertTriangle className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-espresso">Konfirmasi Reset Data</h3>
                <span className="text-[11px] font-semibold text-expense">Tindakan ini permanen!</span>
              </div>
            </div>

            <p className="text-xs text-espresso-muted leading-relaxed">
              Seluruh transaksi, saldo dompet, rencana keuangan, dan pengeluaran pasti akan <strong>dihapus secara permanen</strong>. Akun Anda akan dimulai ulang dengan 1 dompet <strong>Tunai (Rp0)</strong>.
            </p>

            <form onSubmit={handleResetData} className="space-y-3 pt-1">
              <div>
                <label className="block text-[11px] font-semibold text-espresso mb-1">
                  Ketik kata <span className="font-mono font-bold text-expense">RESET</span> di bawah untuk konfirmasi:
                </label>
                <input
                  type="text"
                  required
                  value={confirmResetText}
                  onChange={(e) => setConfirmResetText(e.target.value)}
                  placeholder="Ketik RESET"
                  className="w-full rounded-xl border border-expense/30 bg-surface-card px-3 py-2 text-xs font-bold text-espresso focus:outline-none focus:border-expense tracking-wider uppercase placeholder:normal-case placeholder:font-normal"
                />
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsResetModalOpen(false)}
                  className="flex-1 rounded-xl bg-surface-card py-2 text-xs font-semibold text-espresso-muted hover:text-espresso"
                >
                  Batal
                </button>
                <button
                  type="submit"
                  disabled={confirmResetText.trim().toUpperCase() !== "RESET" || isResetting}
                  className="flex-1 rounded-xl bg-expense py-2 text-xs font-bold text-white hover:bg-expense/90 transition disabled:opacity-40 disabled:cursor-not-allowed shadow-sm"
                >
                  {isResetting ? (
                    <span className="flex items-center justify-center gap-1.5">
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      Mereset...
                    </span>
                  ) : (
                    "Reset Semua"
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

