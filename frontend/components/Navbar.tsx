"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Compass,
  Sparkles,
  Receipt,
  Settings,
  LogOut,
  Wallet,
  Bot,
} from "lucide-react";
import { useAuthStore } from "@/lib/store";

export function Navbar() {
  const [mounted, setMounted] = useState(false);
  const pathname = usePathname();
  const router = useRouter();
  const { user, clearAuth } = useAuthStore();

  useEffect(() => {
    setMounted(true);
  }, []);

  const isAuthPage = pathname.startsWith("/login");
  if (isAuthPage) return null;

  const navItems = [
    { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { label: "Proyeksi", href: "/forecast", icon: Compass },
    { label: "Fin AI", href: "/ai-assistant", icon: Sparkles, highlight: true },
    { label: "Transaksi", href: "/transactions", icon: Receipt },
    { label: "Pengaturan", href: "/settings", icon: Settings },
  ];

  const handleLogout = () => {
    clearAuth();
    router.push("/login");
  };

  return (
    <>
      {/* ==================================================================== */}
      {/* 1. TOP HEADER (Desktop & Mobile) */}
      {/* ==================================================================== */}
      <header className="sticky top-0 z-40 w-full border-b border-surface-border bg-white/80 backdrop-blur-xl px-4 py-3">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <Link href="/dashboard" className="flex items-center gap-2.5 group">
            <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-black shadow-md shadow-black/15 group-hover:scale-105 transition-transform">
              <Bot className="h-5 w-5 text-[#C8F526]" />
            </div>
            <div>
              <span className="text-lg font-black tracking-tight text-espresso">
                Fin<span className="text-emerald-500">AI</span> Track
              </span>
              <span className="ml-2 rounded-full bg-[#C8F526]/30 px-2 py-0.5 text-[9px] font-black text-black border border-[#C8F526]/60 tracking-wider">
                v2.0 NEO
              </span>
            </div>
          </Link>

          <div className="flex items-center gap-3">
            {mounted && user && (
              <div className="hidden sm:flex flex-col text-right">
                <span className="text-xs font-bold text-espresso">{user.name}</span>
                <span className="text-[10px] text-espresso-muted">{user.email}</span>
              </div>
            )}
            <button
              onClick={handleLogout}
              title="Keluar"
              className="flex h-9 w-9 items-center justify-center rounded-xl border border-surface-border bg-surface-card text-espresso-muted transition hover:bg-expense/10 hover:text-expense hover:border-expense/30"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </header>

      {/* ==================================================================== */}
      {/* 2. FLOATING BOTTOM CAPSULE DOCK (Mobile First / PWA) */}
      {/* ==================================================================== */}
      <nav className="md:hidden fixed bottom-4 left-3 right-3 z-50 rounded-full border border-black/5 bg-white/90 backdrop-blur-2xl p-1.5 shadow-2xl shadow-black/10">
        <div className="flex items-center justify-around">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`relative flex items-center justify-center rounded-full transition-all duration-200 ${
                  isActive
                    ? "bg-black text-white px-3.5 py-2 shadow-lg shadow-black/20 gap-1.5"
                    : "text-espresso-muted hover:text-espresso p-2"
                }`}
              >
                <Icon
                  className={`h-4 w-4 shrink-0 transition-transform ${
                    isActive ? "text-[#C8F526] scale-105" : ""
                  }`}
                />
                {isActive && (
                  <span className="text-xs font-bold whitespace-nowrap animate-fadeIn">
                    {item.label}
                  </span>
                )}
              </Link>
            );
          })}
        </div>
      </nav>

      {/* ==================================================================== */}
      {/* 3. DESKTOP FLOATING SIDEBAR NAVIGATION */}
      {/* ==================================================================== */}
      <div className="hidden md:flex fixed left-6 top-24 z-30 flex-col gap-1.5 rounded-3xl border border-surface-border bg-white/85 p-2 backdrop-blur-xl shadow-xl shadow-black/5">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-2xl px-4 py-2.5 text-sm font-semibold transition-all duration-150 ${
                isActive
                  ? "bg-black text-white shadow-md shadow-black/15"
                  : "text-espresso-muted hover:bg-surface-card hover:text-espresso"
              }`}
            >
              <Icon
                className={`h-4 w-4 transition-colors ${
                  isActive ? "text-[#C8F526]" : ""
                }`}
              />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </div>
    </>
  );
}

