"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Compass,
  TrendingUp,
  TrendingDown,
  ShieldAlert,
  CheckCircle2,
  Clock,
  Sparkles,
  Sliders,
  Calendar,
  AlertTriangle,
  Plus,
  Trash2,
  HelpCircle,
  X,
  Loader2,
  Check,
  Zap,
} from "lucide-react";
import { api } from "@/lib/api";

export default function ForecastPage() {
  const [activeTab, setActiveTab] = useState<"ledger" | "fixed" | "simulator">("ledger");

  // Blueprint Setting Modal State
  const [isPlanModalOpen, setIsPlanModalOpen] = useState(false);
  const [monthlyIncome, setMonthlyIncome] = useState("");
  const [dailyLivingBudget, setDailyLivingBudget] = useState("");
  const [monthlySavingsTarget, setMonthlySavingsTarget] = useState("");
  const [cycleStartDay, setCycleStartDay] = useState(1);
  const [isSavingPlan, setIsSavingPlan] = useState(false);

  // Income Stream (Multi-Sumber Pendapatan) State
  const [isAddStreamOpen, setIsAddStreamOpen] = useState(false);
  const [streamName, setStreamName] = useState("");
  const [streamAmount, setStreamAmount] = useState("");
  const [streamFrequency, setStreamFrequency] = useState<"daily" | "weekly" | "biweekly" | "monthly">("weekly");
  const [streamReceiveDay, setStreamReceiveDay] = useState(0); // 0=Senin, 1..31=Tanggal
  const [isSavingStream, setIsSavingStream] = useState(false);

  const queryClient = useQueryClient();

  // Add Fixed Expense Modal State
  const [isAddFixedModalOpen, setIsAddFixedModalOpen] = useState(false);
  const [fixedName, setFixedName] = useState("");
  const [fixedAmount, setFixedAmount] = useState("");
  const [fixedWalletId, setFixedWalletId] = useState("");
  const [isSavingFixed, setIsSavingFixed] = useState(false);

  // Quick Wallet Purpose Config Modal State
  const [isWalletConfigModalOpen, setIsWalletConfigModalOpen] = useState(false);

  // Add Wishlist Modal State
  const [isAddWishlistModalOpen, setIsAddWishlistModalOpen] = useState(false);
  const [wishlistName, setWishlistName] = useState("");
  const [wishlistPrice, setWishlistPrice] = useState("");
  const [isSavingWishlist, setIsSavingWishlist] = useState(false);

  // What-If Simulation State
  const [simName, setSimName] = useState("");
  const [simAmount, setSimAmount] = useState("");
  const [simSource, setSimSource] = useState<"savings_pool" | "operational_wallet">("savings_pool");
  const [isSimulating, setIsSimulating] = useState(false);
  const [simResult, setSimResult] = useState<any | null>(null);

  // ===========================================================================
  // 1. Data Fetching
  // ===========================================================================
  const {
    data: summary,
    isLoading: isSummaryLoading,
    refetch: refetchSummary,
  } = useQuery({
    queryKey: ["forecast-summary"],
    queryFn: async () => (await api.get("/api/v1/forecast/summary")).data,
  });

  const {
    data: ledger,
    isLoading: isLedgerLoading,
    refetch: refetchLedger,
  } = useQuery({
    queryKey: ["forecast-ledger"],
    queryFn: async () => (await api.get("/api/v1/forecast/daily-ledger")).data,
  });

  const {
    data: plan,
    refetch: refetchPlan,
  } = useQuery({
    queryKey: ["forecast-plan"],
    queryFn: async () => {
      const res = await api.get("/api/v1/forecast/plan");
      const d = res.data;
      setMonthlyIncome(String(d.monthly_income));
      setDailyLivingBudget(String(d.daily_living_budget));
      setMonthlySavingsTarget(String(d.monthly_savings_target));
      setCycleStartDay(d.cycle_start_day || 1);
      return d;
    },
  });

  const {
    data: wishlists,
    refetch: refetchWishlists,
  } = useQuery({
    queryKey: ["forecast-wishlists"],
    queryFn: async () => (await api.get("/api/v1/forecast/wishlists")).data,
  });

  const {
    data: incomeStreams,
    refetch: refetchIncomeStreams,
  } = useQuery({
    queryKey: ["forecast-income-streams"],
    queryFn: async () => (await api.get("/api/v1/forecast/income-streams")).data,
  });

  const { data: wallets } = useQuery({
    queryKey: ["wallets"],
    queryFn: async () => (await api.get("/api/v1/wallets")).data,
  });

  const formatIDR = (val: number | string | undefined) => {
    if (val === undefined || val === null) return "Rp0";
    const num = typeof val === "string" ? parseFloat(val) : val;
    return `Rp${Math.round(num).toLocaleString("id-ID")}`;
  };

  // ===========================================================================
  // 2. Handlers
  // ===========================================================================
  const handleSavePlan = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingPlan(true);
    try {
      await api.put("/api/v1/forecast/plan", {
        monthly_income: parseFloat(monthlyIncome),
        daily_living_budget: parseFloat(dailyLivingBudget),
        monthly_savings_target: parseFloat(monthlySavingsTarget),
        cycle_start_day: cycleStartDay,
      });
      setIsPlanModalOpen(false);
      refetchPlan();
      refetchSummary();
      refetchLedger();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Gagal menyimpan blueprint keuangan.");
    } finally {
      setIsSavingPlan(false);
    }
  };

  const handleCreateStream = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!streamName.trim() || !streamAmount) return;
    setIsSavingStream(true);
    try {
      await api.post("/api/v1/forecast/income-streams", {
        name: streamName.trim(),
        amount: parseFloat(streamAmount),
        frequency: streamFrequency,
        receive_day: streamFrequency === "weekly" ? streamReceiveDay : (streamFrequency === "monthly" ? streamReceiveDay : null),
      });
      setStreamName("");
      setStreamAmount("");
      setIsAddStreamOpen(false);
      refetchIncomeStreams();
      refetchSummary();
      refetchLedger();
      refetchPlan();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Gagal menambah sumber pendapatan.");
    } finally {
      setIsSavingStream(false);
    }
  };

  const handleDeleteStream = async (id: string) => {
    if (!confirm("Hapus sumber pendapatan ini?")) return;
    try {
      await api.delete(`/api/v1/forecast/income-streams/${id}`);
      refetchIncomeStreams();
      refetchSummary();
      refetchLedger();
      refetchPlan();
    } catch (err: any) {
      alert("Gagal menghapus sumber pendapatan.");
    }
  };

  const handleToggleFixed = async (id: string) => {
    try {
      await api.post(`/api/v1/forecast/fixed-expenses/${id}/toggle-paid`);
      refetchSummary();
      queryClient.invalidateQueries({ queryKey: ["wallets"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    } catch (err: any) {
      alert("Gagal memperbarui status tagihan.");
    }
  };

  const handleCreateFixed = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fixedName.trim() || !fixedAmount) return;
    setIsSavingFixed(true);
    try {
      await api.post("/api/v1/forecast/fixed-expenses", {
        name: fixedName.trim(),
        amount: parseFloat(fixedAmount),
        wallet_id: fixedWalletId || null,
      });
      setIsAddFixedModalOpen(false);
      setFixedName("");
      setFixedAmount("");
      setFixedWalletId("");
      refetchSummary();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Gagal menambah tagihan pasti.");
    } finally {
      setIsSavingFixed(false);
    }
  };

  const handleDeleteFixed = async (id: string) => {
    if (!confirm("Hapus tagihan pasti ini?")) return;
    try {
      await api.delete(`/api/v1/forecast/fixed-expenses/${id}`);
      refetchSummary();
    } catch (err: any) {
      alert("Gagal menghapus tagihan.");
    }
  };

  const handleCreateWishlist = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!wishlistName.trim() || !wishlistPrice) return;
    setIsSavingWishlist(true);
    try {
      await api.post("/api/v1/forecast/wishlists", {
        item_name: wishlistName.trim(),
        estimated_price: parseFloat(wishlistPrice),
        target_source: "savings_pool",
      });
      setIsAddWishlistModalOpen(false);
      setWishlistName("");
      setWishlistPrice("");
      refetchWishlists();
    } catch (err: any) {
      alert("Gagal menambah wishlist.");
    } finally {
      setIsSavingWishlist(false);
    }
  };

  const handleDeleteWishlist = async (id: string) => {
    if (!confirm("Hapus barang dari daftar wishlist?")) return;
    try {
      await api.delete(`/api/v1/forecast/wishlists/${id}`);
      refetchWishlists();
    } catch (err: any) {
      alert("Gagal menghapus wishlist.");
    }
  };

  const handleRunSimulation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!simName.trim() || !simAmount) return;
    setIsSimulating(true);
    setSimResult(null);

    try {
      const res = await api.post("/api/v1/forecast/simulate", {
        item_name: simName.trim(),
        amount: parseFloat(simAmount),
        source: simSource,
      });
      setSimResult(res.data);
    } catch (err: any) {
      alert("Gagal menjalankan simulasi.");
    } finally {
      setIsSimulating(false);
    }
  };

  const quickSimulate = (name: string, price: number) => {
    setSimName(name);
    setSimAmount(String(price));
    setActiveTab("simulator");
  };

  return (
    <div className="space-y-5 pb-16">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-extrabold tracking-tight text-espresso flex items-center gap-2">
            <Compass className="h-5 w-5 text-terracotta" />
            Proyeksi & Runway
          </h1>
          <p className="text-xs text-espresso-muted">
            Prediksi daya tahan uang, plafon belanja harian ideal, dan simulasi belanja.
          </p>
        </div>

        <button
          type="button"
          onClick={() => setIsPlanModalOpen(true)}
          className="flex items-center gap-1.5 rounded-xl border border-surface-border bg-surface px-3 py-1.5 text-xs font-bold text-espresso shadow-sm hover:border-terracotta transition"
          title="Atur Blueprint Finansial"
        >
          <Sliders className="h-3.5 w-3.5 text-terracotta" />
          <span>Blueprint</span>
        </button>
      </div>

      {/* ===================================================================== */}
      {/* 1. HERO CARD: JATAH BELANJA IDEAL HARI INI (DYNAMIC DAILY RUNWAY)     */}
      {/* ===================================================================== */}
      {summary && (
        <div className="relative overflow-hidden rounded-3xl border border-surface-border bg-gradient-to-br from-surface to-surface-card p-5 shadow-md space-y-4">
          <div className="flex items-center justify-between">
            <span className="rounded-lg bg-amber/20 px-2 py-0.5 text-[10px] font-bold text-terracotta uppercase tracking-wider">
              Batas Belanja Hari Ini
            </span>
            <span className="text-xs text-espresso-muted font-medium">
              Sisa {summary.cycle_info.days_remaining} hari dalam siklus
            </span>
          </div>

          <div>
            <div className="flex items-baseline gap-2">
              <h2 className="text-3xl font-black text-espresso tracking-tight">
                {formatIDR(summary.today_metrics.ideal_spending_today)}
              </h2>
              <span className="text-xs text-espresso-muted font-semibold">/ hari (Ideal)</span>
            </div>

            <div className="mt-2 flex items-center justify-between text-xs">
              <span className="text-espresso-muted">
                Terpakai: <strong className="text-espresso">{formatIDR(summary.today_metrics.actual_spent_today)}</strong>
              </span>
              <span
                className={`font-bold rounded-md px-1.5 py-0.5 text-[11px] ${
                  summary.today_metrics.daily_variance >= 0
                    ? "bg-income/15 text-income"
                    : "bg-expense/15 text-expense"
                }`}
              >
                {summary.today_metrics.daily_variance >= 0
                  ? `Sisa: +${formatIDR(summary.today_metrics.daily_variance)} (Surplus)`
                  : `Over: -${formatIDR(Math.abs(summary.today_metrics.daily_variance))} (Defisit)`}
              </span>
            </div>

            {/* Gauge Progress Bar */}
            <div className="mt-2 h-2.5 w-full overflow-hidden rounded-full bg-cream-dark/60">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  summary.today_metrics.percentage_used > 100
                    ? "bg-expense"
                    : summary.today_metrics.percentage_used >= 80
                    ? "bg-amber"
                    : "bg-income"
                }`}
                style={{ width: `${Math.min(summary.today_metrics.percentage_used, 100)}%` }}
              />
            </div>
          </div>

          {/* Quick Metrics Grid */}
          <div className="grid grid-cols-2 gap-2 pt-2 border-t border-surface-border text-xs">
            <div className="rounded-2xl border border-surface-border bg-surface p-2.5">
              <div className="flex items-center gap-1.5 text-espresso-muted text-[11px]">
                <Clock className="h-3.5 w-3.5 text-terracotta" />
                <span>Saldo Operasional Bebas</span>
              </div>
              <span className="mt-1 block text-sm font-extrabold text-espresso">
                {formatIDR(summary.safe_to_spend_total)}
              </span>
              <span className="text-[10px] text-espresso-muted block truncate">
                Daya tahan: <strong>{summary.runway_prediction.predicted_runway_days} Hari</strong> {summary.runway_prediction.is_runway_safe ? "✅" : "⚠️"}
              </span>
            </div>

            <div className="rounded-2xl border border-surface-border bg-surface p-2.5">
              <div className="flex items-center gap-1.5 text-espresso-muted text-[11px]">
                <Sparkles className="h-3.5 w-3.5 text-income" />
                <span>Tabungan Tersimpan</span>
              </div>
              <span className="mt-1 block text-sm font-extrabold text-income">
                {formatIDR(summary.current_savings_balance ?? summary.savings_pool_balance)}
              </span>
              <span className="text-[10px] text-espresso-muted block truncate">
                Target: {formatIDR(summary.end_of_month_forecast.target_savings)}
              </span>
            </div>
          </div>

          {/* Envelope / Pocket Banking Breakdown Strip */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-1 text-[11px]">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="inline-flex items-center gap-1.5 rounded-xl bg-surface px-2.5 py-1 text-espresso border border-surface-border">
                <span className="h-2 w-2 rounded-full bg-terracotta" />
                <span>Operasional: <strong>{formatIDR(summary.safe_to_spend_total)}</strong></span>
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-xl bg-surface px-2.5 py-1 text-espresso border border-surface-border">
                <span className="h-2 w-2 rounded-full bg-income" />
                <span>Tabungan: <strong>{formatIDR(summary.current_savings_balance ?? summary.savings_pool_balance)}</strong></span>
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-xl bg-surface px-2.5 py-1 text-espresso border border-surface-border">
                <span className="h-2 w-2 rounded-full bg-amber" />
                <span>Tagihan: <strong>{formatIDR(summary.subscription_pool_balance)}</strong></span>
              </span>
            </div>

            <button
              type="button"
              onClick={() => setIsWalletConfigModalOpen(true)}
              className="inline-flex items-center justify-center gap-1 rounded-xl border border-surface-border bg-surface px-2.5 py-1 text-[11px] font-bold text-terracotta hover:border-terracotta transition shadow-xs"
              title="Atur dompet mana yang jadi tabungan, operasional, atau tagihan"
            >
              <span>⚙️ Atur Dompet</span>
            </button>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* 2. SEGMENTED TABS (MOBILE-FIRST)                                     */}
      {/* ===================================================================== */}
      <div className="grid grid-cols-3 gap-1 rounded-2xl bg-surface-card p-1 border border-surface-border text-xs font-bold">
        <button
          type="button"
          onClick={() => setActiveTab("ledger")}
          className={`rounded-xl py-2 transition ${
            activeTab === "ledger"
              ? "bg-terracotta text-white shadow-sm"
              : "text-espresso-muted hover:text-espresso"
          }`}
        >
          📅 Harian
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("fixed")}
          className={`rounded-xl py-2 transition ${
            activeTab === "fixed"
              ? "bg-terracotta text-white shadow-sm"
              : "text-espresso-muted hover:text-espresso"
          }`}
        >
          📋 Tagihan Pasti
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("simulator")}
          className={`rounded-xl py-2 transition ${
            activeTab === "simulator"
              ? "bg-terracotta text-white shadow-sm"
              : "text-espresso-muted hover:text-espresso"
          }`}
        >
          💡 Simulasi
        </button>
      </div>

      {/* ===================================================================== */}
      {/* TAB 1: HARIAN VS IDEAL (SESUAI SPREADSHEET 1 TABEL KANAN)             */}
      {/* ===================================================================== */}
      {activeTab === "ledger" && (
        <div className="rounded-3xl border border-surface-border bg-surface p-4 shadow-sm space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-surface-border">
            <div>
              <h3 className="text-sm font-bold text-espresso">Rekap Pengeluaran Harian</h3>
              <p className="text-[11px] text-espresso-muted">Realisasi belanja vs jatah ideal per tanggal</p>
            </div>
            {ledger && (
              <span className="rounded-lg bg-surface-card px-2 py-1 text-[11px] font-bold text-espresso border border-surface-border">
                Net: {ledger.net_variance >= 0 ? "+" : ""}{formatIDR(ledger.net_variance)}
              </span>
            )}
          </div>

          {isLedgerLoading ? (
            <div className="py-12 flex items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-terracotta" />
            </div>
          ) : ledger && ledger.items.length > 0 ? (
            <div className="divide-y divide-surface-border">
              {ledger.items.map((item: any, idx: number) => (
                <div key={idx} className="py-2.5 flex items-center justify-between text-xs">
                  <div>
                    <div className="flex items-center gap-1.5 font-bold text-espresso">
                      <span>{item.date}</span>
                      <span className="text-[10px] font-normal text-espresso-muted">({item.day_name})</span>
                    </div>
                    <span className="text-[11px] text-espresso-muted block">
                      Plafon Ideal: {formatIDR(item.ideal_spending)}
                    </span>
                    {item.scheduled_income && (
                      <span className="mt-0.5 inline-flex items-center gap-1 text-[10px] font-semibold text-income bg-income/10 px-1.5 py-0.5 rounded-md">
                        <TrendingUp className="h-3 w-3" />
                        +{formatIDR(item.scheduled_income)} ({item.scheduled_income_names?.join(", ")})
                      </span>
                    )}
                  </div>

                  <div className="text-right">
                    <span className="font-bold text-espresso block">
                      {formatIDR(item.total_spent)}
                    </span>
                    <span
                      className={`text-[10px] font-semibold ${
                        item.daily_variance >= 0 ? "text-income" : "text-expense"
                      }`}
                    >
                      {item.daily_variance >= 0 ? "+" : ""}{formatIDR(item.daily_variance)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-8 text-center text-xs text-espresso-muted">
              Belum ada riwayat transaksi pada siklus ini.
            </div>
          )}
        </div>
      )}

      {/* ===================================================================== */}
      {/* TAB 2: TAGIHAN PASTI / FIXED OBLIGATIONS (SESUAI SPREADSHEET 2 KIRI)   */}
      {/* ===================================================================== */}
      {activeTab === "fixed" && (
        <div className="rounded-3xl border border-surface-border bg-surface p-4 shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-surface-border">
            <div>
              <h3 className="text-sm font-bold text-espresso">Pengeluaran Pasti / Rutin</h3>
              <p className="text-[11px] text-espresso-muted">
                Otomatis dicadangkan dari saldo agar jatah belanja tidak terpakai
              </p>
            </div>
            <button
              type="button"
              onClick={() => setIsAddFixedModalOpen(true)}
              className="flex items-center gap-1 rounded-xl bg-terracotta/10 px-2.5 py-1 text-xs font-bold text-terracotta hover:bg-terracotta/20"
            >
              <Plus className="h-3.5 w-3.5" />
              Tambah
            </button>
          </div>

          {summary && (
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="rounded-2xl bg-surface-card p-3 border border-surface-border">
                <span className="text-[10px] text-espresso-muted uppercase font-bold">Total Bulanan</span>
                <span className="mt-0.5 block text-sm font-extrabold text-espresso">
                  {formatIDR(summary.fixed_obligations.total_monthly_fixed)}
                </span>
              </div>
              <div className="rounded-2xl bg-amber/15 p-3 border border-amber/30">
                <span className="text-[10px] text-terracotta uppercase font-bold">Belum Terbayar (Buffer)</span>
                <span className="mt-0.5 block text-sm font-extrabold text-terracotta">
                  {formatIDR(summary.fixed_obligations.unpaid_fixed_buffer)}
                </span>
              </div>
            </div>
          )}

          <div className="space-y-2">
            {summary?.fixed_obligations.items.map((item: any) => (
              <div
                key={item.id}
                className="flex items-center justify-between rounded-2xl border border-surface-border bg-surface-card p-3 transition hover:border-terracotta/40"
              >
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => handleToggleFixed(item.id)}
                    className={`flex h-6 w-6 items-center justify-center rounded-lg border transition ${
                      item.is_paid_this_cycle
                        ? "border-income bg-income text-white shadow-sm"
                        : "border-espresso-muted/40 bg-surface text-transparent"
                    }`}
                    title={item.is_paid_this_cycle ? "Tandai Belum Lunas" : "Tandai Sudah Lunas"}
                  >
                    <Check className="h-4 w-4" />
                  </button>
                  <div>
                    <div className="flex items-center gap-1.5">
                      <span
                        className={`text-xs font-bold block ${
                          item.is_paid_this_cycle ? "line-through text-espresso-muted" : "text-espresso"
                        }`}
                      >
                        {item.name}
                      </span>
                      {item.wallet_name && (
                        <span className="rounded-md bg-amber/20 px-1.5 py-0.2 text-[9px] font-bold text-terracotta border border-amber/30">
                          💳 {item.wallet_name}
                        </span>
                      )}
                    </div>
                    <span className="text-[10px] text-espresso-muted">
                      {item.is_paid_this_cycle
                        ? `✅ Lunas bulan ini${item.wallet_name ? ` (dari ${item.wallet_name})` : ""}`
                        : "⏳ Belum dibayar (Dicadangkan)"}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <span className="text-xs font-bold text-espresso">
                    {formatIDR(item.amount)}
                  </span>
                  <button
                    type="button"
                    onClick={() => handleDeleteFixed(item.id)}
                    className="text-espresso-muted/40 hover:text-expense transition p-1"
                    title="Hapus Tagihan"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* TAB 3: SIMULASI BELANJA "BISA BELI NGGAK?" (SESUAI SPREADSHEET 3)       */}
      {/* ===================================================================== */}
      {activeTab === "simulator" && (
        <div className="space-y-4">
          {/* Simulator Box */}
          <div className="rounded-3xl border border-surface-border bg-surface p-5 shadow-sm space-y-4">
            <div>
              <h3 className="text-sm font-bold text-espresso flex items-center gap-2">
                <Zap className="h-4 w-4 text-amber" />
                Simulasi Belanja ("Bisa Beli Nggak?")
              </h3>
              <p className="text-xs text-espresso-muted mt-0.5">
                Uji dampak pengeluaran sebelum membeli agar tabungan dan jatah hidup Anda tetap aman.
              </p>
            </div>

            <form onSubmit={handleRunSimulation} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-espresso mb-1">Nama Barang / Pengeluaran</label>
                <input
                  type="text"
                  required
                  value={simName}
                  onChange={(e) => setSimName(e.target.value)}
                  placeholder="Misal: Keyboard Mechanical, Soundcard, IEM..."
                  className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-xs font-medium text-espresso placeholder:text-espresso-muted/40 focus:border-terracotta focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-espresso mb-1">Estimasi Harga (Rp)</label>
                <input
                  type="number"
                  required
                  min="1"
                  value={simAmount}
                  onChange={(e) => setSimAmount(e.target.value)}
                  placeholder="500000"
                  className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-sm font-bold text-espresso placeholder:text-espresso-muted/40 focus:border-terracotta focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-espresso mb-1">Sumber Pembiayaan</label>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <button
                    type="button"
                    onClick={() => setSimSource("savings_pool")}
                    className={`rounded-xl py-2 px-3 font-bold border transition text-left ${
                      simSource === "savings_pool"
                        ? "border-terracotta bg-terracotta/10 text-terracotta"
                        : "border-surface-border bg-surface-card text-espresso-muted"
                    }`}
                  >
                    💰 Dari Tabungan
                    <span className="block text-[10px] font-normal text-espresso-muted">
                      Saldo: {formatIDR(summary?.savings_pool_balance)}
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setSimSource("operational_wallet")}
                    className={`rounded-xl py-2 px-3 font-bold border transition text-left ${
                      simSource === "operational_wallet"
                        ? "border-terracotta bg-terracotta/10 text-terracotta"
                        : "border-surface-border bg-surface-card text-espresso-muted"
                    }`}
                  >
                    👛 Dari Uang Jajan
                    <span className="block text-[10px] font-normal text-espresso-muted">
                      Plafon: {formatIDR(summary?.today_metrics.ideal_spending_today)}/hr
                    </span>
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={isSimulating}
                className="w-full rounded-xl bg-terracotta py-2.5 text-xs font-bold text-white shadow-md shadow-terracotta/20 hover:bg-terracotta-hover transition disabled:opacity-50"
              >
                {isSimulating ? (
                  <span className="flex items-center justify-center gap-1.5">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Menghitung Dampak Finansial...
                  </span>
                ) : (
                  "⚡ Simulasikan Sekarang"
                )}
              </button>
            </form>

            {/* Hasil Prediksi Simulasi */}
            {simResult && (
              <div
                className={`rounded-2xl border p-4 space-y-2 text-xs animate-fadeIn ${
                  simResult.verdict === "safe"
                    ? "border-income/40 bg-income/10 text-espresso"
                    : simResult.verdict === "warning"
                    ? "border-amber/40 bg-amber/15 text-espresso"
                    : "border-expense/40 bg-expense/10 text-espresso"
                }`}
              >
                <div className="flex items-center gap-1.5 font-extrabold text-sm">
                  {simResult.verdict === "safe" ? (
                    <CheckCircle2 className="h-4 w-4 text-income" />
                  ) : simResult.verdict === "warning" ? (
                    <AlertTriangle className="h-4 w-4 text-amber" />
                  ) : (
                    <ShieldAlert className="h-4 w-4 text-expense" />
                  )}
                  <span>{simResult.headline}</span>
                </div>
                <p className="text-xs leading-relaxed text-espresso-muted">{simResult.explanation}</p>

                <div className="pt-2 grid grid-cols-2 gap-2 text-[11px] border-t border-espresso/10">
                  <div>
                    <span className="text-espresso-muted block">Tabungan Sesudahnya:</span>
                    <span className="font-bold text-espresso">{formatIDR(simResult.projected_savings_after)}</span>
                  </div>
                  <div>
                    <span className="text-espresso-muted block">Jatah Harian Sesudahnya:</span>
                    <span className="font-bold text-espresso">
                      {formatIDR(simResult.projected_daily_ideal_after)}/hari
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Wishlist List Sesuai Spreadsheet 3 */}
          <div className="rounded-3xl border border-surface-border bg-surface p-4 shadow-sm space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-surface-border">
              <div>
                <h3 className="text-sm font-bold text-espresso">Daftar Impian Belanja (Wishlist)</h3>
                <p className="text-[11px] text-espresso-muted">Rencana belanja besar yang diuji terhadap tabungan</p>
              </div>
              <button
                type="button"
                onClick={() => setIsAddWishlistModalOpen(true)}
                className="flex items-center gap-1 rounded-xl bg-terracotta/10 px-2.5 py-1 text-xs font-bold text-terracotta hover:bg-terracotta/20"
              >
                <Plus className="h-3.5 w-3.5" />
                Tambah
              </button>
            </div>

            <div className="space-y-2">
              {wishlists?.map((item: any) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between rounded-2xl border border-surface-border bg-surface-card p-3 text-xs"
                >
                  <div>
                    <span className="font-bold text-espresso block">{item.item_name}</span>
                    <span className="text-[11px] text-espresso-muted font-semibold">
                      {formatIDR(item.estimated_price)}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => quickSimulate(item.item_name, item.estimated_price)}
                      className="rounded-lg bg-amber/20 px-2.5 py-1 text-[11px] font-bold text-terracotta hover:bg-amber/30 transition"
                    >
                      Uji Dampak
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDeleteWishlist(item.id)}
                      className="text-espresso-muted/40 hover:text-expense transition p-1"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* MODAL 1: ATUR BLUEPRINT KEUANGAN                                      */}
      {/* ===================================================================== */}
      {isPlanModalOpen && (() => {
        const totalStreamMonthly = (incomeStreams || []).reduce(
          (acc: number, s: any) => acc + (parseFloat(s.monthly_equivalent) || 0),
          0
        );
        const cycleDays = summary?.cycle_info?.total_days || 30;
        const parsedAmt = parseFloat(streamAmount) || 0;
        let estimatedStreamEquivalent = 0;
        if (streamFrequency === "daily") {
          estimatedStreamEquivalent = parsedAmt * cycleDays;
        } else if (streamFrequency === "weekly") {
          estimatedStreamEquivalent = parsedAmt * (cycleDays / 7);
        } else if (streamFrequency === "biweekly") {
          estimatedStreamEquivalent = parsedAmt * (cycleDays / 14);
        } else {
          estimatedStreamEquivalent = parsedAmt;
        }

        const daysOfWeek = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"];

        return (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
            <div className="w-full max-w-md max-h-[90vh] overflow-y-auto rounded-3xl border border-surface-border bg-surface p-5 sm:p-6 shadow-2xl space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-surface-border">
                <div>
                  <h3 className="text-base font-bold text-espresso">Atur Blueprint Finansial</h3>
                  <p className="text-[11px] text-espresso-muted">Alur pendapatan multi-sumber, jatah harian & tabungan</p>
                </div>
                <button
                  type="button"
                  onClick={() => setIsPlanModalOpen(false)}
                  className="rounded-lg p-1 text-espresso-muted hover:bg-surface-card hover:text-espresso"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              {/* 1. SEKSI SUMBER PENDAPATAN (MULTI-STREAM) */}
              <div className="rounded-2xl border border-surface-border bg-surface-card/60 p-3.5 space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-xs font-bold text-espresso block">Sumber Pendapatan</span>
                    <span className="text-[10px] text-espresso-muted">
                      {incomeStreams && incomeStreams.length > 0
                        ? `${incomeStreams.length} aliran aktif (Gaji, uang saku, warung, dll)`
                        : "Bisa 1 atau lebih aliran (harian/mingguan/bulanan)"}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setIsAddStreamOpen(!isAddStreamOpen)}
                    className="flex items-center gap-1 rounded-xl bg-terracotta/15 px-2.5 py-1 text-[11px] font-bold text-terracotta hover:bg-terracotta/25 transition"
                  >
                    <Plus className="h-3 w-3" />
                    <span>{isAddStreamOpen ? "Tutup Form" : "Tambah"}</span>
                  </button>
                </div>

                {/* Sub-form Tambah Aliran Baru */}
                {isAddStreamOpen && (
                  <form onSubmit={handleCreateStream} className="rounded-xl border border-terracotta/30 bg-surface p-3 space-y-2.5 shadow-sm">
                    <span className="text-[11px] font-bold text-terracotta block">
                      + Tambah Sumber Pendapatan Baru
                    </span>

                    <div>
                      <label className="block text-[10px] font-semibold text-espresso mb-0.5">Nama Sumber</label>
                      <input
                        type="text"
                        required
                        value={streamName}
                        onChange={(e) => setStreamName(e.target.value)}
                        placeholder="Contoh: Uang Mingguan Kos, Gaji Utama, Freelance"
                        className="w-full rounded-lg border border-surface-border bg-surface-card px-2.5 py-1.5 text-xs text-espresso focus:outline-none focus:border-terracotta"
                      />
                    </div>

                    <div>
                      <label className="block text-[10px] font-semibold text-espresso mb-0.5">Nominal per Penerimaan (Rp)</label>
                      <input
                        type="number"
                        required
                        value={streamAmount}
                        onChange={(e) => setStreamAmount(e.target.value)}
                        placeholder="Contoh: 415258"
                        className="w-full rounded-lg border border-surface-border bg-surface-card px-2.5 py-1.5 text-xs font-bold text-espresso focus:outline-none focus:border-terracotta"
                      />
                    </div>

                    <div>
                      <label className="block text-[10px] font-semibold text-espresso mb-1">Siklus Penerimaan</label>
                      <div className="grid grid-cols-4 gap-1.5">
                        {[
                          { id: "daily", label: "Harian" },
                          { id: "weekly", label: "Mingguan" },
                          { id: "biweekly", label: "2-Mgg" },
                          { id: "monthly", label: "Bulanan" },
                        ].map((item) => (
                          <button
                            key={item.id}
                            type="button"
                            onClick={() => setStreamFrequency(item.id as any)}
                            className={`rounded-lg py-1 text-[11px] font-bold border transition ${
                              streamFrequency === item.id
                                ? "bg-terracotta text-white border-terracotta shadow-xs"
                                : "bg-surface-card text-espresso-muted border-surface-border hover:text-espresso"
                            }`}
                          >
                            {item.label}
                          </button>
                        ))}
                      </div>
                    </div>

                    {streamFrequency === "weekly" && (
                      <div>
                        <label className="block text-[10px] font-semibold text-espresso mb-0.5">Hari Masuk / Cair</label>
                        <select
                          value={streamReceiveDay}
                          onChange={(e) => setStreamReceiveDay(parseInt(e.target.value))}
                          className="w-full rounded-lg border border-surface-border bg-surface-card px-2.5 py-1.5 text-xs text-espresso focus:outline-none focus:border-terracotta"
                        >
                          {daysOfWeek.map((day, idx) => (
                            <option key={idx} value={idx}>
                              Setiap hari {day}
                            </option>
                          ))}
                        </select>
                      </div>
                    )}

                    {streamFrequency === "monthly" && (
                      <div>
                        <label className="block text-[10px] font-semibold text-espresso mb-0.5">Tanggal Cair (1-31)</label>
                        <input
                          type="number"
                          min="1"
                          max="31"
                          value={streamReceiveDay || 1}
                          onChange={(e) => setStreamReceiveDay(parseInt(e.target.value) || 1)}
                          className="w-full rounded-lg border border-surface-border bg-surface-card px-2.5 py-1.5 text-xs text-espresso focus:outline-none focus:border-terracotta"
                        />
                      </div>
                    )}

                    {parsedAmt > 0 && (
                      <div className="rounded-lg bg-amber/15 px-2.5 py-1.5 text-[11px] text-terracotta font-semibold">
                        Estimasi setara bulanan: ~{formatIDR(estimatedStreamEquivalent)} / siklus ({cycleDays} hari)
                      </div>
                    )}

                    <div className="flex gap-2 pt-1">
                      <button
                        type="button"
                        onClick={() => setIsAddStreamOpen(false)}
                        className="flex-1 rounded-lg bg-surface-card py-1.5 text-[11px] font-semibold text-espresso-muted"
                      >
                        Batal
                      </button>
                      <button
                        type="submit"
                        disabled={isSavingStream}
                        className="flex-1 rounded-lg bg-terracotta py-1.5 text-[11px] font-bold text-white hover:bg-terracotta-hover transition disabled:opacity-50"
                      >
                        {isSavingStream ? "Menyimpan..." : "Simpan Aliran"}
                      </button>
                    </div>
                  </form>
                )}

                {/* List Aliran yang sudah terdaftar */}
                {incomeStreams && incomeStreams.length > 0 ? (
                  <div className="space-y-1.5">
                    {incomeStreams.map((s: any) => {
                      const freqLabel = {
                        daily: "Harian",
                        weekly: "Mingguan",
                        biweekly: "2-Mgg",
                        monthly: "Bulanan",
                      }[s.frequency] || s.frequency;

                      const freqBadgeColor = {
                        daily: "bg-amber/20 text-terracotta border-amber/30",
                        weekly: "bg-income/15 text-income border-income/30",
                        biweekly: "bg-purple-100 text-purple-800 border-purple-200",
                        monthly: "bg-espresso/10 text-espresso border-espresso/20",
                      }[s.frequency] || "bg-surface text-espresso";

                      return (
                        <div
                          key={s.id}
                          className="flex items-center justify-between rounded-xl border border-surface-border bg-surface px-3 py-2 text-xs shadow-2xs"
                        >
                          <div>
                            <div className="flex items-center gap-1.5 font-bold text-espresso">
                              <span>{s.name}</span>
                              <span className={`rounded-md border px-1.5 py-0.2 text-[9px] font-semibold uppercase ${freqBadgeColor}`}>
                                {freqLabel}
                              </span>
                            </div>
                            <div className="flex items-center gap-1.5 mt-0.5 text-[10px] text-espresso-muted">
                              <span className="font-semibold text-espresso">
                                {formatIDR(s.amount)}/{s.frequency === "daily" ? "hari" : s.frequency === "weekly" ? "minggu" : s.frequency === "biweekly" ? "2-mgg" : "bln"}
                              </span>
                              <span>•</span>
                              <span>~{formatIDR(s.monthly_equivalent)}/bln</span>
                            </div>
                          </div>
                          <button
                            type="button"
                            onClick={() => handleDeleteStream(s.id)}
                            className="rounded-lg p-1.5 text-espresso-muted hover:bg-expense/10 hover:text-expense transition"
                            title="Hapus sumber pendapatan ini"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      );
                    })}

                    <div className="pt-1 flex items-center justify-between text-xs font-bold text-espresso border-t border-surface-border">
                      <span className="text-[11px] text-espresso-muted">Total Proyeksi Bulanan:</span>
                      <span className="text-sm text-terracotta">{formatIDR(totalStreamMonthly)}</span>
                    </div>
                  </div>
                ) : (
                  <p className="text-[11px] text-espresso-muted italic">
                    Belum ada rincian aliran. Anda dapat memasukkan nominal total pendapatan langsung di bawah atau klik tombol Tambah di atas.
                  </p>
                )}
              </div>

              {/* 2. FORM BLUEPRINT KEUANGAN */}
              <form onSubmit={handleSavePlan} className="space-y-3 pt-1">
                <div>
                  <label className="block text-xs font-semibold text-espresso mb-1">
                    Pendapatan Bulanan (Rp)
                  </label>
                  <input
                    type="number"
                    required
                    value={totalStreamMonthly > 0 ? totalStreamMonthly : monthlyIncome}
                    onChange={(e) => setMonthlyIncome(e.target.value)}
                    disabled={totalStreamMonthly > 0}
                    placeholder="2600000"
                    className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-xs font-bold text-espresso focus:outline-none focus:border-terracotta disabled:opacity-75 disabled:cursor-not-allowed"
                  />
                  {totalStreamMonthly > 0 ? (
                    <span className="text-[10px] text-income mt-0.5 block font-medium">
                      ✓ Dihitung otomatis dari akumulasi sumber pendapatan di atas.
                    </span>
                  ) : (
                    <span className="text-[10px] text-espresso-muted mt-0.5 block">
                      Masukkan nominal total jika tidak merinci per sumber.
                    </span>
                  )}
                </div>

                <div>
                  <label className="block text-xs font-semibold text-espresso mb-1">
                    Patokan Belanja Harian Normal (Rp)
                  </label>
                  <input
                    type="number"
                    required
                    value={dailyLivingBudget}
                    onChange={(e) => setDailyLivingBudget(e.target.value)}
                    placeholder="45000"
                    className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-xs font-bold text-espresso focus:outline-none focus:border-terracotta"
                  />
                  <span className="text-[10px] text-espresso-muted mt-0.5 block">
                    Misal: Makan Rp45.000 x 28 hari = Rp1.260.000
                  </span>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-espresso mb-1">Target Tabungan Bulanan (Rp)</label>
                  <input
                    type="number"
                    required
                    value={monthlySavingsTarget}
                    onChange={(e) => setMonthlySavingsTarget(e.target.value)}
                    placeholder="695000"
                    className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-xs font-bold text-espresso focus:outline-none focus:border-terracotta"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-espresso mb-1">Tanggal Mulai Siklus / Gajian</label>
                  <input
                    type="number"
                    min="1"
                    max="31"
                    required
                    value={cycleStartDay}
                    onChange={(e) => setCycleStartDay(parseInt(e.target.value) || 1)}
                    className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-xs font-bold text-espresso focus:outline-none focus:border-terracotta"
                  />
                  <span className="text-[10px] text-espresso-muted mt-0.5 block">
                    Pilih 1 untuk awal bulan standar, atau tanggal gajian (misal 25).
                  </span>
                </div>

                <div className="flex gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setIsPlanModalOpen(false)}
                    className="flex-1 rounded-xl bg-surface-card py-2 text-xs font-semibold text-espresso-muted hover:text-espresso"
                  >
                    Batal
                  </button>
                  <button
                    type="submit"
                    disabled={isSavingPlan}
                    className="flex-1 rounded-xl bg-terracotta py-2 text-xs font-bold text-white hover:bg-terracotta-hover transition disabled:opacity-50"
                  >
                    {isSavingPlan ? "Menyimpan..." : "Simpan Blueprint"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        );
      })()}

      {/* ===================================================================== */}
      {/* MODAL 2: TAMBAH TAGIHAN PASTI                                         */}
      {/* ===================================================================== */}
      {isAddFixedModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="w-full max-w-sm rounded-3xl border border-surface-border bg-surface p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-espresso">Tambah Tagihan Pasti</h3>
            <form onSubmit={handleCreateFixed} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-espresso mb-1">Nama Tagihan / Pengeluaran</label>
                <input
                  type="text"
                  required
                  value={fixedName}
                  onChange={(e) => setFixedName(e.target.value)}
                  placeholder="Misal: iCloud, Pulsa, Galon, Token..."
                  className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-xs font-medium text-espresso focus:outline-none focus:border-terracotta"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-espresso mb-1">Nominal per Siklus (Rp)</label>
                <input
                  type="number"
                  required
                  min="1"
                  value={fixedAmount}
                  onChange={(e) => setFixedAmount(e.target.value)}
                  placeholder="170000"
                  className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-sm font-bold text-espresso focus:outline-none focus:border-terracotta"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-espresso mb-1">
                  Dompet Pembayar (Opsional)
                </label>
                <select
                  value={fixedWalletId}
                  onChange={(e) => setFixedWalletId(e.target.value)}
                  className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-xs font-medium text-espresso focus:outline-none focus:border-terracotta"
                >
                  <option value="">-- Bebas / Otomatis dari Operasional --</option>
                  {wallets?.map((w: any) => (
                    <option key={w.id} value={w.id}>
                      {w.name} ({w.purpose === "subscription" ? "Tagihan" : w.purpose === "savings" ? "Tabungan" : "Operasional"}) - {formatIDR(w.balance)}
                    </option>
                  ))}
                </select>
                <span className="text-[10px] text-espresso-muted mt-1 block">
                  Pilih dompet khusus tagihan (misal: Subscription) agar dicadangkan dari dompet tersebut dan dipotong saat ditandai lunas.
                </span>
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsAddFixedModalOpen(false)}
                  className="flex-1 rounded-xl bg-surface-card py-2 text-xs font-semibold text-espresso-muted hover:text-espresso"
                >
                  Batal
                </button>
                <button
                  type="submit"
                  disabled={isSavingFixed}
                  className="flex-1 rounded-xl bg-terracotta py-2 text-xs font-bold text-white hover:bg-terracotta-hover transition disabled:opacity-50"
                >
                  {isSavingFixed ? "Menyimpan..." : "Simpan Tagihan"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* MODAL 3: TAMBAH WISHLIST                                              */}
      {/* ===================================================================== */}
      {isAddWishlistModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="w-full max-w-sm rounded-3xl border border-surface-border bg-surface p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-espresso">Tambah Barang Wishlist</h3>
            <form onSubmit={handleCreateWishlist} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-espresso mb-1">Nama Barang</label>
                <input
                  type="text"
                  required
                  value={wishlistName}
                  onChange={(e) => setWishlistName(e.target.value)}
                  placeholder="Misal: Keyboard Mechanical, Soundcard..."
                  className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-xs font-medium text-espresso focus:outline-none focus:border-terracotta"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-espresso mb-1">Estimasi Harga (Rp)</label>
                <input
                  type="number"
                  required
                  min="1"
                  value={wishlistPrice}
                  onChange={(e) => setWishlistPrice(e.target.value)}
                  placeholder="500000"
                  className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-sm font-bold text-espresso focus:outline-none focus:border-terracotta"
                />
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsAddWishlistModalOpen(false)}
                  className="flex-1 rounded-xl bg-surface-card py-2 text-xs font-semibold text-espresso-muted hover:text-espresso"
                >
                  Batal
                </button>
                <button
                  type="submit"
                  disabled={isSavingWishlist}
                  className="flex-1 rounded-xl bg-terracotta py-2 text-xs font-bold text-white hover:bg-terracotta-hover transition disabled:opacity-50"
                >
                  {isSavingWishlist ? "Menyimpan..." : "Simpan ke Wishlist"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      {/* ===================================================================== */}
      {/* MODAL 4: ATUR PERUNTUKAN DOMPET LANGSUNG                              */}
      {/* ===================================================================== */}
      {isWalletConfigModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="w-full max-w-sm rounded-3xl border border-surface-border bg-surface p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-surface-border pb-3">
              <div>
                <h3 className="text-base font-bold text-espresso">Atur Peruntukan Dompet</h3>
                <p className="text-xs text-espresso-muted">Pilih dompet yang jadi tabungan atau operasional</p>
              </div>
              <button
                type="button"
                onClick={() => setIsWalletConfigModalOpen(false)}
                className="rounded-lg p-1 text-espresso-muted hover:bg-surface-card hover:text-espresso"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 max-h-[60vh] overflow-y-auto pr-1">
              {wallets?.map((w: any) => (
                <div
                  key={w.id}
                  className="rounded-2xl border border-surface-border bg-surface-card p-3 space-y-2.5"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-xs font-bold text-espresso block">{w.name}</span>
                      <span className="text-[10px] text-espresso-muted uppercase">{w.type}</span>
                    </div>
                    <span className="text-xs font-extrabold text-espresso">
                      {formatIDR(w.balance)}
                    </span>
                  </div>

                  {/* 3 Option Pills */}
                  <div className="grid grid-cols-3 gap-1 pt-0.5 text-[10px] font-bold">
                    <button
                      type="button"
                      onClick={async () => {
                        await api.put(`/api/v1/wallets/${w.id}`, { purpose: "operational" });
                        refetchSummary();
                        refetchLedger();
                        queryClient.invalidateQueries({ queryKey: ["wallets"] });
                        queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
                      }}
                      className={`rounded-xl py-1.5 px-1.5 transition text-center border ${
                        (w.purpose || "operational") === "operational"
                          ? "bg-terracotta text-white border-terracotta shadow-xs"
                          : "bg-surface text-espresso-muted border-surface-border hover:text-espresso"
                      }`}
                    >
                      💼 Operasional
                    </button>

                    <button
                      type="button"
                      onClick={async () => {
                        await api.put(`/api/v1/wallets/${w.id}`, { purpose: "savings" });
                        refetchSummary();
                        refetchLedger();
                        queryClient.invalidateQueries({ queryKey: ["wallets"] });
                        queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
                      }}
                      className={`rounded-xl py-1.5 px-1.5 transition text-center border ${
                        w.purpose === "savings"
                          ? "bg-income text-white border-income shadow-xs"
                          : "bg-surface text-espresso-muted border-surface-border hover:text-income"
                      }`}
                    >
                      💰 Tabungan
                    </button>

                    <button
                      type="button"
                      onClick={async () => {
                        await api.put(`/api/v1/wallets/${w.id}`, { purpose: "subscription" });
                        refetchSummary();
                        refetchLedger();
                        queryClient.invalidateQueries({ queryKey: ["wallets"] });
                        queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
                      }}
                      className={`rounded-xl py-1.5 px-1.5 transition text-center border ${
                        w.purpose === "subscription"
                          ? "bg-amber text-espresso border-amber shadow-xs"
                          : "bg-surface text-espresso-muted border-surface-border hover:text-terracotta"
                      }`}
                    >
                      💳 Tagihan
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <div className="pt-2 border-t border-surface-border">
              <button
                type="button"
                onClick={() => setIsWalletConfigModalOpen(false)}
                className="w-full rounded-xl bg-terracotta py-2 text-xs font-bold text-white hover:bg-terracotta-hover transition"
              >
                Selesai
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

