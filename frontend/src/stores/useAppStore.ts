import { create } from "zustand";
import api from "../api/client";

export type Theme = "light" | "dark";

function applyThemeClass(theme: Theme) {
  const root = document.documentElement;
  if (theme === "dark") {
    root.classList.add("dark");
  } else {
    root.classList.remove("dark");
  }
}

function getInitialTheme(): Theme {
  const stored = localStorage.getItem("sr-theme");
  if (stored === "light" || stored === "dark") return stored;
  return "dark";
}

interface AppState {
  theme: Theme;
  setTheme: (t: Theme) => void;
  cyclePhase: string;
  suggestedPosition: string;
  matchedStrategies: string[];
  loadingRecommend: boolean;
  refreshRecommend: () => Promise<void>;
}

const initialTheme = getInitialTheme();
applyThemeClass(initialTheme);

export const useAppStore = create<AppState>((set) => ({
  theme: initialTheme,
  setTheme: (t: Theme) => {
    localStorage.setItem("sr-theme", t);
    applyThemeClass(t);
    set({ theme: t });
  },
  cyclePhase: "",
  suggestedPosition: "",
  matchedStrategies: [],
  loadingRecommend: false,
  refreshRecommend: async () => {
    set({ loadingRecommend: true });
    try {
      const res = await api.get("/strategies/recommend");
      const data = res.data || {};
      const matched = Array.isArray(data.matched_strategies) ? data.matched_strategies : [];
      set({
        cyclePhase: data.cycle_phase || "",
        suggestedPosition: data.suggested_position || "",
        matchedStrategies: matched.map((m: any) => m.name).filter(Boolean),
      });
    } catch {
      set({ cyclePhase: "", suggestedPosition: "", matchedStrategies: [] });
    } finally {
      set({ loadingRecommend: false });
    }
  },
}));

