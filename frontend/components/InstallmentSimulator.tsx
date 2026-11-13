"use client";

import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  Calendar,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  CreditCard,
  Loader2,
  PiggyBank,
  Plus,
  ShieldAlert,
  Sparkles,
  TrendingDown,
  Wallet,
  Zap,
} from "lucide-react";
import {
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
} from "recharts";
import { api } from "@/lib/api";

interface AmortizationRow {
  month_index: number;
  due_date: string;
  principal_amount: number | string;
  interest_amount: number | string;
  fee_amount: number | string;
  total_payment: number | string;
  remaining_principal: number | string;
}

interface TenorComparison {
  tenor_months: number;
  monthly_installment: number | string;
  total_interest_and_fees: number | string;
  total_payment: number | string;
  income_ratio_percent: number;
  projected_daily_ideal_after: number | string;
  verdict: "safe" | "warning" | "danger";
}

interface InstallmentSimulationResponse {
  item_name: string;
  item_price: number | string;
  down_payment: number | string;
  dp_source: string;
  tenor_months: number;
  interest_type: string;
  interest_rate: number | string;
  interest_rate_period: string;
  admin_fee: number | string;
  monthly_fee: number | string;
  principal_amount: number | string;
  upfront_cash_needed: number | string;
  monthly_installment: number | string;
  first_month_installment: number | string;
  last_month_installment: number | string;
  total_interest: number | string;
  total_fees: number | string;
  total_installment_payments: number | string;
  total_cost: number | string;
  effective_markup_percent: number;
  is_dp_affordable: boolean;
  is_monthly_affordable: boolean;
  verdict: "safe" | "warning" | "danger";
  headline: string;
  explanation: string;
  recommendations: string[];
  current_savings: number | string;
  projected_savings_after_dp: number | string;
  current_safe_to_spend: number | string;
  projected_safe_to_spend_after_dp: number | string;
  current_monthly_income: number | string;
  current_monthly_fixed: number | string;
  current_monthly_free_cashflow: number | string;
  projected_monthly_free_cashflow: number | string;
  installment_to_income_ratio: number;
  current_daily_ideal: number | string;
  projected_daily_ideal_after: number | string;
  amortization_schedule: AmortizationRow[];
  tenor_comparisons: TenorComparison[];
}

interface InstallmentSimulatorProps {
  summary: any;
  wallets?: any[];
  prefillItem?: { name: string; price: number; nonce?: number } | null;
  formatIDR: (val: number | string | undefined) => string;
  onAppliedToPlanned?: () => void;
  onSavedToWishlist?: () => void;
}

