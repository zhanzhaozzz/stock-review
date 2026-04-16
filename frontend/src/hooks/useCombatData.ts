import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "../api/client";

export interface MarketStateDaily {
  date: string;
  temperature_score: number | null;
  market_phase: string | null;
  style_tag: string | null;
  limit_up_count: number | null;
  limit_down_count: number | null;
  boom_rate: number | null;
  highest_ladder: number | null;
  promotion_rate: number | null;
  total_volume: number | null;
  volume_delta: number | null;
  focus_sectors: string[] | null;
  conclusion: string | null;
}

export interface BattleBrief {
  date: string;
  status_tone: string | null;
  suggested_position: string | null;
  overall_conclusion: string | null;
  macro_context: unknown[] | null;
  main_narrative: unknown[] | null;
  bullish_sectors: unknown[] | null;
  bearish_sectors: unknown[] | null;
  risk_tips: unknown[] | null;
  allowed_actions: unknown[] | null;
  forbidden_actions: unknown[] | null;
}

export interface CandidatePoolEntry {
  id: number;
  date: string;
  code: string;
  name: string;
  source_type: string | null;
  source_reason: string | null;
  theme: string | null;
  thesis: string | null;
  gate_status: string | null;
  gate_reason: string | null;
  action_hint: string | null;
  risk_flags: string[] | null;
  review_outcome: string | null;
  review_note: string | null;
}

export interface PostMarketReview {
  date: string;
  brief_grade: string | null;
  grade_reason: string | null;
  actual_market_trend: string | null;
  carry_over_themes: unknown[] | null;
  next_day_seeds: unknown[] | null;
  eliminated_directions: unknown[] | null;
}

export interface CombatDeskData {
  date: string;
  market_state: MarketStateDaily | null;
  battle_brief: BattleBrief | null;
  candidate_preview: CandidatePoolEntry[];
}

export function useCombatDesk() {
  return useQuery<CombatDeskData>({
    queryKey: ["combat-desk", "today"],
    queryFn: async () => {
      const res = await api.get("/combat-desk/today");
      return res.data;
    },
    staleTime: 2 * 60 * 1000,
  });
}

export function useCandidates() {
  return useQuery<CandidatePoolEntry[]>({
    queryKey: ["candidates", "today"],
    queryFn: async () => {
      const res = await api.get("/candidates/today");
      return res.data || [];
    },
    staleTime: 2 * 60 * 1000,
  });
}

export function usePostMarketReview() {
  return useQuery<PostMarketReview | null>({
    queryKey: ["post-market-review", "today"],
    queryFn: async () => {
      const res = await api.get("/post-market-review/today");
      return res.data;
    },
    staleTime: 2 * 60 * 1000,
  });
}

export function useUpdateCandidate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: number;
      data: { gate_status?: string; gate_reason?: string; action_hint?: string; review_outcome?: string; review_note?: string };
    }) => {
      const res = await api.put(`/candidates/${id}`, data);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["candidates"] });
      qc.invalidateQueries({ queryKey: ["combat-desk"] });
      qc.invalidateQueries({ queryKey: ["post-market-review"] });
    },
  });
}
