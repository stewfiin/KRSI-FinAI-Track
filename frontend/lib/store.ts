import { create } from "zustand";

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  default_currency: string;
  telegram_chat_id: number | null;
  created_at: string;
}

interface AuthState {
  token: string | null;
  user: UserProfile | null;
  isBalanceHidden: boolean;
  isHydrated: boolean;
  initAuth: () => void;
  setAuth: (token: string, user: UserProfile) => void;
  setUser: (user: UserProfile) => void;
  clearAuth: () => void;
  toggleBalanceHidden: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  user: null,
  isBalanceHidden: true,
  isHydrated: false,

  initAuth: () => {
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("finai_token");
      const userStr = localStorage.getItem("finai_user");
      const saved = localStorage.getItem("finai_hide_balance");
      const isHidden = saved !== null ? saved === "true" : true;
      let user: UserProfile | null = null;
      try {
        if (userStr) user = JSON.parse(userStr);
      } catch {}
      set({ token, user, isBalanceHidden: isHidden, isHydrated: true });
    }
  },

  setAuth: (token, user) => {
    if (typeof window !== "undefined") {
      localStorage.setItem("finai_token", token);
      localStorage.setItem("finai_user", JSON.stringify(user));
    }
    set({ token, user, isHydrated: true });
  },

  setUser: (user) => {
    if (typeof window !== "undefined") {
      localStorage.setItem("finai_user", JSON.stringify(user));
    }
    set({ user });
  },

  clearAuth: () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("finai_token");
      localStorage.removeItem("finai_user");
    }
    set({ token: null, user: null });
  },

  toggleBalanceHidden: () => {
    set((state) => {
      const next = !state.isBalanceHidden;
      if (typeof window !== "undefined") {
        localStorage.setItem("finai_hide_balance", String(next));
      }
      return { isBalanceHidden: next };
    });
  },
}));
