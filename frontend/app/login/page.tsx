"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Bot, Loader2, Lock, Mail, User as UserIcon, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

export default function LoginPage() {
  const router = useRouter();
  const { setAuth } = useAuthStore();
  const [isRegister, setIsRegister] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Form State
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setIsLoading(true);

    try {
      if (isRegister) {
        // Register API
        const res = await api.post("/api/v1/auth/register", {
          name: name.trim(),
          email: email.trim(),
          password,
        });
        setAuth(res.data.access_token, res.data.user);
        router.push("/dashboard");
      } else {
        // Login API
        const res = await api.post("/api/v1/auth/login", {
          email: email.trim(),
          password,
        });
        setAuth(res.data.access_token, res.data.user);
        router.push("/dashboard");
      }
    } catch (err: any) {
      setErrorMsg(
        err.response?.data?.detail || "Terjadi kesalahan saat otentikasi. Silakan periksa kembali."
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-[90vh] items-center justify-center px-4 py-8">
      <div className="w-full max-w-md space-y-6">
        {/* Header Branding */}
        <div className="flex flex-col items-center text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-tr from-amber to-terracotta shadow-md shadow-terracotta/20 border border-amber/30">
            <Bot className="h-8 w-8 text-white" />
          </div>
          <h1 className="mt-4 text-2xl font-extrabold tracking-tight text-espresso">
            Fin<span className="text-terracotta">AI</span> Track
          </h1>
          <p className="mt-1 text-xs text-espresso-muted font-medium">
            Smart Personal Finance & AI Voice/Chat Assistant
          </p>
        </div>

        {/* Auth Card */}
        <div className="rounded-3xl border border-surface-border bg-surface p-6 shadow-md">
          {/* Tab Selector */}
          <div className="mb-6 flex rounded-xl bg-surface-card p-1 border border-surface-border">
            <button
              type="button"
              onClick={() => {
                setIsRegister(false);
                setErrorMsg(null);
              }}
              className={`flex-1 rounded-lg py-2 text-xs font-bold transition ${
                !isRegister
                  ? "bg-terracotta text-white shadow-md shadow-terracotta/20"
                  : "text-espresso-muted hover:text-espresso"
              }`}
            >
              Masuk (Login)
            </button>
            <button
              type="button"
              onClick={() => {
                setIsRegister(true);
                setErrorMsg(null);
              }}
              className={`flex-1 rounded-lg py-2 text-xs font-bold transition ${
                isRegister
                  ? "bg-terracotta text-white shadow-md shadow-terracotta/20"
                  : "text-espresso-muted hover:text-espresso"
              }`}
            >
              Daftar Akun
            </button>
          </div>

          {errorMsg && (
            <div className="mb-4 rounded-xl border border-expense/30 bg-expense/10 p-3 text-xs text-expense font-semibold">
              {errorMsg}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {isRegister && (
              <div>
                <label className="mb-1 block text-xs font-semibold text-espresso">
                  Nama Lengkap
                </label>
                <div className="relative">
                  <UserIcon className="absolute left-3 top-2.5 h-4 w-4 text-espresso-muted/50" />
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Dimas Primo"
                    className="w-full rounded-xl border border-surface-border bg-surface py-2 pl-9 pr-3 text-sm font-medium text-espresso placeholder:text-espresso-muted/40 focus:border-terracotta focus:outline-none"
                  />
                </div>
              </div>
            )}

            <div>
              <label className="mb-1 block text-xs font-semibold text-espresso">
                Alamat Email
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-2.5 h-4 w-4 text-espresso-muted/50" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="user@example.com"
                  className="w-full rounded-xl border border-surface-border bg-surface py-2 pl-9 pr-3 text-sm font-medium text-espresso placeholder:text-espresso-muted/40 focus:border-terracotta focus:outline-none"
                />
              </div>
            </div>

            <div>
              <label className="mb-1 block text-xs font-semibold text-espresso">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-2.5 h-4 w-4 text-espresso-muted/50" />
                <input
                  type="password"
                  required
                  minLength={6}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full rounded-xl border border-surface-border bg-surface py-2 pl-9 pr-3 text-sm font-medium text-espresso placeholder:text-espresso-muted/40 focus:border-terracotta focus:outline-none"
                />
              </div>
              {isRegister && (
                <span className="mt-1 block text-[11px] text-espresso-muted">
                  Minimal 6 karakter kombinasi aman.
                </span>
              )}
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="mt-6 flex w-full items-center justify-center gap-2 rounded-xl bg-terracotta py-2.5 text-sm font-bold text-white shadow-md shadow-terracotta/20 transition hover:bg-terracotta-hover disabled:opacity-50"
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  {isRegister ? "Buat Akun Sekarang" : "Masuk ke Dashboard"}
                </>
              )}
            </button>
          </form>

          {isRegister && (
            <p className="mt-4 text-center text-[11px] text-espresso-muted">
              *Registrasi otomatis membuat 1 dompet <strong>Tunai</strong> dan 10 kategori pengeluaran/pemasukan awal.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

