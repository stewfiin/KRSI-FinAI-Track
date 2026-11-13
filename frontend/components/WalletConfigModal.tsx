"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Loader2,
  Pencil,
  PiggyBank,
  Plus,
  Receipt,
  Trash2,
  Wallet,
  X,
} from "lucide-react";
import { api } from "@/lib/api";

interface WalletConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  wallets: any[] | undefined;
  formatIDR: (val: number | string | undefined) => string;
}

export function isProtectedTunaiWallet(wallet: any, allWallets?: any[]): boolean {
  if (!wallet) return false;
  const typeLower = (wallet.type || "").toLowerCase();
  if (typeLower !== "cash") return false;
  const nameLower = (wallet.name || "").trim().toLowerCase();
  const cashCount = (allWallets || []).filter((w) => (w.type || "").toLowerCase() === "cash").length;
  return nameLower === "tunai" || cashCount <= 1;
}

export function WalletConfigModal({
  isOpen,
  onClose,
  wallets,
  formatIDR,
}: WalletConfigModalProps) {
  const queryClient = useQueryClient();

  const [mode, setMode] = useState<"list" | "create" | "edit">("list");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [busyWalletId, setBusyWalletId] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Create form state
  const [newName, setNewName] = useState("");
  const [newType, setNewType] = useState<"cash" | "bank" | "ewallet">("bank");
  const [newPurpose, setNewPurpose] = useState<"operational" | "savings" | "subscription">("operational");
  const [newBalance, setNewBalance] = useState("0");

  // Edit form state
  const [editingWallet, setEditingWallet] = useState<any | null>(null);
  const [editName, setEditName] = useState("");
  const [editType, setEditType] = useState<"cash" | "bank" | "ewallet">("cash");
  const [editPurpose, setEditPurpose] = useState<"operational" | "savings" | "subscription">("operational");
  const [editBalance, setEditBalance] = useState("0");

  if (!isOpen) return null;

  const invalidateWalletQueries = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["wallets"] }),
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] }),
      queryClient.invalidateQueries({ queryKey: ["forecast-summary"] }),
      queryClient.invalidateQueries({ queryKey: ["forecast-ledger"] }),
      queryClient.invalidateQueries({ queryKey: ["forecast-range-projection"] }),
    ]);
  };

  const resetAndClose = () => {
    setMode("list");
    setErrorMsg(null);
    setEditingWallet(null);
    onClose();
  };

  const handleQuickPurpose = async (walletId: string, purpose: "operational" | "savings" | "subscription") => {
    setBusyWalletId(walletId);
    setErrorMsg(null);
    try {
      await api.put(`/api/v1/wallets/${walletId}`, { purpose });
      await invalidateWalletQueries();
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.detail || "Gagal mengubah peruntukan dompet.");
    } finally {
      setBusyWalletId(null);
    }
  };

  const handleCreateWallet = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      await api.post("/api/v1/wallets", {
        name: newName.trim(),
        type: newType,
        purpose: newPurpose,
        balance: parseFloat(newBalance) || 0,
      });
      await invalidateWalletQueries();
      setNewName("");
      setNewType("bank");
      setNewPurpose("operational");
      setNewBalance("0");
      setMode("list");
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.detail || "Gagal menambah dompet.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const openEdit = (w: any) => {
    setEditingWallet(w);
    setEditName(w.name || "");
    setEditType((w.type || "cash") as any);
    setEditPurpose((w.purpose || "operational") as any);
    setEditBalance(String(w.balance ?? "0"));
    setErrorMsg(null);
    setMode("edit");
  };

  const handleUpdateWallet = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingWallet || !editName.trim()) return;
    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      await api.put(`/api/v1/wallets/${editingWallet.id}`, {
        name: editName.trim(),
        type: editType,
        purpose: editPurpose,
        balance: parseFloat(editBalance) || 0,
      });
      await invalidateWalletQueries();
      setEditingWallet(null);
      setMode("list");
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.detail || "Gagal memperbarui data dompet.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteWallet = async (w: any) => {
    if (isProtectedTunaiWallet(w, wallets)) {
      setErrorMsg("Dompet Tunai (Cash) utama tidak dapat dihapus.");
      return;
    }

    const balanceNum = parseFloat(w.balance ?? "0") || 0;
    const transferNote =
      balanceNum !== 0
        ? ` Sisa saldo sebesar ${formatIDR(balanceNum)} akan otomatis dipindahkan ke dompet Tunai (Cash).`
        : "";
    if (!confirm(`Hapus dompet "${w.name}"?${transferNote}`)) return;

    setBusyWalletId(w.id);
    setErrorMsg(null);
    try {
      await api.delete(`/api/v1/wallets/${w.id}`);
      await invalidateWalletQueries();
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.detail || "Gagal menghapus dompet.");
    } finally {
      setBusyWalletId(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <div className="w-full max-w-md rounded-3xl border border-surface-border bg-white p-6 shadow-2xl space-y-4">
        {/* Header Modal */}
        <div className="flex items-center justify-between border-b border-surface-border pb-3 gap-2">
          <div className="flex items-center gap-2 min-w-0">
            {mode !== "list" && (
              <button
                type="button"
                onClick={() => {
                  setMode("list");
                  setErrorMsg(null);
                  setEditingWallet(null);
                }}
                className="rounded-xl p-1.5 text-espresso-muted hover:bg-surface-card hover:text-espresso transition shrink-0"
                title="Kembali"
              >
                <ArrowLeft className="h-4 w-4" />
              </button>
            )}
            <div className="min-w-0">
              <h3 className="text-base font-semibold text-espresso truncate">
                {mode === "create"
                  ? "Tambah Dompet Baru"
                  : mode === "edit"
                  ? "Edit Dompet"
                  : "Atur Dompet"}
              </h3>
              <p className="text-[11px] text-espresso-muted truncate">
                {mode === "create"
                  ? "Buat akun baru dan tentukan peruntukannya"
                  : mode === "edit"
                  ? "Ubah nama, tipe, saldo, atau peruntukan"
                  : "Atur peruntukan, edit, hapus, atau tambah dompet"}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1.5 shrink-0">
            {mode === "list" && (
              <button
                type="button"
                onClick={() => {
                  setErrorMsg(null);
                  setMode("create");
                }}
                className="inline-flex items-center gap-1 rounded-xl bg-[#0D0F17] px-2.5 py-1.5 text-[11px] font-bold text-[#C8F526] hover:bg-[#161A26] transition active:scale-95"
              >
                <Plus className="h-3.5 w-3.5" />
                <span>Tambah Dompet</span>
              </button>
            )}
            <button
              type="button"
              onClick={resetAndClose}
              className="rounded-full p-1 text-espresso-muted hover:bg-surface-card hover:text-espresso transition"
              title="Tutup"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {errorMsg && (
          <div className="rounded-2xl border border-expense/40 bg-expense/10 px-3 py-2 text-xs font-semibold text-expense">
            {errorMsg}
          </div>
        )}

        {/* VIEW 1: DAFTAR DOMPET */}
        {mode === "list" && (
          <>
            <div className="space-y-3 max-h-[60vh] overflow-y-auto pr-1">
              {wallets?.map((w: any) => {
                const isProtected = isProtectedTunaiWallet(w, wallets);
                const isBusy = busyWalletId === w.id;

                return (
                  <div
                    key={w.id}
                    className="rounded-2xl border border-surface-border bg-surface-card p-3 space-y-2.5"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="flex items-center gap-1.5">
                          <span className="text-xs font-bold text-espresso truncate">{w.name}</span>
                          {isProtected && (
                            <span className="rounded-md bg-black/5 px-1.5 py-0.5 text-[9px] font-bold text-espresso-muted uppercase">
                              Utama
                            </span>
                          )}
                        </div>
                        <span className="text-[10px] text-espresso-muted uppercase font-bold">
                          {w.type}
                        </span>
                      </div>

                      <div className="flex items-center gap-1.5 shrink-0">
                        <span className="text-xs font-semibold text-espresso mr-1">
                          {formatIDR(w.balance)}
                        </span>
                        <button
                          type="button"
                          onClick={() => openEdit(w)}
                          disabled={isBusy}
                          className="rounded-xl p-1.5 text-espresso-muted hover:bg-white hover:text-espresso transition disabled:opacity-40"
                          title="Edit Dompet"
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </button>
                        {!isProtected ? (
                          <button
                            type="button"
                            onClick={() => handleDeleteWallet(w)}
                            disabled={isBusy}
                            className="rounded-xl p-1.5 text-espresso-muted hover:bg-expense/10 hover:text-expense transition disabled:opacity-40"
                            title="Hapus Dompet (saldo dipindah ke Tunai)"
                          >
                            {isBusy ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <Trash2 className="h-3.5 w-3.5" />
                            )}
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

                    {/* 3 Option Pills */}
                    <div className="grid grid-cols-3 gap-1.5 pt-0.5 text-[10px] font-bold">
                      <button
                        type="button"
                        disabled={isBusy}
                        onClick={() => handleQuickPurpose(w.id, "operational")}
                        className={`rounded-xl py-2 px-1 transition text-center border inline-flex items-center justify-center gap-1 ${
                          (w.purpose || "operational") === "operational"
                            ? "bg-[#0D0F17] text-[#C8F526] border-[#0D0F17] shadow-xs"
                            : "bg-white text-espresso-muted border-surface-border hover:text-espresso"
                        }`}
                      >
                        <Wallet className="h-3 w-3 shrink-0" />
                        <span>Operasional</span>
                      </button>

                      <button
                        type="button"
                        disabled={isBusy}
                        onClick={() => handleQuickPurpose(w.id, "savings")}
                        className={`rounded-xl py-2 px-1 transition text-center border inline-flex items-center justify-center gap-1 ${
                          w.purpose === "savings"
                            ? "bg-emerald-600 text-white border-emerald-600 shadow-xs"
                            : "bg-white text-espresso-muted border-surface-border hover:text-income"
                        }`}
                      >
                        <PiggyBank className="h-3 w-3 shrink-0" />
                        <span>Tabungan</span>
                      </button>

                      <button
                        type="button"
                        disabled={isBusy}
                        onClick={() => handleQuickPurpose(w.id, "subscription")}
                        className={`rounded-xl py-2 px-1 transition text-center border inline-flex items-center justify-center gap-1 ${
                          w.purpose === "subscription"
                            ? "bg-amber-400 text-black border-amber-400 shadow-xs"
                            : "bg-white text-espresso-muted border-surface-border hover:text-espresso"
                        }`}
                      >
                        <Receipt className="h-3 w-3 shrink-0" />
                        <span>Tagihan</span>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="pt-2 border-t border-surface-border">
              <button
                type="button"
                onClick={resetAndClose}
                className="w-full rounded-2xl bg-[#0D0F17] py-2.5 text-xs font-semibold text-[#C8F526] hover:bg-[#161A26] transition shadow-xs active:scale-98"
              >
                Selesai
              </button>
            </div>
          </>
        )}

        {/* VIEW 2: TAMBAH DOMPET */}
        {mode === "create" && (
          <form onSubmit={handleCreateWallet} className="space-y-3.5">
            <div>
              <label className="block text-xs font-bold text-espresso mb-1">Nama Dompet</label>
              <input
                type="text"
                required
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="Misal: Bank Mandiri / GoPay"
                className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-xs font-medium text-espresso placeholder:text-espresso-muted/40 focus:outline-none focus:border-[#0D0F17]"
              />
            </div>

            <div className="grid grid-cols-2 gap-2.5">
              <div>
                <label className="block text-xs font-bold text-espresso mb-1">Tipe</label>
                <select
                  value={newType}
                  onChange={(e) => setNewType(e.target.value as any)}
                  className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-xs font-semibold text-espresso focus:outline-none focus:border-[#0D0F17]"
                >
                  <option value="cash">Tunai (Cash)</option>
                  <option value="bank">Bank</option>
                  <option value="ewallet">E-Wallet</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-espresso mb-1">Saldo Awal (Rp)</label>
                <input
                  type="number"
                  min="0"
                  value={newBalance}
                  onChange={(e) => setNewBalance(e.target.value)}
                  placeholder="0"
                  className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-xs font-bold text-espresso focus:outline-none focus:border-[#0D0F17]"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-espresso mb-1">Peruntukan (Amplop)</label>
              <select
                value={newPurpose}
                onChange={(e) => setNewPurpose(e.target.value as any)}
                className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-xs font-semibold text-espresso focus:outline-none focus:border-[#0D0F17]"
              >
                <option value="operational">Operasional (Uang jajan / belanja harian)</option>
                <option value="savings">Tabungan (Dana simpanan / darurat)</option>
                <option value="subscription">Tagihan / Langganan (Khusus tagihan rutin)</option>
              </select>
            </div>

            <div className="flex gap-2.5 pt-2">
              <button
                type="button"
                onClick={() => {
                  setMode("list");
                  setErrorMsg(null);
                }}
                className="flex-1 rounded-2xl bg-surface-card py-2.5 text-xs font-bold text-espresso-muted hover:text-espresso transition"
              >
                Batal
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="flex-1 rounded-2xl bg-[#C8F526] py-2.5 text-xs font-bold text-black hover:bg-[#b8e51b] transition shadow-md disabled:opacity-50"
              >
                {isSubmitting ? "Menyimpan..." : "Simpan Dompet"}
              </button>
            </div>
          </form>
        )}

        {/* VIEW 3: EDIT DOMPET */}
        {mode === "edit" && editingWallet && (
          <form onSubmit={handleUpdateWallet} className="space-y-3.5">
            <div>
              <label className="block text-xs font-bold text-espresso mb-1">Nama Dompet</label>
              <input
                type="text"
                required
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-xs font-medium text-espresso focus:outline-none focus:border-[#0D0F17]"
              />
            </div>

            <div className="grid grid-cols-2 gap-2.5">
              <div>
                <label className="block text-xs font-bold text-espresso mb-1">Tipe</label>
                <select
                  value={editType}
                  onChange={(e) => setEditType(e.target.value as any)}
                  className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-xs font-semibold text-espresso focus:outline-none focus:border-[#0D0F17]"
                >
                  <option value="cash">Tunai (Cash)</option>
                  <option value="bank">Bank</option>
                  <option value="ewallet">E-Wallet</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-espresso mb-1">Saldo Saat Ini (Rp)</label>
                <input
                  type="number"
                  value={editBalance}
                  onChange={(e) => setEditBalance(e.target.value)}
                  className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-xs font-bold text-espresso focus:outline-none focus:border-[#0D0F17]"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-espresso mb-1">Peruntukan (Amplop)</label>
              <select
                value={editPurpose}
                onChange={(e) => setEditPurpose(e.target.value as any)}
                className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-xs font-semibold text-espresso focus:outline-none focus:border-[#0D0F17]"
              >
                <option value="operational">Operasional (Uang jajan / belanja harian)</option>
                <option value="savings">Tabungan (Dana simpanan / darurat)</option>
                <option value="subscription">Tagihan / Langganan (Khusus tagihan rutin)</option>
              </select>
            </div>

            <div className="flex gap-2.5 pt-2">
              <button
                type="button"
                onClick={() => {
                  setMode("list");
                  setEditingWallet(null);
                  setErrorMsg(null);
                }}
                className="flex-1 rounded-2xl bg-surface-card py-2.5 text-xs font-bold text-espresso-muted hover:text-espresso transition"
              >
                Batal
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="flex-1 rounded-2xl bg-[#0D0F17] py-2.5 text-xs font-bold text-[#C8F526] hover:bg-[#161A26] transition shadow-md disabled:opacity-50"
              >
                {isSubmitting ? "Menyimpan..." : "Simpan Perubahan"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
