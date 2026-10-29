"use client";

import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Eye,
  EyeOff,
  Wallet as WalletIcon,
  TrendingUp,
  TrendingDown,
  ArrowRightLeft,
  Calendar,
  AlertTriangle,
  Bot,
  Mic,
  Globe,
  Plus,
  Minus,
  X,
  Loader2,
  Tag,
} from "lucide-react";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Legend,
} from "recharts";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { QuickAIBar } from "@/components/QuickAIBar";
import Link from "next/link";

export default function DashboardPage() {
  const [mounted, setMounted] = useState(false);
  const { isBalanceHidden, toggleBalanceHidden } = useAuthStore();

  useEffect(() => {
    setMounted(true);
  }, []);

  // Modal State untuk Catat Transaksi Cepat Langsung di Dashboard
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalType, setModalType] = useState<"expense" | "income" | "transfer">("expense");
  const [amount, setAmount] = useState("");
  const [walletId, setWalletId] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [destWalletId, setDestWalletId] = useState("");
  const [description, setDescription] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Fetch data ringkasan dashboard terpadu
  const { data: summary, isLoading, refetch } = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: async () => {
      const res = await api.get("/api/v1/dashboard/summary");
      return res.data;
    },
  });

  // Fetch Wallets & Categories untuk form pencatatan manual
  const { data: wallets } = useQuery({
    queryKey: ["wallets"],
    queryFn: async () => (await api.get("/api/v1/wallets")).data,
  });

  const { data: categories } = useQuery({
    queryKey: ["categories"],
    queryFn: async () => (await api.get("/api/v1/categories")).data,
  });

  const formatIDR = (val: number | string | undefined) => {
    if (val === undefined || val === null) return "Rp0";
    if (isBalanceHidden) return "••••••••";
    const num = typeof val === "string" ? parseFloat(val) : val;
    return `Rp${num.toLocaleString("id-ID")}`;
  };

  const openTransactionModal = (type: "expense" | "income" | "transfer") => {
    setModalType(type);
    if (wallets && wallets.length > 0) setWalletId(wallets[0].id);
    if (wallets && wallets.length > 1) setDestWalletId(wallets[1].id);

    const relevant = categories?.filter((c: any) => c.type === type);
    if (relevant && relevant.length > 0) {
      setCategoryId(relevant[0].id);
    } else if (categories && categories.length > 0) {
      setCategoryId(categories[0].id);
    }
    setIsModalOpen(true);
  };

  const handleTypeChange = (newType: "expense" | "income" | "transfer") => {
    setModalType(newType);
    if (newType !== "transfer") {
      const relevant = categories?.filter((c: any) => c.type === newType);
      if (relevant && relevant.length > 0) {
        setCategoryId(relevant[0].id);
      }
    }
  };

  const handleSaveTransaction = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!amount || !walletId) return;
    if (modalType !== "transfer" && !categoryId) return;
    if (modalType === "transfer" && (!destWalletId || destWalletId === walletId)) {
      alert("Pilih dompet tujuan yang berbeda untuk transfer.");
      return;
    }

    setIsSubmitting(true);
    try {
      await api.post("/api/v1/transactions", {
        wallet_id: walletId,
        category_id: modalType === "transfer" ? (categories?.[0]?.id || categoryId) : categoryId,
        amount: parseFloat(amount),
        type: modalType,
        description: description.trim() || undefined,
        destination_wallet_id: modalType === "transfer" ? destWalletId : undefined,
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

  const getSourceIcon = (source: string) => {
    switch (source) {
      case "telegram_bot":
        return (
          <span title="Bot Telegram">
            <Bot className="h-3 w-3 text-sky-400" />
          </span>
        );
      case "ai_voice":
        return (
          <span title="AI Voice Note">
            <Mic className="h-3 w-3 text-purple-400" />
          </span>
        );
      case "ai_chat":
        return (
          <span title="AI Chatbot">
            <Bot className="h-3 w-3 text-blue-400" />
          </span>
        );
      default:
        return (
          <span title="Web Manual">
            <Globe className="h-3 w-3 text-emerald-400" />
          </span>
        );
    }
  };

  const DONUT_COLORS = [
    "#D4621A", // Terracotta
    "#F4AE52", // Amber
    "#588157", // Sage Green
    "#2A1A0E", // Espresso
    "#C78229", // Deep Amber
    "#993E0A", // Dark Terracotta
    "#456944", // Deep Sage
    "#6B584B", // Espresso Muted
  ];

  return (
    <div className="space-y-6">
      {/* 1. Quick AI Input Bar (Pinned at top - Mendukung input masuk & keluar sekaligus) */}
      <div className="sticky top-16 z-20">
        <QuickAIBar onSuccess={() => refetch()} />
      </div>

      {/* 2. Total Saldo & Financial Overview Card */}
      <div className="relative overflow-hidden rounded-3xl border border-surface-border bg-gradient-to-br from-surface to-surface-card p-5 sm:p-6 shadow-sm">
        <div className="relative z-10 flex flex-col justify-between gap-5 sm:flex-row sm:items-center">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold tracking-wider text-espresso-muted uppercase">
                Total Saldo Gabungan
              </span>
              <button
                type="button"
                onClick={toggleBalanceHidden}
                className="flex items-center justify-center h-6 w-6 rounded-md text-espresso-muted hover:text-espresso hover:bg-espresso/5 transition"
                title={isBalanceHidden ? "Tampilkan nominal (Sensor aktif)" : "Sembunyikan nominal (Sensor nonaktif)"}
                aria-label={isBalanceHidden ? "Tampilkan Saldo" : "Sembunyikan Saldo"}
              >
                {isBalanceHidden ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            <h2 className="mt-1.5 text-3xl font-extrabold tracking-tight text-espresso sm:text-4xl">
              {formatIDR(summary?.total_balance)}
            </h2>
          </div>

          {/* Mini Cashflow Metrics - Status Ringkasan Arus Kas Bulan Ini (Indikator informatif, bukan tombol duplikat) */}
          <div className="grid grid-cols-2 gap-2.5 sm:flex sm:items-center sm:gap-3">
            <div className="rounded-2xl border border-income/25 bg-income-bg/70 px-3.5 py-2.5 sm:px-4 sm:py-2.5">
              <div className="flex items-center gap-1.5 text-[11px] font-semibold text-income">
                <TrendingUp className="h-3.5 w-3.5" />
                <span>Pemasukan Bln Ini</span>
              </div>
              <span className="mt-1 block text-sm font-bold text-espresso">
                {formatIDR(summary?.monthly_income)}
              </span>
            </div>

            <div className="rounded-2xl border border-expense/25 bg-expense-bg/70 px-3.5 py-2.5 sm:px-4 sm:py-2.5">
              <div className="flex items-center gap-1.5 text-[11px] font-semibold text-expense">
                <TrendingDown className="h-3.5 w-3.5" />
                <span>Pengeluaran Bln Ini</span>
              </div>
              <span className="mt-1 block text-sm font-bold text-espresso">
                {formatIDR(summary?.monthly_expense)}
              </span>
            </div>
          </div>
        </div>

        {/* Background glow decoration */}
        <div className="absolute -right-16 -top-16 h-48 w-48 rounded-full bg-amber/15 blur-3xl pointer-events-none" />
      </div>

      {/* 3. Tombol Aksi Cepat Terpadu (Modern, Clean & High-Affordance Input Buttons) */}
      <div className="grid grid-cols-3 gap-2.5 sm:gap-3">
        <button
          type="button"
          onClick={() => openTransactionModal("income")}
          className="group flex flex-col sm:flex-row items-center justify-center gap-1.5 sm:gap-2.5 rounded-2xl border border-income/30 bg-surface px-3 py-3 shadow-xs hover:border-income hover:bg-income/5 hover:shadow-sm active:scale-95 transition-all"
        >
          <div className="flex h-7 w-7 items-center justify-center rounded-xl bg-income/15 text-income group-hover:scale-105 transition-transform">
            <Plus className="h-4 w-4 stroke-[2.5]" />
          </div>
          <span className="text-xs sm:text-sm font-bold text-espresso">Masuk</span>
        </button>

        <button
          type="button"
          onClick={() => openTransactionModal("expense")}
          className="group flex flex-col sm:flex-row items-center justify-center gap-1.5 sm:gap-2.5 rounded-2xl border border-expense/30 bg-surface px-3 py-3 shadow-xs hover:border-expense hover:bg-expense/5 hover:shadow-sm active:scale-95 transition-all"
        >
          <div className="flex h-7 w-7 items-center justify-center rounded-xl bg-expense/15 text-expense group-hover:scale-105 transition-transform">
            <Minus className="h-4 w-4 stroke-[2.5]" />
          </div>
          <span className="text-xs sm:text-sm font-bold text-espresso">Keluar</span>
        </button>

        <button
          type="button"
          onClick={() => openTransactionModal("transfer")}
          className="group flex flex-col sm:flex-row items-center justify-center gap-1.5 sm:gap-2.5 rounded-2xl border border-amber/40 bg-surface px-3 py-3 shadow-xs hover:border-amber hover:bg-amber/10 hover:shadow-sm active:scale-95 transition-all"
        >
          <div className="flex h-7 w-7 items-center justify-center rounded-xl bg-amber/20 text-terracotta group-hover:scale-105 transition-transform">
            <ArrowRightLeft className="h-4 w-4 stroke-[2.5]" />
          </div>
          <span className="text-xs sm:text-sm font-bold text-espresso">Transfer</span>
        </button>
      </div>

      {/* 4. Daftar Dompet (Horizontal Grid) */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-bold tracking-tight text-espresso">Dompet & Rekening</h3>
          <Link
            href="/settings"
            className="flex items-center gap-1 text-xs font-semibold text-terracotta hover:text-terracotta-hover"
          >
            <Plus className="h-3.5 w-3.5" />
            Tambah Dompet
          </Link>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {summary?.wallets?.map((wallet: any) => (
            <div
              key={wallet.id}
              className="rounded-2xl border border-surface-border bg-surface p-4 shadow-sm transition hover:border-terracotta/40 hover:shadow-md"
            >
              <div className="flex items-center justify-between">
                <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-terracotta/10 text-terracotta">
                  <WalletIcon className="h-4 w-4" />
                </div>
                <span className="rounded-md bg-surface-card px-2 py-0.5 text-[10px] font-semibold text-espresso-muted border border-surface-border uppercase">
                  {wallet.type}
                </span>
              </div>
              <span className="mt-3 block text-xs font-medium text-espresso-muted truncate">
                {wallet.name}
              </span>
              <span className="mt-0.5 block text-sm font-bold text-espresso">
                {formatIDR(wallet.balance)}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* 5. Visualisasi Grafik (Donut Category & 7-Days Cashflow Bar) */}
      {(() => {
        const categoryChartData = (summary?.category_breakdown || []).map((cat: any) => ({
          ...cat,
          total_amount: Number(cat.total_amount ?? cat.total_spent ?? 0),
          total_spent: Number(cat.total_amount ?? cat.total_spent ?? 0),
        }));

        const cashflowChartData = (summary?.daily_cashflow || summary?.recent_7_days_cashflow || []).map((item: any) => ({
          ...item,
          day: item.day || item.day_name || item.date,
          income: Number(item.income ?? 0),
          expense: Number(item.expense ?? 0),
        }));

        const hasCashflowActivity = cashflowChartData.some((d: any) => d.income > 0 || d.expense > 0);

        return (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {/* Donut Chart: Pengeluaran per Kategori */}
            <div className="rounded-2xl border border-surface-border bg-surface p-5 shadow-sm">
              <h3 className="text-sm font-bold text-espresso">Komposisi Pengeluaran Bulan Ini</h3>
              <p className="text-xs text-espresso-muted">Proporsi kategori belanja terbesar</p>

              {mounted && categoryChartData.length > 0 ? (
                <div className="mt-4 flex flex-col items-center sm:flex-row sm:justify-between">
                  <div className="h-48 w-48 flex-shrink-0">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={categoryChartData}
                          cx="50%"
                          cy="50%"
                          innerRadius={50}
                          outerRadius={75}
                          paddingAngle={4}
                          dataKey="total_amount"
                          nameKey="category_name"
                        >
                          {categoryChartData.map((entry: any, index: number) => (
                            <Cell
                              key={`cell-${index}`}
                              fill={entry.category_color || DONUT_COLORS[index % DONUT_COLORS.length]}
                            />
                          ))}
                        </Pie>
                        <Tooltip
                          formatter={(value: any) => [
                            `Rp${parseFloat(value).toLocaleString("id-ID")}`,
                            "Total",
                          ]}
                          contentStyle={{
                            backgroundColor: "#FFFFFF",
                            borderColor: "#EBD8C1",
                            borderRadius: "12px",
                            fontSize: "12px",
                            color: "#2A1A0E",
                            boxShadow: "0 4px 12px rgba(42, 26, 14, 0.08)",
                          }}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>

                  {/* Legend List */}
                  <div className="mt-4 w-full flex-1 space-y-1.5 sm:mt-0 sm:pl-4">
                    {categoryChartData.slice(0, 5).map((cat: any, i: number) => (
                      <div key={cat.category_id} className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2 truncate">
                          <span
                            className="h-2.5 w-2.5 rounded-full flex-shrink-0"
                            style={{
                              backgroundColor:
                                cat.category_color || DONUT_COLORS[i % DONUT_COLORS.length],
                            }}
                          />
                          <span className="text-espresso font-medium truncate">{cat.category_name}</span>
                        </div>
                        <span className="font-bold text-espresso ml-2">
                          {cat.percentage.toFixed(0)}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="flex h-48 items-center justify-center text-xs text-espresso-muted">
                  Belum ada data pengeluaran bulan ini.
                </div>
              )}
            </div>

            {/* Bar Chart: Arus Kas 7 Hari Terakhir */}
            <div className="rounded-2xl border border-surface-border bg-surface p-5 shadow-sm">
              <h3 className="text-sm font-bold text-espresso">Arus Kas 7 Hari Terakhir</h3>
              <p className="text-xs text-espresso-muted">Pemasukan vs Pengeluaran harian</p>

              {mounted && cashflowChartData.length > 0 && hasCashflowActivity ? (
                <div className="mt-4 h-48 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={cashflowChartData}>
                      <XAxis
                        dataKey="day"
                        stroke="#8C7767"
                        fontSize={11}
                        tickLine={false}
                        axisLine={false}
                      />
                      <YAxis
                        stroke="#8C7767"
                        fontSize={10}
                        tickLine={false}
                        axisLine={false}
                        tickFormatter={(val) => `Rp${(val / 1000).toFixed(0)}k`}
                      />
                      <Tooltip
                        formatter={(val: any) => [
                          `Rp${parseFloat(val).toLocaleString("id-ID")}`,
                          "",
                        ]}
                        contentStyle={{
                          backgroundColor: "#FFFFFF",
                          borderColor: "#EBD8C1",
                          borderRadius: "12px",
                          fontSize: "12px",
                          color: "#2A1A0E",
                          boxShadow: "0 4px 12px rgba(42, 26, 14, 0.08)",
                        }}
                      />
                      <Bar dataKey="income" name="Pemasukan" fill="#588157" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="expense" name="Pengeluaran" fill="#D4621A" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="flex h-48 items-center justify-center text-xs text-espresso-muted">
                  Belum ada riwayat transaksi dalam 7 hari terakhir.
                </div>
              )}
            </div>
          </div>
        );
      })()}

      {/* 6. Peringatan Status Anggaran (Budget Progress Bars) */}
      {(() => {
        const budgetStatusesList = summary?.budget_statuses || summary?.budgets || [];
        if (!budgetStatusesList || budgetStatusesList.length === 0) return null;
        return (
          <div className="rounded-2xl border border-surface-border bg-surface p-5 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-sm font-bold text-espresso">Pemantauan Batas Anggaran</h3>
              <span className="text-xs text-espresso-muted">Bulan Ini</span>
            </div>

            <div className="space-y-4">
              {budgetStatusesList.map((b: any) => (
                <div key={b.category_id || b.id} className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-espresso">{b.category_name}</span>
                    <span
                      className={`rounded-md px-1.5 py-0.5 text-[10px] font-bold ${
                        b.status === "overbudget"
                          ? "bg-expense/15 text-expense"
                          : b.status === "waspada"
                          ? "bg-amber/20 text-terracotta"
                          : "bg-income/15 text-income"
                      }`}
                    >
                      {b.status.toUpperCase()} ({b.percentage_used}%)
                    </span>
                  </div>

                  <div className="h-2 w-full overflow-hidden rounded-full bg-cream-dark/50">
                    <div
                      className={`h-full rounded-full transition-all ${
                        b.status === "overbudget"
                          ? "bg-expense"
                          : b.status === "waspada"
                          ? "bg-amber"
                          : "bg-income"
                      }`}
                      style={{ width: `${Math.min(b.percentage_used, 100)}%` }}
                    />
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-espresso-muted">
                    <span>Terpakai: {formatIDR(b.spent_amount)}</span>
                    <span>Batas: {formatIDR(b.amount_limit)}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })()}

      {/* 7. Transaksi Terkini */}
      <div className="rounded-2xl border border-surface-border bg-surface p-5 shadow-sm">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-sm font-bold text-espresso">5 Transaksi Terakhir</h3>
          <Link href="/transactions" className="text-xs font-semibold text-terracotta hover:text-terracotta-hover">
            Lihat Semua Transaksi →
          </Link>
        </div>

        {summary?.recent_transactions && summary.recent_transactions.length > 0 ? (
          <div className="divide-y divide-surface-border">
            {summary.recent_transactions.map((tx: any) => (
              <div key={tx.id} className="flex items-center justify-between py-3">
                <div className="flex items-center gap-3">
                  <div
                    className="flex h-9 w-9 items-center justify-center rounded-xl font-bold text-xs"
                    style={{
                      backgroundColor: tx.type === "transfer" ? "#F4AE5225" : `${tx.category_color || "#D4621A"}20`,
                      color: tx.type === "transfer" ? "#D4621A" : (tx.category_color || "#D4621A"),
                    }}
                  >
                    {tx.type === "transfer" ? (
                      <ArrowRightLeft className="h-4 w-4" />
                    ) : (
                      tx.category_name?.slice(0, 2).toUpperCase() || "TX"
                    )}
                  </div>
                  <div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-sm font-semibold text-espresso">
                        {tx.description || tx.category_name}
                      </span>
                      {getSourceIcon(tx.source)}
                    </div>
                    <span className="text-xs text-espresso-muted">
                      {tx.wallet_name} • {tx.transaction_date}
                    </span>
                  </div>
                </div>

                <span
                  className={`text-sm font-bold ${
                    tx.type === "income"
                      ? "text-income"
                      : tx.type === "expense"
                      ? "text-expense"
                      : "text-terracotta"
                  }`}
                >
                  {tx.type === "income" ? "+" : tx.type === "expense" ? "-" : "↔ "}
                  {formatIDR(tx.amount)}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div className="py-6 text-center text-xs text-espresso-muted">
            Belum ada catatan transaksi. Gunakan Quick AI bar di atas atau tombol aksi untuk mulai mencatat!
          </div>
        )}
      </div>

      {/* Modal Terpadu: Catat Transaksi Cepat (Masuk, Keluar, Transfer dalam 1 UI) */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm">
          <div className="relative w-full max-w-md rounded-3xl border border-surface-border bg-surface p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-surface-border">
              <h3 className="text-base font-bold text-espresso">Catat Transaksi Manual</h3>
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="rounded-lg p-1 text-espresso-muted hover:bg-surface-card hover:text-espresso"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleSaveTransaction} className="mt-4 space-y-4">
              {/* Segmented Control: Pilihan Tipe Transaksi */}
              <div className="grid grid-cols-3 gap-1 rounded-2xl bg-surface-card p-1 border border-surface-border">
                <button
                  type="button"
                  onClick={() => handleTypeChange("expense")}
                  className={`rounded-xl py-2 text-xs font-bold transition ${
                    modalType === "expense"
                      ? "bg-expense text-white shadow-md"
                      : "text-espresso-muted hover:text-espresso"
                  }`}
                >
                  📉 Keluar
                </button>
                <button
                  type="button"
                  onClick={() => handleTypeChange("income")}
                  className={`rounded-xl py-2 text-xs font-bold transition ${
                    modalType === "income"
                      ? "bg-income text-white shadow-md"
                      : "text-espresso-muted hover:text-espresso"
                  }`}
                >
                  📈 Masuk
                </button>
                <button
                  type="button"
                  onClick={() => handleTypeChange("transfer")}
                  className={`rounded-xl py-2 text-xs font-bold transition ${
                    modalType === "transfer"
                      ? "bg-terracotta text-white shadow-md"
                      : "text-espresso-muted hover:text-espresso"
                  }`}
                >
                  🔄 Transfer
                </button>
              </div>

              {/* Nominal Input */}
              <div>
                <label className="block text-xs font-semibold text-espresso">Nominal (Rp)</label>
                <input
                  type="number"
                  step="1000"
                  min="1"
                  required
                  placeholder="0"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  className="mt-1 block w-full rounded-xl border border-surface-border bg-surface px-3 py-2.5 text-base font-bold text-espresso placeholder:text-espresso-muted/40 focus:border-terracotta focus:outline-none"
                />
                {/* Quick nominal chips */}
                <div className="mt-2 flex gap-1.5 overflow-x-auto pb-1">
                  {[10000, 20000, 50000, 100000].map((val) => (
                    <button
                      key={val}
                      type="button"
                      onClick={() => setAmount(val.toString())}
                      className="rounded-lg border border-surface-border bg-surface-card px-2.5 py-1 text-[11px] font-semibold text-espresso-muted hover:border-terracotta hover:text-espresso"
                    >
                      +{val >= 1000 ? `${val / 1000}rb` : val}
                    </button>
                  ))}
                </div>
              </div>

              {/* Pilihan Kategori (Hanya jika bukan transfer) */}
              {modalType !== "transfer" && (
                <div>
                  <label className="block text-xs font-semibold text-espresso">
                    Kategori {modalType === "income" ? "Pemasukan" : "Pengeluaran"}
                  </label>
                  <select
                    value={categoryId}
                    onChange={(e) => setCategoryId(e.target.value)}
                    required
                    className="mt-1 block w-full rounded-xl border border-surface-border bg-surface px-3 py-2.5 text-xs font-medium text-espresso focus:border-terracotta focus:outline-none"
                  >
                    {categories
                      ?.filter((c: any) => c.type === modalType)
                      .map((cat: any) => (
                        <option key={cat.id} value={cat.id}>
                          {cat.name}
                        </option>
                      ))}
                  </select>
                </div>
              )}

              {/* Pilihan Dompet */}
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div>
                  <label className="block text-xs font-semibold text-espresso">
                    {modalType === "transfer" ? "Dompet Asal" : "Dompet"}
                  </label>
                  <select
                    value={walletId}
                    onChange={(e) => setWalletId(e.target.value)}
                    required
                    className="mt-1 block w-full rounded-xl border border-surface-border bg-surface px-3 py-2.5 text-xs font-medium text-espresso focus:border-terracotta focus:outline-none"
                  >
                    {wallets?.map((w: any) => (
                      <option key={w.id} value={w.id}>
                        {w.name} (Rp{parseFloat(w.balance).toLocaleString("id-ID")})
                      </option>
                    ))}
                  </select>
                </div>

                {modalType === "transfer" && (
                  <div>
                    <label className="block text-xs font-semibold text-espresso">Dompet Tujuan</label>
                    <select
                      value={destWalletId}
                      onChange={(e) => setDestWalletId(e.target.value)}
                      required
                      className="mt-1 block w-full rounded-xl border border-surface-border bg-surface px-3 py-2.5 text-xs font-medium text-espresso focus:border-terracotta focus:outline-none"
                    >
                      {wallets
                        ?.filter((w: any) => w.id !== walletId)
                        .map((w: any) => (
                          <option key={w.id} value={w.id}>
                            {w.name} (Rp{parseFloat(w.balance).toLocaleString("id-ID")})
                          </option>
                        ))}
                    </select>
                  </div>
                )}
              </div>

              {/* Deskripsi / Catatan */}
              <div>
                <label className="block text-xs font-semibold text-espresso">Catatan / Deskripsi (Opsional)</label>
                <input
                  type="text"
                  placeholder="misal: Makan siang, Uang saku ortu, Beli kopi..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="mt-1 block w-full rounded-xl border border-surface-border bg-surface px-3 py-2 text-xs font-medium text-espresso placeholder:text-espresso-muted/40 focus:border-terracotta focus:outline-none"
                />
              </div>

              {/* Tombol Simpan */}
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full rounded-xl bg-terracotta py-3 text-xs font-bold text-white shadow-lg shadow-terracotta/20 hover:bg-terracotta-hover transition disabled:opacity-50"
              >
                {isSubmitting ? (
                  <span className="flex items-center justify-center gap-1.5">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Menyimpan...
                  </span>
                ) : (
                  `Simpan ${modalType === "income" ? "Pemasukan" : modalType === "expense" ? "Pengeluaran" : "Transfer"}`
                )}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
