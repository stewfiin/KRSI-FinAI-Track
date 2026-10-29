"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
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

  // Add Fixed Expense Modal State
  const [isAddFixedModalOpen, setIsAddFixedModalOpen] = useState(false);
  const [fixedName, setFixedName] = useState("");
  const [fixedAmount, setFixedAmount] = useState("");
  const [isSavingFixed, setIsSavingFixed] = useState(false);

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

  const handleToggleFixed = async (id: string) => {
    try {
      await api.post(`/api/v1/forecast/fixed-expenses/${id}/toggle-paid`);
      refetchSummary();
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
      });
      setIsAddFixedModalOpen(false);
      setFixedName("");
      setFixedAmount("");
      refetchSummary();
    } catch (err: any) {
      alert("Gagal menambah tagihan pasti.");
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
                <span>Daya Tahan Uang</span>
              </div>
              <span className="mt-1 block text-sm font-extrabold text-espresso">
                {summary.runway_prediction.predicted_runway_days} Hari
              </span>
              <span className="text-[10px] text-espresso-muted block truncate">
                {summary.runway_prediction.is_runway_safe ? "✅ Cukup sampai gajian" : "⚠️ Cepat habis!"}
              </span>
            </div>

            <div className="rounded-2xl border border-surface-border bg-surface p-2.5">
              <div className="flex items-center gap-1.5 text-espresso-muted text-[11px]">
                <Sparkles className="h-3.5 w-3.5 text-income" />
                <span>Prediksi Tabungan</span>
              </div>
              <span className="mt-1 block text-sm font-extrabold text-income">
                {formatIDR(summary.end_of_month_forecast.projected_end_savings)}
              </span>
              <span className="text-[10px] text-espresso-muted block truncate">
                Target: {formatIDR(summary.end_of_month_forecast.target_savings)}
              </span>
            </div>
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
                    <span
                      className={`text-xs font-bold block ${
                        item.is_paid_this_cycle ? "line-through text-espresso-muted" : "text-espresso"
                      }`}
                    >
                      {item.name}
                    </span>
                    <span className="text-[10px] text-espresso-muted">
                      {item.is_paid_this_cycle ? "✅ Lunas bulan ini" : "⏳ Belum dibayar (Dicadangkan)"}
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
      {isPlanModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="w-full max-w-sm rounded-3xl border border-surface-border bg-surface p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-surface-border">
              <h3 className="text-base font-bold text-espresso">Atur Blueprint Finansial</h3>
              <button
                type="button"
                onClick={() => setIsPlanModalOpen(false)}
                className="rounded-lg p-1 text-espresso-muted hover:bg-surface-card hover:text-espresso"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleSavePlan} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-espresso mb-1">Pendapatan Bulanan (Rp)</label>
                <input
                  type="number"
                  required
                  value={monthlyIncome}
                  onChange={(e) => setMonthlyIncome(e.target.value)}
                  placeholder="2600000"
                  className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-xs font-bold text-espresso focus:outline-none focus:border-terracotta"
                />
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
      )}

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
    </div>
  );
}

