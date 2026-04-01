import { useEffect, useMemo, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";
import SentimentTrend from "../components/charts/SentimentTrend";

interface ReviewItem {
  id: number;
  date: string;
  market_sentiment: string;
  market_height: number;
  market_leader: string;
  main_sector: string;
  review_summary: string;
  is_confirmed: boolean;
}

interface SentimentLog {
  id: number;
  date: string;
  cycle_phase: string;
  market_height: number;
  main_sector: string;
  transition_note: string;
}

const phaseColors: Record<string, string> = {
  "冰点": "bg-blue-500/15 text-blue-300 border-blue-500/30",
  "启动": "bg-cyan-500/15 text-cyan-300 border-cyan-500/30",
  "发酵": "bg-lime-500/15 text-lime-300 border-lime-500/30",
  "高潮": "bg-red-500/15 text-red-300 border-red-500/30",
  "高位混沌": "bg-yellow-500/15 text-yellow-300 border-yellow-500/30",
  "分歧": "bg-purple-500/15 text-purple-300 border-purple-500/30",
  "退潮": "bg-orange-500/15 text-orange-300 border-orange-500/30",
};

function daysBetween(a: Date, b: Date) {
  return Math.floor((a.getTime() - b.getTime()) / (24 * 3600 * 1000));
}

function iso(d: Date) {
  return d.toISOString().slice(0, 10);
}

export default function ReviewHistory() {
  const navigate = useNavigate();
  const [reviews, setReviews] = useState<ReviewItem[]>([]);
  const [sentiment, setSentiment] = useState<SentimentLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [phaseFilter, setPhaseFilter] = useState<string>("全部");

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [r1, r2] = await Promise.allSettled([
        api.get("/review/list?limit=100"),
        api.get("/review/sentiment?limit=90"),
      ]);
      if (r1.status === "fulfilled") setReviews(r1.value.data || []);
      if (r2.status === "fulfilled") setSentiment(r2.value.data || []);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const reviewMap = useMemo(() => {
    const m = new Map<string, ReviewItem>();
    for (const r of reviews) m.set(r.date, r);
    return m;
  }, [reviews]);

  const recentDays = useMemo(() => {
    const today = new Date();
    const list: Date[] = [];
    for (let i = 0; i < 90; i++) {
      const d = new Date(today);
      d.setDate(today.getDate() - i);
      list.push(d);
    }
    return list.reverse();
  }, []);

  const filteredReviews = useMemo(() => {
    if (phaseFilter === "全部") return reviews;
    return reviews.filter((r) => r.market_sentiment === phaseFilter);
  }, [reviews, phaseFilter]);

  const phases = useMemo(() => {
    const set = new Set<string>();
    for (const r of reviews) if (r.market_sentiment) set.add(r.market_sentiment);
    return ["全部", ...Array.from(set)];
  }, [reviews]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">历史复盘</h2>
        <div className="flex items-center gap-2">
          <select
            className="bg-card border border-edge rounded-lg px-3 py-1.5 text-sm"
            value={phaseFilter}
            onChange={(e) => setPhaseFilter(e.target.value)}
          >
            {phases.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
          <button
            onClick={loadData}
            className="px-3 py-1.5 text-sm bg-input hover:bg-card-hover rounded-lg transition"
          >
            刷新
          </button>
        </div>
      </div>

      {loading ? (
        <div className="text-dim text-center py-20">加载中...</div>
      ) : (
        <>
          {/* 情绪趋势图 */}
          <div className="bg-card rounded-xl p-5 border border-edge">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-muted">情绪周期趋势（近90天）</h3>
              <div className="text-xs text-dim">纵轴：市场高度</div>
            </div>
            <SentimentTrend
              data={sentiment.map((s) => ({ date: s.date, cycle_phase: s.cycle_phase, market_height: s.market_height }))}
              height={220}
            />
          </div>

          {/* 日历视图（近90天） */}
          <div className="bg-card rounded-xl p-5 border border-edge">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-muted">日历视图（近90天）</h3>
              <div className="text-xs text-dim">
                有复盘的日期可点击进入详情
              </div>
            </div>
            <div className="grid grid-cols-15 gap-2">
              {recentDays.map((d) => {
                const key = iso(d);
                const r = reviewMap.get(key);
                const phase = r?.market_sentiment || "";
                const cls = phase ? (phaseColors[phase] || "bg-input text-secondary border-edge") : "bg-base text-dim border-gray-900";
                const dim = daysBetween(new Date(), d) < 7 ? "ring-1 ring-blue-500/20" : "";
                const clickable = !!r && (phaseFilter === "全部" || phase === phaseFilter);
                return (
                  <button
                    key={key}
                    onClick={() => clickable && navigate(`/review?date=${key}`)}
                    className={`h-14 rounded-lg border p-2 text-left transition ${cls} ${dim} ${clickable ? "hover:bg-card-hover" : "opacity-60 cursor-default"}`}
                    disabled={!clickable}
                    title={r ? `${key} ${phase} 高度${r.market_height}板` : key}
                  >
                    <div className="text-[11px] font-mono">{key.slice(5)}</div>
                    {r ? (
                      <div className="mt-1 text-[11px] text-secondary/90 truncate">
                        {phase} · {r.market_height}板
                      </div>
                    ) : (
                      <div className="mt-1 text-[11px] text-dim">—</div>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* 列表（筛选后的） */}
          <div className="bg-card rounded-xl border border-edge">
            <div className="px-5 py-3 border-b border-edge flex items-center justify-between">
              <h3 className="text-sm font-semibold text-muted">复盘列表</h3>
              <div className="text-xs text-dim">共 {filteredReviews.length} 条</div>
            </div>
            <div className="divide-y divide-edge">
              {filteredReviews.map((r) => (
                <button
                  key={r.id}
                  onClick={() => navigate(`/review?date=${r.date}`)}
                  className="w-full text-left px-5 py-3 hover:bg-card-hover transition"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm">{r.date}</span>
                      {r.market_sentiment && (
                        <span className={`text-xs px-2 py-0.5 rounded border ${phaseColors[r.market_sentiment] || "border-edge text-muted"}`}>
                          {r.market_sentiment}
                        </span>
                      )}
                      {r.is_confirmed ? (
                        <span className="text-xs px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
                          已确认
                        </span>
                      ) : (
                        <span className="text-xs px-2 py-0.5 rounded bg-gray-500/10 text-dim border border-edge">
                          未确认
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-dim flex items-center gap-3">
                      {r.market_leader && <span>龙头: {r.market_leader}</span>}
                      <span>高度 {r.market_height} 板</span>
                    </div>
                  </div>
                  <div className="mt-1 text-sm text-secondary truncate">
                    {r.main_sector ? `主线: ${r.main_sector} · ` : ""}{r.review_summary || "—"}
                  </div>
                </button>
              ))}
              {filteredReviews.length === 0 && (
                <div className="text-dim text-center py-16">暂无复盘数据</div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
