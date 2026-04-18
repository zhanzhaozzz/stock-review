import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "../api/client";

type ReviewStatus = "draft" | "published";

interface DailyReviewItem {
  id: number;
  date: string;
  status: ReviewStatus;
  market_sentiment: string;
  sentiment_cycle_main: string;
  market_height: number;
  market_leader: string;
  dragon_stock: string;
  core_middle_stock: string;
  market_ladder: string;
  total_volume: string;
  total_limit_up: number;
  first_board_count: number;
  broken_board_count: number;
  sentiment_detail: string;
  main_sector: string;
  sub_sector: string;
  main_sectors: string;
  sub_sectors: string;
  market_style: string;
  broken_boards: string;
  broken_high_stock: string;
  conclusion_quadrant: string;
  review_summary: string;
  next_day_plan: string;
  next_day_prediction: string;
  next_day_mode: string;
  applicable_strategy: string;
  suggested_position: string;
  ai_review_draft: string;
  ai_next_day_suggestion: string;
  market_action: string;
  market_result: string;
  is_confirmed: boolean;
}

function safeStr(v: unknown): string {
  if (typeof v === "string") return v;
  if (v === null || v === undefined) return "";
  return String(v);
}

export default function LegacyDailyReview() {
  const [searchParams] = useSearchParams();
  const dateParam = searchParams.get("date");
  const dateKey = dateParam || "today";

  const qc = useQueryClient();

  const {
    data: review,
    isLoading,
    isFetching,
    error,
    refetch,
  } = useQuery<DailyReviewItem | null>({
    queryKey: ["legacy-review", dateKey],
    queryFn: async () => {
      try {
        if (dateParam) {
          const res = await api.get(`/review/date/${dateParam}`);
          return res.data;
        }
        const res = await api.get("/review/today");
        return res.data;
      } catch (e: any) {
        const status = e?.response?.status;
        if (status === 404) return null;
        throw e;
      }
    },
    staleTime: 2 * 60 * 1000,
    retry: false,
  });

  const [reviewSummary, setReviewSummary] = useState("");
  const [nextDayPlan, setNextDayPlan] = useState("");
  const [marketAction, setMarketAction] = useState("");
  const [marketResult, setMarketResult] = useState("");
  const [confirmed, setConfirmed] = useState(false);

  useEffect(() => {
    if (!review) return;
    setReviewSummary(safeStr(review.review_summary));
    setNextDayPlan(safeStr(review.next_day_plan));
    setMarketAction(safeStr(review.market_action));
    setMarketResult(safeStr(review.market_result));
    setConfirmed(!!review.is_confirmed);
  }, [review?.id]);

  const generateMutation = useMutation({
    mutationFn: async () => {
      const suffix = dateParam ? `?target_date=${encodeURIComponent(dateParam)}` : "";
      const res = await api.post(`/review/run${suffix}`);
      return res.data;
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["legacy-review", dateKey] });
      await refetch();
    },
  });

  const updateMutation = useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      if (!review) throw new Error("复盘不存在");
      const res = await api.put(`/review/${review.id}`, payload);
      return res.data;
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["legacy-review", dateKey] });
      await refetch();
    },
  });

  function handleSave() {
    if (!review) return;
    updateMutation.mutate({
      review_summary: reviewSummary,
      next_day_plan: nextDayPlan,
      market_action: marketAction,
      market_result: marketResult,
      is_confirmed: confirmed,
    });
  }

  function handleReset() {
    if (!review) return;
    setReviewSummary(safeStr(review.review_summary));
    setNextDayPlan(safeStr(review.next_day_plan));
    setMarketAction(safeStr(review.market_action));
    setMarketResult(safeStr(review.market_result));
    setConfirmed(!!review.is_confirmed);
  }

  const displayDate = review?.date || dateParam || "今日";

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold">旧复盘（Excel）</h2>
          <div className="text-xs text-dim mt-1 flex items-center gap-2 flex-wrap">
            <span>日期：{displayDate}</span>
            <span className="text-dim/40">|</span>
            <Link to="/review" className="text-blue-300 hover:text-blue-200 transition">
              切回 V1 盘后复盘
            </Link>
            <span className="text-dim/40">|</span>
            <Link to="/review/history" className="text-blue-300 hover:text-blue-200 transition">
              历史复盘
            </Link>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="px-3 py-1.5 text-sm bg-input hover:bg-card-hover disabled:opacity-50 rounded-lg transition"
          >
            刷新
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="text-dim text-center py-20">加载中...</div>
      ) : error ? (
        <div className="bg-card rounded-xl p-6 border border-edge">
          <div className="text-sm text-red-300">加载失败：{safeStr((error as any)?.message)}</div>
          <div className="text-xs text-dim mt-2">请检查后端服务与 /api/v1/review/* 接口是否可用</div>
        </div>
      ) : !review ? (
        <div className="bg-card rounded-xl p-8 border border-edge text-center">
          <div className="text-sm text-muted">该日期暂无旧复盘记录</div>
          <div className="text-xs text-dim mt-2">你可以先生成一份草稿（可覆盖更新）</div>
          <div className="mt-4 flex justify-center gap-2">
            <button
              onClick={() => generateMutation.mutate()}
              disabled={generateMutation.isPending}
              className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg transition"
            >
              生成复盘
            </button>
            <Link
              to="/review/history"
              className="px-4 py-2 text-sm bg-input hover:bg-card-hover rounded-lg transition"
            >
              去历史复盘
            </Link>
          </div>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <div className="bg-card rounded-xl p-4 border border-edge">
              <div className="text-xs text-dim">市场情绪</div>
              <div className="text-sm text-secondary mt-1">{review.market_sentiment || "--"}</div>
            </div>
            <div className="bg-card rounded-xl p-4 border border-edge">
              <div className="text-xs text-dim">情绪主阶段</div>
              <div className="text-sm text-secondary mt-1">{review.sentiment_cycle_main || "--"}</div>
            </div>
            <div className="bg-card rounded-xl p-4 border border-edge">
              <div className="text-xs text-dim">市场高度</div>
              <div className="text-sm text-secondary mt-1">{review.market_height || 0} 板</div>
            </div>
            <div className="bg-card rounded-xl p-4 border border-edge">
              <div className="text-xs text-dim">主线板块</div>
              <div className="text-sm text-secondary mt-1">{review.main_sector || "--"}</div>
            </div>
          </div>

          <div className="bg-card rounded-xl p-5 border border-edge">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-muted">复盘内容（可编辑）</h3>
              <div className="flex items-center gap-2">
                <label className="flex items-center gap-2 text-xs text-muted select-none cursor-pointer">
                  <input
                    type="checkbox"
                    checked={confirmed}
                    onChange={(e) => setConfirmed(e.target.checked)}
                    className="accent-blue-500"
                  />
                  已确认（发布）
                </label>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div>
                <div className="text-xs text-dim mb-1">复盘总结</div>
                <textarea
                  className="w-full min-h-[160px] bg-input border border-edge rounded-lg px-3 py-2 text-sm text-secondary"
                  value={reviewSummary}
                  onChange={(e) => setReviewSummary(e.target.value)}
                  placeholder="写下今天的主线、关键分歧、亏钱点/赚钱点..."
                />
              </div>
              <div>
                <div className="text-xs text-dim mb-1">明日计划</div>
                <textarea
                  className="w-full min-h-[160px] bg-input border border-edge rounded-lg px-3 py-2 text-sm text-secondary"
                  value={nextDayPlan}
                  onChange={(e) => setNextDayPlan(e.target.value)}
                  placeholder="写下明日观察方向、仓位纪律、预案..."
                />
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
              <div>
                <div className="text-xs text-dim mb-1">当日动作</div>
                <input
                  className="w-full bg-input border border-edge rounded-lg px-3 py-2 text-sm text-secondary"
                  value={marketAction}
                  onChange={(e) => setMarketAction(e.target.value)}
                  placeholder="如：空仓 / 轻仓试错 / 做了接力 / 只看不做..."
                />
              </div>
              <div>
                <div className="text-xs text-dim mb-1">结果</div>
                <input
                  className="w-full bg-input border border-edge rounded-lg px-3 py-2 text-sm text-secondary"
                  value={marketResult}
                  onChange={(e) => setMarketResult(e.target.value)}
                  placeholder="如：赚 / 亏 / 平 / 执行不到位..."
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 mt-4">
              <button
                onClick={handleReset}
                disabled={updateMutation.isPending}
                className="px-4 py-2 text-sm bg-input hover:bg-card-hover disabled:opacity-50 rounded-lg transition"
              >
                重置
              </button>
              <button
                onClick={handleSave}
                disabled={updateMutation.isPending}
                className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg transition"
              >
                保存
              </button>
            </div>
          </div>

          <div className="bg-card rounded-xl p-5 border border-edge">
            <h3 className="text-sm font-semibold text-muted mb-3">系统产出（只读）</h3>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 text-sm">
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-dim">龙头</span>
                  <span className="text-secondary">{review.market_leader || "--"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-dim">涨停数</span>
                  <span className="text-secondary">{review.total_limit_up || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-dim">首板</span>
                  <span className="text-secondary">{review.first_board_count || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-dim">炸板</span>
                  <span className="text-secondary">{review.broken_board_count || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-dim">成交额</span>
                  <span className="text-secondary">{review.total_volume || "--"}</span>
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-dim">结论象限</span>
                  <span className="text-secondary">{review.conclusion_quadrant || "--"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-dim">适用战法</span>
                  <span className="text-secondary">{review.applicable_strategy || "--"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-dim">建议仓位</span>
                  <span className="text-secondary">{review.suggested_position || "--"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-dim">状态</span>
                  <span className="text-secondary">{review.is_confirmed ? "已确认" : "未确认"}</span>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

