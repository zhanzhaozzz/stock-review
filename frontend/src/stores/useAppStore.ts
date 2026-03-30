import { create } from "zustand";
import api from "../api/client";

interface AppState {
  cyclePhase: string;
  suggestedPosition: string;
  matchedStrategies: string[];
  loadingRecommend: boolean;
  refreshRecommend: () => Promise<void>;
}

export const useAppStore = create<AppState>((set) => ({
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

