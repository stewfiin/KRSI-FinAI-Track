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
    <div className="flex min-h-[88vh] items-center justify-center px-4 py-8">
      <div className="w-full max-w-md space-y-6">
        {/* Header Branding */}
        <div className="flex flex-col items-center text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-3xl bg-[#0D0F17] shadow-xl shadow-black/15 border border-white/10">
            <Bot className="h-8 w-8 text-[#C8F526]" />
          </div>
          <div className="mt-4 flex items-center gap-2">
            <h1 className="text-2xl font-black tracking-tight text-black">
              Fin<span className="text-emerald-500">AI</span> Track
            </h1>
            <span className="rounded-full bg-[#C8F526] px-2.5 py-0.5 text-[10px] font-black text-black tracking-wider">
              v2.0 NEO
            </span>
          </div>
        </div>

        {/* Auth Card */}
        <div className="rounded-[28px] border border-black/5 bg-white p-6 sm:p-7 shadow-xl shadow-black/5">
          {/* Tab Selector */}
          <div className="mb-6 flex rounded-2xl bg-gray-100 p-1.5">
            <button
              type="button"
              onClick={() => {
                setIsRegister(false);
                setErrorMsg(null);
              }}
              className={`flex-1 rounded-xl py-2.5 text-xs font-black transition-all ${
                !isRegister
                  ? "bg-[#0D0F17] text-[#C8F526] shadow-md shadow-black/15"
                  : "text-gray-500 hover:text-black"
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
              className={`flex-1 rounded-xl py-2.5 text-xs font-black transition-all ${
                isRegister
                  ? "bg-[#0D0F17] text-[#C8F526] shadow-md shadow-black/15"
                  : "text-gray-500 hover:text-black"
              }`}
            >
              Daftar Akun
            </button>
          </div>

          {errorMsg && (
            <div className="mb-4 rounded-2xl border border-rose-200 bg-rose-50 p-3.5 text-xs text-rose-600 font-bold">
              {errorMsg}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {isRegister && (
              <div>
                <label className="mb-1.5 block text-xs font-black text-black">
                  Nama Lengkap
                </label>
                <div className="relative">
                  <UserIcon className="absolute left-3.5 top-3 h-4 w-4 text-gray-400" />
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Dimas Primo"
                    className="w-full rounded-2xl border border-gray-200 bg-gray-50/50 py-2.5 pl-10 pr-3.5 text-sm font-bold text-black placeholder:text-gray-400 focus:border-black focus:bg-white focus:outline-none transition"
                  />
                </div>
              </div>
            )}

            <div>
              <label className="mb-1.5 block text-xs font-black text-black">
                Alamat Email
              </label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-3 h-4 w-4 text-gray-400" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="user@example.com"
                  className="w-full rounded-2xl border border-gray-200 bg-gray-50/50 py-2.5 pl-10 pr-3.5 text-sm font-bold text-black placeholder:text-gray-400 focus:border-black focus:bg-white focus:outline-none transition"
                />
              </div>
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-black text-black">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-3 h-4 w-4 text-gray-400" />
                <input
                  type="password"
                  required
                  minLength={6}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full rounded-2xl border border-gray-200 bg-gray-50/50 py-2.5 pl-10 pr-3.5 text-sm font-bold text-black placeholder:text-gray-400 focus:border-black focus:bg-white focus:outline-none transition"
                />
              </div>
              {isRegister && (
                <span className="mt-1.5 block text-[11px] font-medium text-gray-400">
                  Minimal 6 karakter kombinasi aman.
                </span>
              )}
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="mt-6 flex w-full items-center justify-center gap-2 rounded-2xl bg-[#C8F526] py-3 text-sm font-black text-black shadow-lg shadow-[#C8F526]/25 transition hover:bg-[#b8e51b] active:scale-98 disabled:opacity-50"
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
            <p className="mt-4 text-center text-[11px] text-gray-400 font-medium">
              *Registrasi otomatis membuat 1 dompet <strong>Tunai</strong> dan 10 kategori pengeluaran/pemasukan awal.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