export function InstallmentSimulator({
  summary,
  wallets,
  prefillItem,
  formatIDR,
  onAppliedToPlanned,
  onSavedToWishlist,
}: InstallmentSimulatorProps) {
  const [itemName, setItemName] = useState("");
  const [itemPrice, setItemPrice] = useState("");
  const [dpMode, setDpMode] = useState<"percent" | "amount">("percent");
  const [dpPercent, setDpPercent] = useState("20");
  const [dpAmount, setDpAmount] = useState("");
  const [dpSource, setDpSource] = useState<"savings_pool" | "operational_wallet">("savings_pool");

  const [tenorMonths, setTenorMonths] = useState<number>(12);
  const [interestType, setInterestType] = useState<"zero" | "flat" | "effective">("flat");
  const [interestRate, setInterestRate] = useState("1.5");
  const [interestRatePeriod, setInterestRatePeriod] = useState<"monthly" | "annual">("monthly");

  const [showAdvanced, setShowAdvanced] = useState(false);
  const [adminFee, setAdminFee] = useState("");
  const [monthlyFee, setMonthlyFee] = useState("");
  const [startDate, setStartDate] = useState(() => new Date().toISOString().split("T")[0]);
  const [dueDayOfMonth, setDueDayOfMonth] = useState("");

  const [isSimulating, setIsSimulating] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [result, setResult] = useState<InstallmentSimulationResponse | null>(null);
  const [showSchedule, setShowSchedule] = useState(false);

  // Aksi lanjutan: Jadwalkan ke Proyeksi / Wishlist
  const [selectedWalletId, setSelectedWalletId] = useState("");
  const [includeDpInPlan, setIncludeDpInPlan] = useState(true);
  const [isApplying, setIsApplying] = useState(false);
  const [applySuccessMsg, setApplySuccessMsg] = useState<string | null>(null);
  const [isSavingWishlist, setIsSavingWishlist] = useState(false);
  const [wishlistSavedMsg, setWishlistSavedMsg] = useState<string | null>(null);

  useEffect(() => {
    if (prefillItem) {
      setItemName(prefillItem.name);
      setItemPrice(String(prefillItem.price));
      setResult(null);
      setErrorMsg(null);
      setApplySuccessMsg(null);
      setWishlistSavedMsg(null);
    }
  }, [prefillItem]);

  const parsedPrice = parseFloat(itemPrice) || 0;
  const computedDownPayment = useMemo(() => {
    if (dpMode === "percent") {
      const pct = Math.max(0, Math.min(99, parseFloat(dpPercent) || 0));
      return Math.round((parsedPrice * pct) / 100);
    }
    return Math.max(0, parseFloat(dpAmount) || 0);
  }, [dpMode, dpPercent, dpAmount, parsedPrice]);

  const buildPayload = (overrideTenor?: number) => ({
    item_name: itemName.trim(),
    item_price: parsedPrice,
    down_payment: computedDownPayment,
    dp_source: dpSource,
    tenor_months: overrideTenor ?? tenorMonths,
    interest_type: interestType,
    interest_rate: interestType === "zero" ? 0 : parseFloat(interestRate) || 0,
    interest_rate_period: interestRatePeriod,
    admin_fee: parseFloat(adminFee) || 0,
    monthly_fee: parseFloat(monthlyFee) || 0,
    start_date: startDate || undefined,
    due_day_of_month: dueDayOfMonth ? parseInt(dueDayOfMonth, 10) : undefined,
  });

  const runSimulation = async (overrideTenor?: number) => {
    if (!itemName.trim() || parsedPrice <= 0) {
      setErrorMsg("Masukkan nama barang dan harga barang yang valid.");
      return;
    }
    if (computedDownPayment >= parsedPrice) {
      setErrorMsg("Uang muka (DP) harus lebih kecil dari harga barang.");
      return;
    }

    setIsSimulating(true);
    setErrorMsg(null);
    setApplySuccessMsg(null);
    setWishlistSavedMsg(null);

    try {
      const res = await api.post("/api/v1/forecast/simulate-installment", buildPayload(overrideTenor));
      setResult(res.data);
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.detail || "Gagal menghitung simulasi cicilan.");
    } finally {
      setIsSimulating(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await runSimulation();
  };

  const handleSelectComparisonTenor = async (newTenor: number) => {
    setTenorMonths(newTenor);
    await runSimulation(newTenor);
  };

  const handleApplyToPlanned = async () => {
    if (!result) return;
    setIsApplying(true);
    setApplySuccessMsg(null);
    setErrorMsg(null);
    try {
      const res = await api.post("/api/v1/forecast/simulate-installment/apply-to-planned", {
        ...buildPayload(),
        wallet_id: selectedWalletId || null,
        include_down_payment: includeDpInPlan,
      });
      setApplySuccessMsg(res.data.message);
      onAppliedToPlanned?.();
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.detail || "Gagal menjadwalkan cicilan ke proyeksi.");
    } finally {
      setIsApplying(false);
    }
  };

  const handleSaveWishlist = async () => {
    if (!itemName.trim() || parsedPrice <= 0) return;
    setIsSavingWishlist(true);
    setWishlistSavedMsg(null);
    try {
      await api.post("/api/v1/forecast/wishlists", {
        item_name: itemName.trim(),
        estimated_price: parsedPrice,
        priority: "medium",
        target_source: dpSource,
      });
      setWishlistSavedMsg(`"${itemName.trim()}" ditambahkan ke Wishlist.`);
      onSavedToWishlist?.();
    } catch {
      setErrorMsg("Gagal menyimpan ke Wishlist.");
    } finally {
      setIsSavingWishlist(false);
    }
  };

  const chartData = useMemo(() => {
    if (!result) return [];
    const principal = Number(result.principal_amount) || 0;
    const dp = Number(result.down_payment) || 0;
    const interestAndFees = (Number(result.total_interest) || 0) + (Number(result.total_fees) || 0);
    return [
      { name: "Pokok Pinjaman", value: principal, color: "#0D0F17" },
      ...(dp > 0 ? [{ name: "Uang Muka (DP)", value: dp, color: "#10B981" }] : []),
      ...(interestAndFees > 0 ? [{ name: "Bunga & Biaya", value: interestAndFees, color: "#F43F5E" }] : []),
    ];
  }, [result]);

  return (
    <div className="space-y-4">
      {/* Form Simulasi Cicilan */}
      <div className="rounded-3xl border border-surface-border bg-white p-5 sm:p-6 shadow-xs space-y-4">
        <div className="flex items-start justify-between gap-2">
          <div>
            <h3 className="text-sm font-black text-espresso flex items-center gap-2">
              <CreditCard className="h-4 w-4 text-[#0D0F17]" />
              Simulasi Cicilan & Uji Kelayakan
            </h3>
            <p className="text-[11px] text-espresso-muted">
              Hitung cicilan 0%, Flat, atau Efektif serta dampaknya terhadap cashflow & jatah harian Anda
            </p>
          </div>
          <span className="rounded-full bg-[#C8F526]/40 border border-[#C8F526] px-2.5 py-0.5 text-[10px] font-black text-black shrink-0">
            Smart DSR
          </span>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Nama & Harga */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-bold text-espresso mb-1">Nama Barang / Kebutuhan</label>
              <input
                type="text"
                required
                value={itemName}
                onChange={(e) => setItemName(e.target.value)}
                placeholder="Misal: Laptop Kerja, Motor, HP..."
                className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-xs font-medium text-espresso placeholder:text-espresso-muted/40 focus:border-[#0D0F17] focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-espresso mb-1">Harga Barang (Rp)</label>
              <input
                type="number"
                required
                min="1"
                value={itemPrice}
                onChange={(e) => setItemPrice(e.target.value)}
                placeholder="12000000"
                className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-sm font-bold text-espresso placeholder:text-espresso-muted/40 focus:border-[#0D0F17] focus:outline-none"
              />
            </div>
          </div>

          {/* Uang Muka (DP) */}
          <div className="rounded-2xl border border-surface-border bg-surface-card/60 p-3.5 space-y-2.5">
            <div className="flex items-center justify-between gap-2">
              <label className="text-xs font-bold text-espresso">
                Uang Muka / DP{" "}
                {parsedPrice > 0 && (
                  <span className="text-espresso-muted font-semibold">
                    ({formatIDR(computedDownPayment)})
                  </span>
                )}
              </label>
              <div className="inline-flex rounded-xl bg-white border border-surface-border p-0.5 text-[10px] font-bold">
                <button
                  type="button"
                  onClick={() => setDpMode("percent")}
                  className={`px-2 py-1 rounded-lg transition ${
                    dpMode === "percent" ? "bg-[#0D0F17] text-[#C8F526]" : "text-espresso-muted"
                  }`}
                >
                  % Persen
                </button>
                <button
                  type="button"
                  onClick={() => setDpMode("amount")}
                  className={`px-2 py-1 rounded-lg transition ${
                    dpMode === "amount" ? "bg-[#0D0F17] text-[#C8F526]" : "text-espresso-muted"
                  }`}
                >
                  Rp Nominal
                </button>
              </div>
            </div>

            {dpMode === "percent" ? (
              <div className="flex flex-wrap items-center gap-1.5">
                {["0", "10", "20", "30", "50"].map((pct) => (
                  <button
                    key={pct}
                    type="button"
                    onClick={() => setDpPercent(pct)}
                    className={`rounded-xl px-2.5 py-1.5 text-[11px] font-bold border transition ${
                      dpPercent === pct
                        ? "bg-[#0D0F17] text-[#C8F526] border-[#0D0F17]"
                        : "bg-white text-espresso-muted border-surface-border hover:text-espresso"
                    }`}
                  >
                    {pct}%
                  </button>
                ))}
                <div className="flex items-center gap-1 ml-auto">
                  <input
                    type="number"
                    min="0"
                    max="99"
                    step="0.5"
                    value={dpPercent}
                    onChange={(e) => setDpPercent(e.target.value)}
                    className="w-16 rounded-xl border border-surface-border bg-white px-2.5 py-1.5 text-xs font-bold text-espresso text-right focus:border-[#0D0F17] focus:outline-none"
                  />
                  <span className="text-xs font-bold text-espresso-muted">%</span>
                </div>
              </div>
            ) : (
              <input
                type="number"
                min="0"
                value={dpAmount}
                onChange={(e) => setDpAmount(e.target.value)}
                placeholder="Nominal DP (misal: 2000000)"
                className="w-full rounded-xl border border-surface-border bg-white px-3 py-2 text-xs font-bold text-espresso focus:border-[#0D0F17] focus:outline-none"
              />
            )}

            {/* Sumber DP */}
            <div className="grid grid-cols-2 gap-2 pt-1 text-xs">
              <button
                type="button"
                onClick={() => setDpSource("savings_pool")}
                className={`rounded-xl p-2.5 font-bold border transition text-left ${
                  dpSource === "savings_pool"
                    ? "border-[#0D0F17] bg-[#0D0F17] text-white"
                    : "border-surface-border bg-white text-espresso-muted"
                }`}
              >
                <div className="flex items-center gap-1.5 text-[11px]">
                  <PiggyBank
                    className={`h-3.5 w-3.5 shrink-0 ${
                      dpSource === "savings_pool" ? "text-[#C8F526]" : "text-emerald-700"
                    }`}
                  />
                  <span>DP dari Tabungan</span>
                </div>
                <span
                  className={`block text-[10px] font-normal mt-0.5 ${
                    dpSource === "savings_pool" ? "text-white/70" : "text-espresso-muted"
                  }`}
                >
                  Saldo: {formatIDR(summary?.savings_pool_balance)}
                </span>
              </button>

              <button
                type="button"
                onClick={() => setDpSource("operational_wallet")}
                className={`rounded-xl p-2.5 font-bold border transition text-left ${
                  dpSource === "operational_wallet"
                    ? "border-[#0D0F17] bg-[#0D0F17] text-white"
                    : "border-surface-border bg-white text-espresso-muted"
                }`}
              >
                <div className="flex items-center gap-1.5 text-[11px]">
                  <Wallet
                    className={`h-3.5 w-3.5 shrink-0 ${
                      dpSource === "operational_wallet" ? "text-[#C8F526]" : "text-espresso"
                    }`}
                  />
                  <span>DP dari Kas Bebas</span>
                </div>
                <span
                  className={`block text-[10px] font-normal mt-0.5 ${
                    dpSource === "operational_wallet" ? "text-white/70" : "text-espresso-muted"
                  }`}
                >
                  Bebas: {formatIDR(summary?.safe_to_spend_total)}
                </span>
              </button>
            </div>
          </div>

          {/* Tenor */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-bold text-espresso">Tenor Cicilan (Bulan)</label>
              <span className="text-[11px] font-black text-espresso">{tenorMonths} Bulan</span>
            </div>
            <div className="flex flex-wrap items-center gap-1.5">
              {[3, 6, 12, 18, 24, 36].map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setTenorMonths(t)}
                  className={`rounded-xl px-3 py-1.5 text-[11px] font-bold border transition ${
                    tenorMonths === t
                      ? "bg-[#0D0F17] text-[#C8F526] border-[#0D0F17]"
                      : "bg-surface-card text-espresso-muted border-surface-border hover:text-espresso"
                  }`}
                >
                  {t} Bln
                </button>
              ))}
              <input
                type="number"
                min="1"
                max="240"
                value={tenorMonths}
                onChange={(e) => setTenorMonths(Math.max(1, parseInt(e.target.value, 10) || 1))}
                className="w-20 ml-auto rounded-xl border border-surface-border bg-surface-card px-2.5 py-1.5 text-xs font-bold text-espresso text-center focus:border-[#0D0F17] focus:outline-none"
                title="Tenor kustom (bulan)"
              />
            </div>
          </div>

          {/* Skema Bunga */}
          <div className="space-y-2.5">
            <label className="block text-xs font-bold text-espresso">Skema Bunga / Margin</label>
            <div className="grid grid-cols-3 gap-1.5 text-[11px] font-bold">
              {[
                { id: "zero", label: "0% (Tanpa Bunga)" },
                { id: "flat", label: "Bunga Flat" },
                { id: "effective", label: "Efektif / Anuitas" },
              ].map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => setInterestType(opt.id as any)}
                  className={`rounded-xl py-2 px-2 border transition text-center ${
                    interestType === opt.id
                      ? "bg-[#0D0F17] text-[#C8F526] border-[#0D0F17]"
                      : "bg-surface-card text-espresso-muted border-surface-border hover:text-espresso"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>

            {interestType !== "zero" && (
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[11px] font-semibold text-espresso-muted mb-1">
                    Suku Bunga (%)
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="0.01"
                    value={interestRate}
                    onChange={(e) => setInterestRate(e.target.value)}
                    placeholder="1.5"
                    className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-xs font-bold text-espresso focus:border-[#0D0F17] focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-espresso-muted mb-1">
                    Periode Bunga
                  </label>
                  <select
                    value={interestRatePeriod}
                    onChange={(e) => setInterestRatePeriod(e.target.value as any)}
                    className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-xs font-bold text-espresso focus:border-[#0D0F17] focus:outline-none"
                  >
                    <option value="monthly">% per Bulan</option>
                    <option value="annual">% per Tahun</option>
                  </select>
                </div>
              </div>
            )}
          </div>

          {/* Biaya & Jadwal Opsional */}
          <div className="rounded-2xl border border-surface-border bg-surface-card/40 px-3.5 py-2.5">
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex w-full items-center justify-between text-xs font-bold text-espresso-muted hover:text-espresso"
            >
              <span>Biaya Admin & Jadwal Jatuh Tempo (Opsional)</span>
              {showAdvanced ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>

            {showAdvanced && (
              <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-2.5 border-t border-surface-border">
                <div>
                  <label className="block text-[11px] font-semibold text-espresso-muted mb-1">
                    Biaya Admin Awal (Rp)
                  </label>
                  <input
                    type="number"
                    min="0"
                    value={adminFee}
                    onChange={(e) => setAdminFee(e.target.value)}
                    placeholder="0"
                    className="w-full rounded-xl border border-surface-border bg-white px-3 py-1.5 text-xs font-bold text-espresso focus:border-[#0D0F17] focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-espresso-muted mb-1">
                    Biaya Layanan Bulanan (Rp)
                  </label>
                  <input
                    type="number"
                    min="0"
                    value={monthlyFee}
                    onChange={(e) => setMonthlyFee(e.target.value)}
                    placeholder="0"
                    className="w-full rounded-xl border border-surface-border bg-white px-3 py-1.5 text-xs font-bold text-espresso focus:border-[#0D0F17] focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-espresso-muted mb-1">
                    Tanggal Mulai / Bayar DP
                  </label>
                  <input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="w-full rounded-xl border border-surface-border bg-white px-3 py-1.5 text-xs font-medium text-espresso focus:border-[#0D0F17] focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-espresso-muted mb-1">
                    Tanggal Jatuh Tempo (1-31)
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="31"
                    value={dueDayOfMonth}
                    onChange={(e) => setDueDayOfMonth(e.target.value)}
                    placeholder="Sama dengan tgl mulai"
                    className="w-full rounded-xl border border-surface-border bg-white px-3 py-1.5 text-xs font-medium text-espresso focus:border-[#0D0F17] focus:outline-none"
                  />
                </div>
              </div>
            )}
          </div>

          {errorMsg && (
            <div className="rounded-2xl border border-expense/40 bg-expense/10 px-3.5 py-2.5 text-xs font-semibold text-expense">
              {errorMsg}
            </div>
          )}

          <button
            type="submit"
            disabled={isSimulating}
            className="w-full rounded-2xl bg-[#C8F526] py-3 text-xs font-black text-black shadow-md hover:bg-[#b8e51b] transition disabled:opacity-50 inline-flex items-center justify-center gap-1.5 active:scale-98"
          >
            {isSimulating ? (
              <span className="flex items-center gap-1.5">
                <Loader2 className="h-4 w-4 animate-spin" />
                Menghitung Simulasi & Kelayakan...
              </span>
            ) : (
              <>
                <Zap className="h-4 w-4 shrink-0" />
                <span>Hitung & Uji Kelayakan Cicilan</span>
              </>
            )}
          </button>
        </form>
      </div>

      {/* Hasil Simulasi Cicilan */}
      {result && (
        <div className="space-y-4 animate-fadeIn">
          {/* 1. Banner Vonis Kelayakan */}
          <div
            className={`rounded-3xl border p-5 space-y-2.5 ${
              result.verdict === "safe"
                ? "border-income/40 bg-income/10 text-espresso"
                : result.verdict === "warning"
                ? "border-[#F59E0B]/50 bg-[#FEF3C7]/60 text-espresso"
                : "border-expense/40 bg-expense/10 text-espresso"
            }`}
          >
            <div className="flex items-center gap-2 text-sm font-black">
              {result.verdict === "safe" ? (
                <CheckCircle2 className="h-5 w-5 text-income shrink-0" />
              ) : result.verdict === "warning" ? (
                <AlertTriangle className="h-5 w-5 text-[#D97706] shrink-0" />
              ) : (
                <ShieldAlert className="h-5 w-5 text-expense shrink-0" />
              )}
              <span>{result.headline}</span>
            </div>
            <p className="text-xs leading-relaxed text-espresso-muted">{result.explanation}</p>

            {result.recommendations.length > 0 && (
              <div className="pt-2 border-t border-black/10 space-y-1">
                <span className="text-[10px] font-black uppercase tracking-wider text-espresso">
                  Rekomendasi FinAI
                </span>
                <ul className="space-y-1">
                  {result.recommendations.map((rec, idx) => (
                    <li key={idx} className="text-[11px] text-espresso flex items-start gap-1.5">
                      <Sparkles className="h-3.5 w-3.5 text-espresso shrink-0 mt-0.5" />
                      <span>{rec}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* 2. 4 Kartu Metrik Utama */}
          <div className="grid grid-cols-2 gap-2.5">
            <div className="rounded-2xl border border-surface-border bg-white p-4 shadow-xs">
              <span className="text-[10px] font-bold uppercase text-espresso-muted block">
                Cicilan per Bulan
              </span>
              <span className="text-base sm:text-lg font-black text-espresso block mt-0.5">
                {formatIDR(result.monthly_installment)}
              </span>
              <span className="text-[10px] text-espresso-muted">
                {result.tenor_months}x angsuran ({result.interest_type === "zero" ? "0%" : result.interest_type === "flat" ? "Flat" : "Efektif"})
              </span>
            </div>

            <div className="rounded-2xl border border-surface-border bg-white p-4 shadow-xs">
              <span className="text-[10px] font-bold uppercase text-espresso-muted block">
                Total Bunga & Biaya
              </span>
              <span className="text-base sm:text-lg font-black text-expense block mt-0.5">
                {formatIDR(Number(result.total_interest) + Number(result.total_fees))}
              </span>
              <span className="text-[10px] text-espresso-muted">
                Total bayar: {formatIDR(result.total_cost)} (+{result.effective_markup_percent}%)
              </span>
            </div>

            <div className="rounded-2xl border border-surface-border bg-white p-4 shadow-xs">
              <span className="text-[10px] font-bold uppercase text-espresso-muted block">
                Rasio Cicilan (DSR)
              </span>
              <span
                className={`text-base sm:text-lg font-black block mt-0.5 ${
                  result.installment_to_income_ratio <= 20
                    ? "text-income"
                    : result.installment_to_income_ratio <= 30
                    ? "text-[#D97706]"
                    : "text-expense"
                }`}
              >
                {result.installment_to_income_ratio}%{" "}
                <span className="text-[10px] font-bold text-espresso-muted">dari income</span>
              </span>
              <span className="text-[10px] text-espresso-muted">
                Sisa cashflow: {formatIDR(result.projected_monthly_free_cashflow)}/bln
              </span>
            </div>

            <div className="rounded-2xl border border-surface-border bg-white p-4 shadow-xs">
              <span className="text-[10px] font-bold uppercase text-espresso-muted block">
                Dampak Jatah Harian
              </span>
              <div className="flex items-baseline gap-1 mt-0.5">
                <span className="text-base sm:text-lg font-black text-espresso">
                  {formatIDR(result.projected_daily_ideal_after)}
                </span>
                <span className="text-[10px] text-espresso-muted">/hr</span>
              </div>
              <span className="text-[10px] text-espresso-muted flex items-center gap-1">
                <TrendingDown className="h-3 w-3 shrink-0" />
                dari {formatIDR(result.current_daily_ideal)}/hr
              </span>
            </div>
          </div>

          {/* 3. Dampak DP & Komposisi Biaya */}
          <div className="rounded-3xl border border-surface-border bg-white p-5 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-surface-border pb-2.5">
              <h4 className="text-xs font-black text-espresso">Komposisi Pembayaran & Dampak DP</h4>
              <span className="text-[11px] font-bold text-espresso-muted">
                Dana Awal: {formatIDR(result.upfront_cash_needed)}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 items-center">
              <div className="h-44 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={chartData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      innerRadius={42}
                      outerRadius={68}
                      paddingAngle={3}
                    >
                      {chartData.map((entry, idx) => (
                        <Cell key={idx} fill={entry.color} />
                      ))}
                    </Pie>
                    <RechartsTooltip
                      formatter={(value: any) => formatIDR(value)}
                      contentStyle={{
                        borderRadius: "12px",
                        border: "1px solid #E5E8F0",
                        fontSize: "11px",
                        fontWeight: 700,
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              <div className="space-y-2 text-xs">
                {chartData.map((entry, idx) => (
                  <div key={idx} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span
                        className="h-2.5 w-2.5 rounded-full shrink-0"
                        style={{ backgroundColor: entry.color }}
                      />
                      <span className="text-espresso-muted font-medium">{entry.name}</span>
                    </div>
                    <span className="font-bold text-espresso">{formatIDR(entry.value)}</span>
                  </div>
                ))}
                <div className="pt-2 border-t border-surface-border space-y-1">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-espresso-muted">
                      {result.dp_source === "savings_pool" ? "Tabungan setelah DP:" : "Kas Bebas setelah DP:"}
                    </span>
                    <span
                      className={`font-black ${
                        result.is_dp_affordable ? "text-income" : "text-expense"
                      }`}
                    >
                      {formatIDR(
                        result.dp_source === "savings_pool"
                          ? result.projected_savings_after_dp
                          : result.projected_safe_to_spend_after_dp
                      )}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 4. Perbandingan Multi-Tenor */}
          <div className="rounded-3xl border border-surface-border bg-white p-5 shadow-xs space-y-3">
            <div>
              <h4 className="text-xs font-black text-espresso">Bandingkan Opsi Tenor</h4>
              <p className="text-[11px] text-espresso-muted">
                Klik salah satu tenor di bawah untuk langsung mengganti simulasi
              </p>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {result.tenor_comparisons.map((item) => {
                const isSelected = item.tenor_months === result.tenor_months;
                const badgeClass =
                  item.verdict === "safe"
                    ? "bg-income/15 text-income"
                    : item.verdict === "warning"
                    ? "bg-[#FEF3C7] text-[#B45309]"
                    : "bg-expense/15 text-expense";
                const verdictText =
                  item.verdict === "safe" ? "Aman" : item.verdict === "warning" ? "Ketat" : "Berat";

                return (
                  <button
                    key={item.tenor_months}
                    type="button"
                    onClick={() => handleSelectComparisonTenor(item.tenor_months)}
                    className={`rounded-2xl border p-3 text-left transition ${
                      isSelected
                        ? "border-[#0D0F17] bg-[#0D0F17] text-white shadow-sm"
                        : "border-surface-border bg-surface-card hover:border-[#0D0F17]/40 text-espresso"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-black">{item.tenor_months} Bln</span>
                      <span className={`rounded-full px-1.5 py-0.5 text-[9px] font-black ${badgeClass}`}>
                        {verdictText}
                      </span>
                    </div>
                    <span className="text-xs font-black block">
                      {formatIDR(item.monthly_installment)}
                    </span>
                    <span
                      className={`text-[10px] block mt-0.5 ${
                        isSelected ? "text-white/70" : "text-espresso-muted"
                      }`}
                    >
                      DSR {item.income_ratio_percent}%
                    </span>
                    <span
                      className={`text-[10px] block ${
                        isSelected ? "text-[#C8F526]" : "text-espresso-muted"
                      }`}
                    >
                      Bunga: {formatIDR(item.total_interest_and_fees)}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* 5. Jadwal Amortisasi (Collapsible) */}
          <div className="rounded-3xl border border-surface-border bg-white p-5 shadow-xs space-y-3">
            <button
              type="button"
              onClick={() => setShowSchedule(!showSchedule)}
              className="flex w-full items-center justify-between text-left"
            >
              <div>
                <h4 className="text-xs font-black text-espresso flex items-center gap-1.5">
                  <Calendar className="h-3.5 w-3.5" />
                  Jadwal Angsuran ({result.amortization_schedule.length} Bulan)
                </h4>
                <p className="text-[11px] text-espresso-muted">
                  Rincian pokok, bunga, biaya, dan sisa pinjaman tiap bulan
                </p>
              </div>
              {showSchedule ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>

            {showSchedule && (
              <div className="overflow-x-auto max-h-80 border border-surface-border rounded-2xl">
                <table className="w-full text-left text-[11px]">
                  <thead className="bg-surface-card sticky top-0 text-[10px] uppercase text-espresso-muted font-bold">
                    <tr>
                      <th className="px-3 py-2">Bln</th>
                      <th className="px-3 py-2">Jatuh Tempo</th>
                      <th className="px-3 py-2 text-right">Pokok</th>
                      <th className="px-3 py-2 text-right">Bunga/Biaya</th>
                      <th className="px-3 py-2 text-right">Total Bayar</th>
                      <th className="px-3 py-2 text-right">Sisa Pokok</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surface-border">
                    {result.amortization_schedule.map((row) => (
                      <tr key={row.month_index} className="hover:bg-surface-card/50">
                        <td className="px-3 py-2 font-bold text-espresso">#{row.month_index}</td>
                        <td className="px-3 py-2 text-espresso-muted whitespace-nowrap">{row.due_date}</td>
                        <td className="px-3 py-2 text-right font-medium text-espresso whitespace-nowrap">
                          {formatIDR(row.principal_amount)}
                        </td>
                        <td className="px-3 py-2 text-right text-expense whitespace-nowrap">
                          {formatIDR(Number(row.interest_amount) + Number(row.fee_amount))}
                        </td>
                        <td className="px-3 py-2 text-right font-black text-espresso whitespace-nowrap">
                          {formatIDR(row.total_payment)}
                        </td>
                        <td className="px-3 py-2 text-right text-espresso-muted whitespace-nowrap">
                          {formatIDR(row.remaining_principal)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* 6. Terapkan ke Proyeksi Cashflow / Simpan ke Wishlist */}
          <div className="rounded-3xl border border-surface-border bg-white p-5 shadow-xs space-y-3">
            <div>
              <h4 className="text-xs font-black text-espresso">Langkah Selanjutnya</h4>
              <p className="text-[11px] text-espresso-muted">
                Jadwalkan angsuran ini ke Prediksi Saldo Masa Depan untuk melihat dampaknya pada buku kas harian
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              <div>
                <label className="block text-[10px] font-bold text-espresso-muted mb-1">
                  Dompet Pembayar Cicilan (Opsional)
                </label>
                <select
                  value={selectedWalletId}
                  onChange={(e) => setSelectedWalletId(e.target.value)}
                  className="w-full rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-xs font-semibold text-espresso focus:outline-none"
                >
                  <option value="">-- Otomatis Operasional Utama --</option>
                  {wallets?.map((w: any) => (
                    <option key={w.id} value={w.id}>
                      {w.name} ({formatIDR(w.balance)})
                    </option>
                  ))}
                </select>
              </div>

              <label className="flex items-center gap-2 rounded-xl border border-surface-border bg-surface-card px-3 py-2 text-xs font-semibold text-espresso cursor-pointer self-end">
                <input
                  type="checkbox"
                  checked={includeDpInPlan}
                  onChange={(e) => setIncludeDpInPlan(e.target.checked)}
                  className="rounded border-surface-border"
                />
                <span>Sertakan DP & Biaya Admin Awal</span>
              </label>
            </div>

            {applySuccessMsg && (
              <div className="rounded-2xl border border-income/40 bg-income/10 px-3.5 py-2.5 text-xs font-bold text-income">
                {applySuccessMsg}
              </div>
            )}

            {wishlistSavedMsg && (
              <div className="rounded-2xl border border-income/40 bg-income/10 px-3.5 py-2.5 text-xs font-bold text-income">
                {wishlistSavedMsg}
              </div>
            )}

            <div className="flex flex-col sm:flex-row gap-2">
              <button
                type="button"
                onClick={handleApplyToPlanned}
                disabled={isApplying}
                className="flex-1 rounded-2xl bg-[#0D0F17] py-2.5 px-4 text-xs font-black text-[#C8F526] hover:bg-[#161A26] transition disabled:opacity-50 inline-flex items-center justify-center gap-1.5"
              >
                {isApplying ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Calendar className="h-3.5 w-3.5" />
                )}
                <span>Jadwalkan ke Prediksi Saldo</span>
              </button>

              <button
                type="button"
                onClick={handleSaveWishlist}
                disabled={isSavingWishlist}
                className="rounded-2xl border border-surface-border bg-surface-card py-2.5 px-4 text-xs font-bold text-espresso hover:border-[#0D0F17] transition disabled:opacity-50 inline-flex items-center justify-center gap-1.5"
              >
                <Plus className="h-3.5 w-3.5" />
                <span>Simpan ke Wishlist</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
