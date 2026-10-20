"use client";

import { useState } from "react";
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
  const { isBalanceHidden, toggleBalanceHidden } = useAuthStore();

  // Fetch data ringkasan dashboard terpadu
  const { data: summary, isLoading, refetch } = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: async () => {
      const res = await api.get("/api/v1/dashboard/summary");
      return res.data;
    },
  });

  const formatIDR = (val: number | string | undefined) => {
    if (val === undefined || val === null) return "Rp0";
    if (isBalanceHidden) return "••••••••";
    const num = typeof val === "string" ? parseFloat(val) : val;
    return `Rp${num.toLocaleString("id-ID")}`;
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
    "#EF4444",
    "#F59E0B",
    "#3B82F6",
    "#8B5CF6",
    "#EC4899",
    "#10B981",
    "#06B6D4",
    "#6B7280",
  ];

  return (
    <div className="space-y-6">
      {/* 1. Quick AI Input Bar (Pinned at top) */}
      <div className="sticky top-16 z-20">
        <QuickAIBar onSuccess={() => refetch()} />
      </div>

      {/* 2. Total Saldo & Financial Overview Card */}
      <div className="relative overflow-hidden rounded-3xl border border-surface-border bg-gradient-to-br from-surface to-surface-card p-6 shadow-xl">
        <div className="relative z-10 flex flex-col justify-between gap-6 sm:flex-row sm:items-center">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold tracking-wider text-slate-400 uppercase">
                Total Saldo Gabungan
              </span>
              <button
                type="button"
                onClick={toggleBalanceHidden}
                className="text-slate-400 hover:text-white transition"
                title={isBalanceHidden ? "Tampilkan Saldo" : "Sembunyikan Saldo"}
              >
                {isBalanceHidden ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            <h2 className="mt-2 text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
              {formatIDR(summary?.total_balance)}
            </h2>
          </div>

          {/* Mini Cashflow Metrics */}
          <div className="flex items-center gap-4">
            <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-2.5">
              <div className="flex items-center gap-1.5 text-xs text-emerald-400">
                <TrendingUp className="h-3.5 w-3.5" />
                <span>Pemasukan</span>
              </div>
              <span className="mt-1 block text-sm font-bold text-emerald-300">
                {formatIDR(summary?.monthly_income)}
              </span>
            </div>

            <div className="rounded-2xl border border-red-500/20 bg-red-500/10 px-4 py-2.5">
              <div className="flex items-center gap-1.5 text-xs text-red-400">
                <TrendingDown className="h-3.5 w-3.5" />
                <span>Pengeluaran</span>
              </div>
              <span className="mt-1 block text-sm font-bold text-red-300">
                {formatIDR(summary?.monthly_expense)}
              </span>
            </div>
          </div>
        </div>

        {/* Background glow decoration */}
        <div className="absolute -right-16 -top-16 h-48 w-48 rounded-full bg-blue-500/10 blur-3xl pointer-events-none" />
      </div>

      {/* 3. Daftar Dompet (Horizontal Carousel / Grid) */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-bold tracking-tight text-slate-200">Dompet & Rekening</h3>
          <Link
            href="/settings"
            className="flex items-center gap-1 text-xs font-semibold text-blue-400 hover:text-blue-300"
          >
            <Plus className="h-3.5 w-3.5" />
            Tambah Dompet
          </Link>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {summary?.wallets?.map((wallet: any) => (
            <div
              key={wallet.id}
              className="rounded-2xl border border-surface-border bg-surface-card p-4 transition hover:border-slate-600"
            >
              <div className="flex items-center justify-between">
                <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-blue-500/10 text-blue-400">
                  <WalletIcon className="h-4 w-4" />
                </div>
                <span className="rounded-md bg-surface-border px-2 py-0.5 text-[10px] font-medium text-slate-400 uppercase">
                  {wallet.type}
                </span>
              </div>
              <span className="mt-3 block text-xs font-medium text-slate-300 truncate">
                {wallet.name}
              </span>
              <span className="mt-0.5 block text-sm font-bold text-white">
                {formatIDR(wallet.balance)}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* 4. Visualisasi Grafik (Donut Category & 7-Days Cashflow Bar) */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Donut Chart: Pengeluaran per Kategori */}
        <div className="rounded-2xl border border-surface-border bg-surface p-5 shadow-lg">
          <h3 className="text-sm font-bold text-slate-200">Komposisi Pengeluaran Bulan Ini</h3>
          <p className="text-xs text-slate-400">Proporsi kategori belanja terbesar</p>

          {summary?.category_breakdown && summary.category_breakdown.length > 0 ? (
            <div className="mt-4 flex flex-col items-center sm:flex-row sm:justify-between">
              <div className="h-48 w-48">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={summary.category_breakdown}
                      dataKey="total_amount"
                      nameKey="category_name"
                      innerRadius={45}
                      outerRadius={75}
                      paddingAngle={3}
                    >
                      {summary.category_breakdown.map((entry: any, index: number) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={entry.category_color || DONUT_COLORS[index % DONUT_COLORS.length]}
                        />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(val: any) => formatIDR(val)}
                      contentStyle={{
                        backgroundColor: "#1E293B",
                        borderColor: "#334155",
                        borderRadius: "12px",
                        fontSize: "12px",
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              {/* Legend List */}
              <div className="mt-4 flex flex-1 flex-col gap-2 sm:mt-0 sm:pl-4">
                {summary.category_breakdown.slice(0, 5).map((item: any, idx: number) => (
                  <div key={idx} className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2 truncate">
                      <span
                        className="h-2.5 w-2.5 rounded-full flex-shrink-0"
                        style={{ backgroundColor: item.category_color || DONUT_COLORS[idx % DONUT_COLORS.length] }}
                      />
                      <span className="text-slate-300 truncate">{item.category_name}</span>
                    </div>
                    <span className="font-semibold text-white ml-2">
                      {item.percentage}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="flex h-48 items-center justify-center text-xs text-slate-500">
              Belum ada data pengeluaran di bulan ini.
            </div>
          )}
        </div>

        {/* Bar Chart: Tren Arus Kas 7 Hari Terakhir */}
        <div className="rounded-2xl border border-surface-border bg-surface p-5 shadow-lg">
          <h3 className="text-sm font-bold text-slate-200">Arus Kas 7 Hari Terakhir</h3>
          <p className="text-xs text-slate-400">Pemasukan vs Pengeluaran harian</p>

          <div className="mt-4 h-48 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={summary?.recent_7_days_cashflow || []} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <XAxis dataKey="day_name" stroke="#64748B" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748B" fontSize={10} tickLine={false} tickFormatter={(val) => `Rp${(val/1000).toFixed(0)}k`} />
                <Tooltip
                  formatter={(val: any) => formatIDR(val)}
                  contentStyle={{
                    backgroundColor: "#1E293B",
                    borderColor: "#334155",
                    borderRadius: "12px",
                    fontSize: "12px",
                  }}
                />
                <Bar dataKey="income" name="Pemasukan" fill="#10B981" radius={[4, 4, 0, 0]} />
                <Bar dataKey="expense" name="Pengeluaran" fill="#EF4444" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* 5. Status Anggaran Bulanan (Progress Bars) */}
      {summary?.budget_statuses && summary.budget_statuses.length > 0 && (
        <div className="rounded-2xl border border-surface-border bg-surface p-5 shadow-lg">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-200">Pantauan Plafon Anggaran (Budgets)</h3>
            <Link href="/ai-assistant" className="text-xs font-semibold text-blue-400 hover:text-blue-300">
              Kelola dengan AI $\rightarrow$
            </Link>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {summary.budget_statuses.map((b: any) => (
              <div key={b.category_id} className="space-y-1.5 rounded-xl border border-surface-border bg-surface-card p-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-200">{b.category_name}</span>
                  <span
                    className={`rounded-md px-2 py-0.5 text-[10px] font-bold ${
                      b.status === "overbudget"
                        ? "bg-red-500/20 text-red-400"
                        : b.status === "waspada"
                        ? "bg-amber-500/20 text-amber-400"
                        : "bg-emerald-500/20 text-emerald-400"
                    }`}
                  >
                    {b.status.toUpperCase()} ({b.percentage_used}%)
                  </span>
                </div>

                <div className="h-2 w-full overflow-hidden rounded-full bg-surface-border">
                  <div
                    className={`h-full rounded-full transition-all ${
                      b.status === "overbudget"
                        ? "bg-red-500"
                        : b.status === "waspada"
                        ? "bg-amber-500"
                        : "bg-emerald-500"
                    }`}
                    style={{ width: `${Math.min(b.percentage_used, 100)}%` }}
                  />
                </div>

                <div className="flex items-center justify-between text-[11px] text-slate-400">
                  <span>Terpakai: {formatIDR(b.spent_amount)}</span>
                  <span>Batas: {formatIDR(b.amount_limit)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 6. Transaksi Terkini */}
      <div className="rounded-2xl border border-surface-border bg-surface p-5 shadow-lg">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-200">5 Transaksi Terakhir</h3>
          <Link href="/transactions" className="text-xs font-semibold text-blue-400 hover:text-blue-300">
            Lihat Semua Transaksi $\rightarrow$
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
                      backgroundColor: `${tx.category_color || "#3B82F6"}20`,
                      color: tx.category_color || "#3B82F6",
                    }}
                  >
                    {tx.category_name?.slice(0, 2).toUpperCase() || "TX"}
                  </div>
                  <div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-sm font-medium text-slate-100">
                        {tx.description || tx.category_name}
                      </span>
                      {getSourceIcon(tx.source)}
                    </div>
                    <span className="text-xs text-slate-400">
                      {tx.wallet_name} • {tx.transaction_date}
                    </span>
                  </div>
                </div>

                <span
                  className={`text-sm font-bold ${
                    tx.type === "income"
                      ? "text-emerald-400"
                      : tx.type === "expense"
                      ? "text-red-400"
                      : "text-blue-400"
                  }`}
                >
                  {tx.type === "income" ? "+" : tx.type === "expense" ? "-" : ""}
                  {formatIDR(tx.amount)}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div className="py-6 text-center text-xs text-slate-500">
            Belum ada catatan transaksi. Gunakan Quick AI bar di atas untuk mulai mencatat!
          </div>
        )}
      </div>
    </div>
  );
}

