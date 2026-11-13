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
  Pencil,
  Loader2,
  Copy,
  Clock,
  LogOut,
  AlertTriangle,
  RotateCcw,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { isProtectedTunaiWallet } from "@/components/WalletConfigModal";
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

  // Edit Wallet Modal State
  const [editingWallet, setEditingWallet] = useState<any | null>(null);
  const [editWalletName, setEditWalletName] = useState("");
  const [editWalletType, setEditWalletType] = useState<"cash" | "bank" | "ewallet">("bank");
  const [editWalletPurpose, setEditWalletPurpose] = useState<"operational" | "savings" | "subscription">("operational");
  const [editWalletBalance, setEditWalletBalance] = useState("0");
  const [isUpdatingWallet, setIsUpdatingWallet] = useState(false);

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
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      queryClient.invalidateQueries({ queryKey: ["forecast-summary"] });
    } catch (err: any) {
      alert(err.response?.data?.detail || "Gagal menambah dompet.");
    }
  };

  // Action: Open Edit Wallet Modal
  const openEditWallet = (w: any) => {
    setEditingWallet(w);
    setEditWalletName(w.name);
    setEditWalletType(w.type);
    setEditWalletPurpose(w.purpose || "operational");
    setEditWalletBalance(String(w.balance));
  };

  // Action: Update Wallet
  const handleUpdateWallet = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingWallet || !editWalletName.trim()) return;
    setIsUpdatingWallet(true);
    try {
      await api.put(`/api/v1/wallets/${editingWallet.id}`, {
        name: editWalletName.trim(),
        type: editWalletType,
        purpose: editWalletPurpose,
        balance: parseFloat(editWalletBalance) || 0,
      });
      setEditingWallet(null);
      refetchWallets();
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      queryClient.invalidateQueries({ queryKey: ["forecast-summary"] });
      queryClient.invalidateQueries({ queryKey: ["forecast-ledger"] });
    } catch (err: any) {
      alert(err.response?.data?.detail || "Gagal mengubah data dompet.");
    } finally {
      setIsUpdatingWallet(false);
    }
  };

  // Action: 1-Click Quick Change Purpose from Card
  const handleQuickChangePurpose = async (walletId: string, newPurpose: string) => {
    try {
      await api.put(`/api/v1/wallets/${walletId}`, {
        purpose: newPurpose,
      });
      refetchWallets();
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      queryClient.invalidateQueries({ queryKey: ["forecast-summary"] });
      queryClient.invalidateQueries({ queryKey: ["forecast-ledger"] });
    } catch (err: any) {
      alert("Gagal memperbarui peruntukan dompet.");
    }
  };

  // Action: Delete Wallet
  const handleDeleteWallet = async (w: any) => {
    if (isProtectedTunaiWallet(w, wallets)) {
      alert("Dompet Tunai (Cash) utama tidak dapat dihapus.");
      return;
    }
    const balanceNum = parseFloat(w.balance ?? "0") || 0;
    const transferNote =
      balanceNum !== 0
        ? ` Sisa saldo sebesar Rp${balanceNum.toLocaleString("id-ID")} akan otomatis dipindahkan ke dompet Tunai (Cash).`
        : "";
    if (!confirm(`Hapus dompet "${w.name}"?${transferNote}`)) return;
    try {
      await api.delete(`/api/v1/wallets/${w.id}`);
      if (editingWallet?.id === w.id) setEditingWallet(null);
      refetchWallets();
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      queryClient.invalidateQueries({ queryKey: ["forecast-summary"] });
      queryClient.invalidateQueries({ queryKey: ["forecast-ledger"] });
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Gagal menghapus dompet.");
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
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-[#C8F526] animate-pulse" />
          <h1 className="text-xl font-black tracking-tight text-espresso flex items-center gap-2">
            <SettingsIcon className="h-5 w-5 text-espresso" />
            Pengaturan & Integrasi
          </h1>
        </div>
        <p className="text-xs text-espresso-muted font-medium mt-0.5">
          Kelola akun, integrasi bot Telegram, dompet & kategori transaksi
        </p>
      </div>

      {/* ===================================================================== */}
      {/* KARTU 1: INTEGRASI BOT TELEGRAM */}
      {/* ===================================================================== */}
      <div className="rounded-3xl border border-white/10 bg-gradient-to-br from-[#0F1117] via-[#161A26] to-[#0A0C12] p-6 text-white shadow-xl relative overflow-hidden">
        {/* Ambient Glow */}
        <div className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full bg-[#C8F526]/10 blur-3xl" />

        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/10 text-[#C8F526] border border-white/15 shadow-sm">
              <Bot className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-black text-white">Bot Telegram FinAI</h3>
                {tgStatus?.is_linked ? (
                  <span className="flex items-center gap-1 rounded-full bg-[#C8F526] px-2.5 py-0.5 text-[10px] font-black text-black">
                    <CheckCircle2 className="h-3 w-3" />
                    TERHUBUNG
                  </span>
                ) : (
                  <span className="rounded-full bg-white/10 border border-white/20 px-2.5 py-0.5 text-[10px] font-bold text-white/70">
                    BELUM TERHUBUNG
                  </span>
                )}
              </div>
              <p className="text-xs text-white/70 mt-1 leading-relaxed">
                {tgStatus?.is_linked
                  ? `Akun Anda terhubung dengan Chat ID: ${tgStatus.telegram_chat_id}. Kirim teks atau Voice Note ke bot kapan saja!`
                  : "Catat pengeluaran lewat chat & voice note di Telegram sambil beraktivitas."}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {tgStatus?.is_linked ? (
              <>
                <a
                  href="https://t.me/FinAi_track_bot"
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-1.5 rounded-2xl bg-[#C8F526] px-4 py-2.5 text-xs font-black text-black hover:bg-[#b8e51b] transition shadow-md active:scale-95"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                  Buka Chat Bot
                </a>
                <button
                  type="button"
                  onClick={handleUnlinkTelegram}
                  className="rounded-2xl border border-white/20 bg-white/10 px-3.5 py-2.5 text-xs font-bold text-white hover:bg-white/20 transition active:scale-95"
                >
                  Putus
                </button>
              </>
            ) : (
              <button
                type="button"
                onClick={handleGenerateTelegramOtp}
                disabled={isGeneratingOtp}
                className="flex items-center gap-2 rounded-2xl bg-[#C8F526] px-5 py-3 text-xs font-black text-black shadow-md hover:bg-[#b8e51b] transition disabled:opacity-50 active:scale-95"
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
      <div className="rounded-3xl border border-surface-border bg-white p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-surface-border pb-3">
          <div className="flex items-center gap-2">
            <WalletIcon className="h-4 w-4 text-espresso" />
            <h3 className="text-sm font-black text-espresso">Daftar Dompet / Rekening</h3>
          </div>
          <button
            type="button"
            onClick={() => setIsWalletModalOpen(true)}
            className="flex items-center gap-1 rounded-xl bg-[#0D0F17] px-3 py-1.5 text-xs font-black text-[#C8F526] hover:bg-[#161A26] transition shadow-xs active:scale-95"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Tambah Dompet</span>
          </button>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {wallets?.map((w: any) => (
            <div
              key={w.id}
              className="rounded-2xl border border-surface-border bg-surface-card p-3.5 flex flex-col justify-between gap-3 shadow-2xs hover:border-[#0D0F17]/30 transition"
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <span className="text-xs font-bold text-espresso block">{w.name}</span>
                  <span className="text-[10px] text-espresso-muted uppercase font-bold">{w.type}</span>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => openEditWallet(w)}
                    className="rounded-xl p-1.5 text-espresso-muted hover:bg-white hover:text-espresso transition"
                    title="Ubah Dompet & Peruntukan"
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </button>
                  {!isProtectedTunaiWallet(w, wallets) ? (
                    <button
                      type="button"
                      onClick={() => handleDeleteWallet(w)}
                      className="rounded-xl p-1.5 text-espresso-muted hover:bg-expense/10 hover:text-expense transition"
                      title="Hapus Dompet (saldo dipindah ke Tunai)"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  ) : (
                    <span
                      className="rounded-xl p-1.5 text-espresso-muted/30 cursor-not-allowed"
                      title="Dompet Tunai (Cash) tidak dapat dihapus"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </span>
                  )}
                </div>
              </div>

              {/* Saldo & Quick Purpose Selector */}
              <div className="flex items-center justify-between border-t border-surface-border/60 pt-2 text-xs">
                <span className="font-black text-espresso">
                  Rp{parseFloat(w.balance).toLocaleString("id-ID")}
                </span>

                {/* Quick Toggle / Select Purpose */}
                <select
                  value={w.purpose || "operational"}
                  onChange={(e) => handleQuickChangePurpose(w.id, e.target.value)}
                  className={`rounded-xl px-2.5 py-1 text-[11px] font-bold border cursor-pointer focus:outline-none transition ${
                    w.purpose === "savings"
                      ? "bg-emerald-600 text-white border-emerald-600"
                      : w.purpose === "subscription"
                      ? "bg-amber-400 text-black border-amber-400"
                      : "bg-[#0D0F17] text-[#C8F526] border-[#0D0F17]"
                  }`}
                  title="Ubah peruntukan dompet ini langsung"
                >
                  <option value="operational" className="bg-white text-espresso">💼 Operasional</option>
                  <option value="savings" className="bg-white text-espresso">💰 Tabungan</option>
                  <option value="subscription" className="bg-white text-espresso">💳 Tagihan</option>
                </select>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ===================================================================== */}
      {/* KARTU 3: MANAJEMEN KATEGORI */}
      {/* ===================================================================== */}
      <div className="rounded-3xl border border-surface-border bg-white p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-surface-border pb-3">
          <div className="flex items-center gap-2">
            <Tag className="h-4 w-4 text-espresso" />
            <h3 className="text-sm font-black text-espresso">Kategori Pemasukan & Pengeluaran</h3>
          </div>
          <button
            type="button"
            onClick={() => setIsCategoryModalOpen(true)}
            className="flex items-center gap-1 rounded-xl bg-[#0D0F17] px-3 py-1.5 text-xs font-black text-[#C8F526] hover:bg-[#161A26] transition shadow-xs active:scale-95"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Tambah Kategori</span>
          </button>
        </div>

        <div className="flex flex-wrap gap-2">
          {categories?.map((c: any) => (
            <span
              key={c.id}
              className="rounded-xl border border-surface-border bg-surface-card px-3 py-1.5 text-xs text-espresso font-semibold flex items-center gap-1.5"
            >
              <span
                className="h-2 w-2 rounded-full"
                style={{ backgroundColor: c.color || (c.type === "expense" ? "#F43F5E" : "#10B981") }}
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
      <div className="rounded-3xl border border-rose-200 bg-rose-500/5 p-6 shadow-xs space-y-3">
        <div className="flex items-center gap-2 text-rose-600">
          <AlertTriangle className="h-5 w-5 shrink-0" />
          <h3 className="text-sm font-black text-espresso">Reset Seluruh Data Finansial</h3>
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
            className="flex items-center gap-2 rounded-2xl bg-rose-600 px-4 py-2.5 text-xs font-black text-white shadow-sm hover:bg-rose-700 transition active:scale-95"
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
          <div className="w-full max-w-sm rounded-3xl border border-surface-border bg-white p-6 text-center shadow-2xl space-y-5">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-[#0D0F17] text-[#C8F526] shadow-sm">
              <Bot className="h-7 w-7" />
            </div>

            <div>
              <h3 className="text-lg font-black text-espresso">Tautkan ke Bot Telegram</h3>
              <p className="text-xs text-espresso-muted mt-1 leading-relaxed">
                Kirim kode 6 digit berikut ke bot <strong>@FinAi_track_bot</strong> di Telegram.
              </p>
            </div>

            {/* OTP Code Display Box */}
            <div className="flex items-center justify-center gap-3 rounded-2xl border border-surface-border bg-surface-card py-3.5 px-4 shadow-2xs">
              <span className="text-3xl font-black tracking-widest text-espresso font-mono">
                {pairingCode}
              </span>
              <button
                type="button"
                onClick={() => {
                  navigator.clipboard.writeText(pairingCode || "");
                  setCopied(true);
                  setTimeout(() => setCopied(false), 2000);
                }}
                className="rounded-xl bg-white border border-surface-border p-2 text-espresso hover:bg-surface-card transition"
                title="Salin Kode"
              >
                {copied ? <CheckCircle2 className="h-4 w-4 text-income" /> : <Copy className="h-4 w-4" />}
              </button>
            </div>

            <div className="flex items-center justify-center gap-1.5 text-[11px] text-espresso-muted font-bold">
              <Clock className="h-3.5 w-3.5" />
              <span>Kode ini berlaku selama 5 menit.</span>
            </div>

            <div className="space-y-2 pt-2">
              <a
                href={`https://t.me/FinAi_track_bot?start=${pairingCode}`}
                target="_blank"
                rel="noreferrer"
                className="flex w-full items-center justify-center gap-2 rounded-2xl bg-[#C8F526] py-3 text-xs font-black text-black shadow-md hover:bg-[#b8e51b] transition active:scale-95"
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
                className="w-full rounded-2xl bg-surface-card py-2.5 text-xs font-bold text-espresso-muted hover:text-espresso transition"
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
          <div className="w-full max-w-sm rounded-3xl border border-surface-border bg-white p-6 shadow-2xl space-y-4">
            <div>
              <h3 className="text-base font-black text-espresso">Tambah Dompet / Rekening</h3>
              <p className="text-[11px] text-espresso-muted">Pilih jenis akun & peruntukan pengelolaan uang</p>
            </div>
            <form onSubmit={handleCreateWallet} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-espresso mb-1">Nama Dompet</label>
                <input
                  type="text"
                  required
                  value={walletName}
                  onChange={(e) => setWalletName(e.target.value)}
                  placeholder="Misal: Bank Mandiri / GoPay"
                  className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-xs font-medium text-espresso placeholder:text-espresso-muted/40 focus:outline-none focus:border-[#0D0F17]"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-espresso mb-1">Tipe</label>
                <select
                  value={walletType}
                  onChange={(e: any) => setWalletType(e.target.value)}
                  className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-xs font-semibold text-espresso focus:outline-none focus:border-[#0D0F17]"
                >
                  <option value="cash">Tunai (Cash)</option>
                  <option value="bank">Bank</option>
                  <option value="ewallet">E-Wallet</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-espresso mb-1">
                  Peruntukan Dompet (Amplop / Pocket)
                </label>
                <select
                  value={walletPurpose}
                  onChange={(e: any) => setWalletPurpose(e.target.value)}
                  className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-xs font-semibold text-espresso focus:outline-none focus:border-[#0D0F17]"
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
                <label className="block text-xs font-bold text-espresso mb-1">Saldo Awal (Rp)</label>
                <input
                  type="number"
                  min="0"
                  value={walletBalance}
                  onChange={(e) => setWalletBalance(e.target.value)}
                  placeholder="0"
                  className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-xs font-black text-espresso focus:outline-none focus:border-[#0D0F17]"
                />
              </div>

              <div className="flex gap-2.5 pt-2">
                <button
                  type="button"
                  onClick={() => setIsWalletModalOpen(false)}
                  className="flex-1 rounded-2xl bg-surface-card py-2.5 text-xs font-bold text-espresso-muted hover:text-espresso transition"
                >
                  Batal
                </button>
                <button
                  type="submit"
                  className="flex-1 rounded-2xl bg-[#C8F526] py-2.5 text-xs font-black text-black hover:bg-[#b8e51b] transition shadow-md active:scale-98"
                >
                  Simpan
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* MODAL 2B: UBAH DATA & PERUNTUKAN DOMPET                               */}
      {/* ===================================================================== */}
      {editingWallet && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-md p-4">
          <div className="w-full max-w-sm rounded-[28px] border border-black/5 bg-white p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3">
              <div>
                <h3 className="text-base font-black text-black">Atur Dompet</h3>
                <p className="text-xs text-gray-400 font-medium">Tentukan fungsi dompet untuk sistem proyeksi</p>
              </div>
              <button
                type="button"
                onClick={() => setEditingWallet(null)}
                className="h-8 w-8 flex items-center justify-center rounded-xl bg-gray-100 text-gray-500 hover:text-black transition"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleUpdateWallet} className="space-y-4">
              <div>
                <label className="block text-xs font-black text-black mb-1">Nama Dompet</label>
                <input
                  type="text"
                  required
                  value={editWalletName}
                  onChange={(e) => setEditWalletName(e.target.value)}
                  className="w-full rounded-2xl border border-gray-200 bg-gray-50/50 px-3.5 py-2.5 text-xs text-black focus:outline-none focus:border-black font-bold"
                />
              </div>

              <div>
                <label className="block text-xs font-black text-black mb-1">Tipe</label>
                <select
                  value={editWalletType}
                  onChange={(e: any) => setEditWalletType(e.target.value)}
                  className="w-full rounded-2xl border border-gray-200 bg-gray-50/50 px-3.5 py-2.5 text-xs font-bold text-black focus:outline-none focus:border-black"
                >
                  <option value="cash">Tunai (Cash)</option>
                  <option value="bank">Bank</option>
                  <option value="ewallet">E-Wallet</option>
                </select>
              </div>

              {/* PERUNTUKAN DOMPET SELECTION CARDS */}
              <div>
                <label className="block text-xs font-black text-black mb-1.5">
                  Peruntukan Dompet (Amplop / Pocket)
                </label>
                <div className="space-y-2">
                  <div
                    onClick={() => setEditWalletPurpose("operational")}
                    className={`cursor-pointer rounded-2xl border p-3.5 transition flex items-start gap-3 ${
                      editWalletPurpose === "operational"
                        ? "border-black bg-gray-50 shadow-sm ring-1 ring-black"
                        : "border-gray-100 bg-gray-50/50 hover:border-gray-300"
                    }`}
                  >
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-black text-white text-sm">
                      💼
                    </div>
                    <div>
                      <span className="text-xs font-black text-black block">Dompet Operasional</span>
                      <span className="text-[11px] text-gray-500 font-medium block leading-tight mt-0.5">
                        Uang jajan & makan harian. Saldo ini menjadi dasar jatah belanja ideal hari ini.
                      </span>
                    </div>
                  </div>

                  <div
                    onClick={() => setEditWalletPurpose("savings")}
                    className={`cursor-pointer rounded-2xl border p-3.5 transition flex items-start gap-3 ${
                      editWalletPurpose === "savings"
                        ? "border-emerald-600 bg-emerald-50/40 shadow-sm ring-1 ring-emerald-600"
                        : "border-gray-100 bg-gray-50/50 hover:border-emerald-200"
                    }`}
                  >
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-emerald-500 text-white text-sm">
                      💰
                    </div>
                    <div>
                      <span className="text-xs font-black text-emerald-700 block">Dompet Tabungan</span>
                      <span className="text-[11px] text-gray-500 font-medium block leading-tight mt-0.5">
                        Simpanan riil / dana darurat. Saldo ini <strong>tidak boleh terpotong jajan harian</strong> dan dihitung sebagai tabungan tersimpan.
                      </span>
                    </div>
                  </div>

                  <div
                    onClick={() => setEditWalletPurpose("subscription")}
                    className={`cursor-pointer rounded-2xl border p-3.5 transition flex items-start gap-3 ${
                      editWalletPurpose === "subscription"
                        ? "border-amber-500 bg-amber-50/40 shadow-sm ring-1 ring-amber-500"
                        : "border-gray-100 bg-gray-50/50 hover:border-amber-200"
                    }`}
                  >
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-amber-400 text-black text-sm">
                      💳
                    </div>
                    <div>
                      <span className="text-xs font-black text-amber-700 block">Dompet Tagihan / Langganan</span>
                      <span className="text-[11px] text-gray-500 font-medium block leading-tight mt-0.5">
                        Khusus pembayaran tagihan rutin (iCloud, wifi, cicilan). Dicadangkan terpisah agar aman.
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-xs font-black text-black mb-1">Saldo Dompet Saat Ini (Rp)</label>
                <input
                  type="number"
                  step="any"
                  value={editWalletBalance}
                  onChange={(e) => setEditWalletBalance(e.target.value)}
                  className="w-full rounded-2xl border border-gray-200 bg-gray-50/50 px-3.5 py-2.5 text-xs font-bold text-black focus:outline-none focus:border-black"
                />
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setEditingWallet(null)}
                  className="flex-1 rounded-2xl bg-gray-100 py-3 text-xs font-bold text-gray-600 hover:text-black transition"
                >
                  Batal
                </button>
                <button
                  type="submit"
                  disabled={isUpdatingWallet}
                  className="flex-1 rounded-2xl bg-[#C8F526] py-3 text-xs font-black text-black hover:bg-[#b8e51b] transition shadow-md shadow-lime-500/20 disabled:opacity-50"
                >
                  {isUpdatingWallet ? "Menyimpan..." : "Simpan Perubahan"}
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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-md p-4">
          <div className="w-full max-w-sm rounded-[28px] border border-black/5 bg-white p-6 shadow-2xl">
            <h3 className="text-base font-black text-black mb-4">Tambah Kategori</h3>
            <form onSubmit={handleCreateCategory} className="space-y-4">
              <div>
                <label className="block text-xs font-black text-black mb-1">Nama Kategori</label>
                <input
                  type="text"
                  required
                  value={catName}
                  onChange={(e) => setCatName(e.target.value)}
                  placeholder="Misal: Tagihan Listrik"
                  className="w-full rounded-2xl border border-gray-200 bg-gray-50/50 px-3.5 py-2.5 text-xs text-black placeholder:text-gray-400 focus:outline-none focus:border-black font-semibold"
                />
              </div>

              <div>
                <label className="block text-xs font-black text-black mb-1">Tipe</label>
                <select
                  value={catType}
                  onChange={(e: any) => setCatType(e.target.value)}
                  className="w-full rounded-2xl border border-gray-200 bg-gray-50/50 px-3.5 py-2.5 text-xs font-bold text-black focus:outline-none focus:border-black"
                >
                  <option value="expense">Pengeluaran (Expense)</option>
                  <option value="income">Pemasukan (Income)</option>
                </select>
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsCategoryModalOpen(false)}
                  className="flex-1 rounded-2xl bg-gray-100 py-3 text-xs font-bold text-gray-600 hover:text-black transition"
                >
                  Batal
                </button>
                <button
                  type="submit"
                  className="flex-1 rounded-2xl bg-[#C8F526] py-3 text-xs font-black text-black hover:bg-[#b8e51b] transition shadow-md shadow-lime-500/20"
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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-md p-4">
          <div className="w-full max-w-sm rounded-[28px] border border-rose-200 bg-white p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-3 border-b border-rose-100 pb-3.5">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-rose-50 text-rose-600">
                <AlertTriangle className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-base font-black text-black">Konfirmasi Reset Data</h3>
                <span className="text-[11px] font-bold text-rose-600">Tindakan ini permanen!</span>
              </div>
            </div>

            <p className="text-xs text-gray-500 leading-relaxed font-medium">
              Seluruh transaksi, saldo dompet, rencana keuangan, dan pengeluaran pasti akan <strong>dihapus secara permanen</strong>. Akun Anda akan dimulai ulang dengan 1 dompet <strong>Tunai (Rp0)</strong>.
            </p>

            <form onSubmit={handleResetData} className="space-y-3 pt-1">
              <div>
                <label className="block text-[11px] font-bold text-black mb-1">
                  Ketik kata <span className="font-mono font-black text-rose-600">RESET</span> di bawah untuk konfirmasi:
                </label>
                <input
                  type="text"
                  required
                  value={confirmResetText}
                  onChange={(e) => setConfirmResetText(e.target.value)}
                  placeholder="Ketik RESET"
                  className="w-full rounded-2xl border border-rose-200 bg-rose-50/30 px-3.5 py-2.5 text-xs font-black text-black focus:outline-none focus:border-rose-600 tracking-wider uppercase placeholder:normal-case placeholder:font-normal"
                />
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsResetModalOpen(false)}
                  className="flex-1 rounded-2xl bg-gray-100 py-3 text-xs font-bold text-gray-600 hover:text-black transition"
                >
                  Batal
                </button>
                <button
                  type="submit"
                  disabled={confirmResetText.trim().toUpperCase() !== "RESET" || isResetting}
                  className="flex-1 rounded-2xl bg-rose-600 py-3 text-xs font-black text-white hover:bg-rose-700 transition disabled:opacity-40 disabled:cursor-not-allowed shadow-md shadow-rose-600/20"
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

