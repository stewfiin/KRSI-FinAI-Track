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
    { label: "AI Assistant", href: "/ai-assistant", icon: Sparkles, highlight: true },
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
      <header className="sticky top-0 z-40 w-full border-b border-surface-border bg-surface/90 backdrop-blur-md px-4 py-3">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <Link href="/dashboard" className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-espresso to-terracotta shadow-md shadow-terracotta/20">
              <Bot className="h-5 w-5 text-cream" />
            </div>
            <div>
              <span className="text-lg font-bold tracking-tight text-espresso">
                Fin<span className="text-terracotta">AI</span> Track
              </span>
              <span className="ml-1.5 rounded-md bg-amber/20 px-1.5 py-0.5 text-[10px] font-semibold text-terracotta border border-amber/40">
                MVP v1.0
              </span>
            </div>
          </Link>

          <div className="flex items-center gap-3">
            {mounted && user && (
              <div className="hidden sm:flex flex-col text-right">
                <span className="text-xs font-semibold text-espresso">{user.name}</span>
                <span className="text-[10px] text-espresso-muted">{user.email}</span>
              </div>
            )}
            <button
              onClick={handleLogout}
              title="Keluar"
              className="flex h-9 w-9 items-center justify-center rounded-lg border border-surface-border bg-surface-card text-espresso-muted transition hover:bg-expense/10 hover:text-expense"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </header>

      {/* ==================================================================== */}
      {/* 2. BOTTOM NAVIGATION BAR (Mobile First / PWA) */}
      {/* ==================================================================== */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 border-t border-surface-border bg-surface/95 backdrop-blur-lg px-2 py-1.5 shadow-lg">
        <div className="flex items-center justify-around">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`relative flex flex-col items-center gap-1 rounded-xl px-3 py-1.5 transition-all ${
                  isActive
                    ? "text-terracotta font-bold"
                    : "text-espresso-muted hover:text-espresso"
                }`}
              >
                <div
                  className={`flex h-8 w-8 items-center justify-center rounded-xl transition ${
                    isActive
                      ? item.highlight
                        ? "bg-gradient-to-tr from-terracotta to-amber text-white shadow-md shadow-terracotta/30"
                        : "bg-terracotta/15 text-terracotta"
                      : ""
                  }`}
                >
                  <Icon className="h-4 w-4" />
                </div>
                <span className="text-[11px] leading-none">{item.label}</span>
              </Link>
            );
          })}
        </div>
      </nav>

      {/* ==================================================================== */}
      {/* 3. DESKTOP FLOATING BAR / SIDEBAR NAVIGATION */}
      {/* ==================================================================== */}
      <div className="hidden md:flex fixed left-6 top-24 z-30 flex-col gap-2 rounded-2xl border border-surface-border bg-surface/90 p-2 backdrop-blur-lg shadow-md">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-xl px-4 py-2.5 text-sm font-medium transition ${
                isActive
                  ? item.highlight
                    ? "bg-gradient-to-r from-espresso to-terracotta text-white shadow-md shadow-terracotta/25 border border-terracotta/30"
                    : "bg-terracotta text-white shadow-sm"
                  : "text-espresso-muted hover:bg-cream-dark/50 hover:text-espresso"
              }`}
            >
              <Icon className="h-4 w-4" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </div>
    </>
  );
}

