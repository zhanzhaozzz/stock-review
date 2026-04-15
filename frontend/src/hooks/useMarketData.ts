import { useQuery } from "@tanstack/react-query";
import api from "../api/client";

export function useMarketOverview() {
  return useQuery({
    queryKey: ["market", "overview"],
    queryFn: async () => {
      const res = await api.get("/market/overview");
      return res.data;
    },
    staleTime: 2 * 60 * 1000,
  });
}

export function useMarketSectors(type: string = "concept", limit: number = 20) {
  return useQuery({
    queryKey: ["market", "sectors", type, limit],
    queryFn: async () => {
      const res = await api.get(`/market/sectors?sector_type=${type}&limit=${limit}`);
      return res.data || [];
    },
    staleTime: 2 * 60 * 1000,
  });
}

export function useStockDaily(code: string | null, days: number = 60) {
  return useQuery({
    queryKey: ["stock", "daily", code, days],
    queryFn: async () => {
      const res = await api.get(`/market/stock/${code}/daily?days=${days}`);
      return res.data;
    },
    enabled: !!code,
    staleTime: 5 * 60 * 1000,
  });
}

export function useStockQuote(code: string | null) {
  return useQuery({
    queryKey: ["stock", "quote", code],
    queryFn: async () => {
      const res = await api.get(`/market/quote/${code}`);
      return res.data?.error ? null : res.data;
    },
    enabled: !!code,
    staleTime: 30 * 1000,
  });
}

export function useStockFundamental(code: string | null) {
  return useQuery({
    queryKey: ["stock", "fundamental", code],
    queryFn: async () => {
      const res = await api.get(`/market/fundamental/${code}`);
      return res.data;
    },
    enabled: !!code,
    staleTime: 10 * 60 * 1000,
  });
}

export function useRatingHistory(code: string | null, limit: number = 1) {
  return useQuery({
    queryKey: ["rating", "history", code, limit],
    queryFn: async () => {
      const res = await api.get(`/ratings/history/${code}?limit=${limit}`);
      return res.data || [];
    },
    enabled: !!code,
    staleTime: 5 * 60 * 1000,
  });
}

export function useAnalysisHistory(code: string | null, limit: number = 1) {
  return useQuery({
    queryKey: ["analysis", "history", code, limit],
    queryFn: async () => {
      const res = await api.get(`/analysis/history?code=${code}&limit=${limit}`);
      return res.data || [];
    },
    enabled: !!code,
    staleTime: 5 * 60 * 1000,
  });
}

export function useLimitUp(dateStr: string = "today") {
  return useQuery({
    queryKey: ["market", "limitUp", dateStr],
    queryFn: async () => {
      const res = await api.get(`/market/limit-up?date=${dateStr}`);
      return res.data;
    },
    staleTime: 5 * 60 * 1000,
  });
}
