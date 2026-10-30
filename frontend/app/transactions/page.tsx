"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Plus,
  Filter,
  Trash2,
  Calendar,
  Wallet as WalletIcon,
  Tag,
  Loader2,
  Globe,
  Bot,
  Mic,
  ArrowRightLeft,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { api } from "@/lib/api";

export default function TransactionsPage() {
  const [filterType, setFilterType] = useState<string>("");
  const [filterWallet, setFilterWallet] = useState<string>("");
  const [filterCategory, setFilterCategory] = useState<string>("");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form State untuk Tambah Transaksi Manual
  const [amount, setAmount] = useState("");
  const [type, setType] = useState<"expense" | "income" | "transfer">("expense");
  const [walletId, setWalletId] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [description, setDescription] = useState("");
  const [destWalletId, setDestWalletId] = useState("");

  // Fetch Wallets
  const { data: wallets } = useQuery({
    queryKey: ["wallets"],
    queryFn: async () => (await api.get("/api/v1/wallets")).data,
  });

  // Fetch Categories
  const { data: categories } = useQuery({
    queryKey: ["categories"],
    queryFn: async () => (await api.get("/api/v1/categories")).data,
  });

  // Fetch Transactions dengan query filters
  const {
    data: transactions,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["transactions", filterType, filterWallet, filterCategory],
    queryFn: async () => {
      const params: any = {};
      if (filterType) params.type = filterType;
      if (filterWallet) params.wallet_id = filterWallet;
      if (filterCategory) params.category_id = filterCategory;
      const res = await api.get("/api/v1/transactions", { params });
      return res.data;
    },
  });

  const handleCreateTransaction = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!walletId || !categoryId || !amount) return;
    setIsSubmitting(true);

    try {
      await api.post("/api/v1/transactions", {
        wallet_id: walletId,
        category_id: categoryId,
        amount: parseFloat(amount),
        type,
        description: description.trim() || undefined,
        destination_wallet_id: type === "transfer" ? destWalletId : undefined,
        source: "manual_web",
      });

      setIsModalOpen(false);
      setAmount("");
      setDescription("");
      refetch();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Gagal mencatat transaksi.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Hapus transaksi ini? Saldo dompet Anda akan dikembalikan secara otomatis.")) {
      return;
    }
    try {
      await api.delete(`/api/v1/transactions/${id}`);
      refetch();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Gagal menghapus transaksi.");
    }
  };

  const getSourceIcon = (source: string) => {
    switch (source) {
      case "telegram_bot":
        return (
          <span title="Telegram Bot">
            <Bot className="h-3.5 w-3.5 text-sky-400" />
          </span>
        );
      case "ai_voice":
        return (
          <span title="AI Voice Note">
            <Mic className="h-3.5 w-3.5 text-purple-400" />
          </span>
        );
      case "ai_chat":
        return (
          <span title="AI Chatbot">
            <Bot className="h-3.5 w-3.5 text-blue-400" />
          </span>
        );
      default:
        return (
          <span title="Web Manual">
            <Globe className="h-3.5 w-3.5 text-emerald-400" />
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-espresso">Buku Besar Transaksi</h1>
        </div>

        <button
          type="button"
          onClick={() => {
            if (wallets && wallets.length > 0) setWalletId(wallets[0].id);
            if (categories && categories.length > 0) setCategoryId(categories[0].id);
            setIsModalOpen(true);
          }}
          className="flex items-center gap-1.5 rounded-xl bg-terracotta px-4 py-2.5 text-xs font-semibold text-white shadow-md shadow-terracotta/20 hover:bg-terracotta-hover transition"
        >
          <Plus className="h-4 w-4" />
          Catat Transaksi Manual
        </button>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-2 rounded-2xl border border-surface-border bg-surface p-3 shadow-sm">
        <div className="flex items-center gap-1.5 text-xs font-medium text-espresso-muted pr-2">
          <Filter className="h-3.5 w-3.5 text-terracotta" />
          <span>Filter:</span>
        </div>

        {/* Filter Tipe */}
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          className="rounded-xl border border-surface-border bg-surface-card px-3 py-1.5 text-xs font-medium text-espresso focus:outline-none focus:border-terracotta"
        >
          <option value="">Semua Tipe</option>
          <option value="expense">Pengeluaran</option>
          <option value="income">Pemasukan</option>
          <option value="transfer">Transfer</option>
        </select>

        {/* Filter Dompet */}
        <select
          value={filterWallet}
          onChange={(e) => setFilterWallet(e.target.value)}
          className="rounded-xl border border-surface-border bg-surface-card px-3 py-1.5 text-xs font-medium text-espresso focus:outline-none focus:border-terracotta"
        >
          <option value="">Semua Dompet</option>
          {wallets?.map((w: any) => (
            <option key={w.id} value={w.id}>
              {w.name}
            </option>
          ))}
        </select>

        {/* Filter Kategori */}
        <select
          value={filterCategory}
          onChange={(e) => setFilterCategory(e.target.value)}
          className="rounded-xl border border-surface-border bg-surface-card px-3 py-1.5 text-xs font-medium text-espresso focus:outline-none focus:border-terracotta"
        >
          <option value="">Semua Kategori</option>
          {categories?.map((c: any) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>

        {(filterType || filterWallet || filterCategory) && (
          <button
            onClick={() => {
              setFilterType("");
              setFilterWallet("");
              setFilterCategory("");
            }}
            className="text-xs font-semibold text-terracotta hover:text-terracotta-hover ml-auto"
          >
            Reset Filter
          </button>
        )}
      </div>

      {/* Transaction List */}
      <div className="rounded-3xl border border-surface-border bg-surface p-4 shadow-sm">
        {isLoading ? (
          <div className="flex h-40 items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-terracotta" />
          </div>
        ) : transactions && transactions.length > 0 ? (
          <div className="divide-y divide-surface-border">
            {transactions.map((tx: any) => (
              <div
                key={tx.id}
                className="flex items-center justify-between py-3.5 px-2 hover:bg-surface-card/60 rounded-xl transition"
              >
                <div className="flex items-center gap-3">
                  <div
                    className="flex h-10 w-10 items-center justify-center rounded-2xl font-bold text-xs"
                    style={{
                      backgroundColor: `${tx.category_color || "#D4621A"}20`,
                      color: tx.category_color || "#D4621A",
                    }}
                  >
                    {tx.type === "income" ? (
                      <TrendingUp className="h-4 w-4" />
                    ) : tx.type === "expense" ? (
                      <TrendingDown className="h-4 w-4" />
                    ) : (
                      <ArrowRightLeft className="h-4 w-4" />
                    )}
                  </div>

                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-espresso">
                        {tx.description || tx.category_name}
                      </span>
                      {getSourceIcon(tx.source)}
                    </div>
                    <div className="flex items-center gap-2 text-xs text-espresso-muted mt-0.5">
                      <span>{tx.wallet_name}</span>
                      <span>•</span>
                      <span>{tx.category_name}</span>
                      <span>•</span>
                      <span>{tx.transaction_date}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <span
                    className={`text-sm font-bold ${
                      tx.type === "income"
                        ? "text-income"
                        : tx.type === "expense"
                        ? "text-expense"
                        : "text-terracotta"
                    }`}
                  >
                    {tx.type === "income" ? "+" : tx.type === "expense" ? "-" : ""}
                    Rp{parseFloat(tx.amount).toLocaleString("id-ID")}
                  </span>

                  <button
                    onClick={() => handleDelete(tx.id)}
                    title="Hapus Transaksi"
                    className="text-espresso-muted/40 hover:text-expense transition p-1"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="py-12 text-center text-xs text-espresso-muted">
            Tidak ada transaksi yang cocok dengan filter yang dipilih.
          </div>
        )}
      </div>

      {/* Modal Tambah Transaksi Manual */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-3xl border border-surface-border bg-surface p-6 shadow-2xl">
            <h3 className="text-base font-bold text-espresso mb-4">Catat Transaksi Manual</h3>

            <form onSubmit={handleCreateTransaction} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-espresso mb-1">Tipe Transaksi</label>
                <div className="grid grid-cols-3 gap-2">
                  {(["expense", "income", "transfer"] as const).map((t) => (
                    <button
                      key={t}
                      type="button"
                      onClick={() => setType(t)}
                      className={`rounded-xl py-2 text-xs font-bold capitalize transition ${
                        type === t
                          ? t === "expense"
                            ? "bg-expense text-white shadow-md shadow-expense/25"
                            : t === "income"
                            ? "bg-income text-white shadow-md shadow-income/25"
                            : "bg-terracotta text-white shadow-md shadow-terracotta/25"
                          : "bg-surface-card text-espresso-muted hover:text-espresso"
                      }`}
                    >
                      {t === "expense" ? "Keluar" : t === "income" ? "Masuk" : "Transfer"}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-espresso mb-1">Nominal (Rp)</label>
                <input
                  type="number"
                  required
                  min="1"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="50000"
                  className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-sm font-semibold text-espresso placeholder:text-espresso-muted/40 focus:outline-none focus:border-terracotta"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-espresso mb-1">
                  {type === "transfer" ? "Dompet Asal" : "Dompet"}
                </label>
                <select
                  required
                  value={walletId}
                  onChange={(e) => setWalletId(e.target.value)}
                  className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-xs font-medium text-espresso focus:outline-none focus:border-terracotta"
                >
                  {wallets?.map((w: any) => (
                    <option key={w.id} value={w.id}>
                      {w.name} (Saldo: Rp{parseFloat(w.balance).toLocaleString("id-ID")})
                    </option>
                  ))}
                </select>
              </div>

              {type === "transfer" && (
                <div>
                  <label className="block text-xs font-semibold text-espresso mb-1">Dompet Tujuan</label>
                  <select
                    required
                    value={destWalletId}
                    onChange={(e) => setDestWalletId(e.target.value)}
                    className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-xs font-medium text-espresso focus:outline-none focus:border-terracotta"
                  >
                    <option value="">Pilih dompet penerima...</option>
                    {wallets
                      ?.filter((w: any) => w.id !== walletId)
                      .map((w: any) => (
                        <option key={w.id} value={w.id}>
                          {w.name}
                        </option>
                      ))}
                  </select>
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-espresso mb-1">Kategori</label>
                <select
                  required
                  value={categoryId}
                  onChange={(e) => setCategoryId(e.target.value)}
                  className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-xs font-medium text-espresso focus:outline-none focus:border-terracotta"
                >
                  {categories?.map((c: any) => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({c.type})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-espresso mb-1">Deskripsi / Catatan</label>
                <input
                  type="text"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Misal: Makan malam di warung"
                  className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-xs font-medium text-espresso placeholder:text-espresso-muted/40 focus:outline-none focus:border-terracotta"
                />
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="flex-1 rounded-xl bg-surface-card py-2.5 text-xs font-semibold text-espresso-muted hover:text-espresso"
                >
                  Batal
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="flex-1 rounded-xl bg-terracotta py-2.5 text-xs font-semibold text-white hover:bg-terracotta-hover disabled:opacity-50"
                >
                  {isSubmitting ? "Menyimpan..." : "Simpan Transaksi"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

