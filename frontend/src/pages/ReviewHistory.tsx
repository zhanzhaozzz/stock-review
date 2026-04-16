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
  "退潮": "bg-orange-500/15 text-orange-300 border-orange-500/30",
};

const WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"];

function iso(d: Date) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function getMonthDays(year: number, month: number) {
  return new Date(year, month + 1, 0).getDate();
}

function getFirstDayOfWeek(year: number, month: number) {
  const day = new Date(year, month, 1).getDay();
  return day === 0 ? 6 : day - 1;
}

export default function ReviewHistory() {
  const navigate = useNavigate();
  const [reviews, setReviews] = useState<ReviewItem[]>([]);
  const [sentiment, setSentiment] = useState<SentimentLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [phaseFilter, setPhaseFilter] = useState<string>("全部");

  const now = new Date();
  const [calYear, setCalYear] = useState(now.getFullYear());
  const [calMonth, setCalMonth] = useState(now.getMonth());

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [r1, r2] = await Promise.allSettled([
        api.get("/review/list?limit=200"),
        api.get("/review/sentiment?limit=200"),
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

  const calendarCells = useMemo(() => {
    const totalDays = getMonthDays(calYear, calMonth);
    const startWeekday = getFirstDayOfWeek(calYear, calMonth);
    const cells: (Date | null)[] = [];
    for (let i = 0; i < startWeekday; i++) cells.push(null);
    for (let d = 1; d <= totalDays; d++) cells.push(new Date(calYear, calMonth, d));
    const trailing = (7 - (cells.length % 7)) % 7;
    for (let i = 0; i < trailing; i++) cells.push(null);
    return cells;
  }, [calYear, calMonth]);

  const prevMonth = () => {
    if (calMonth === 0) { setCalYear((y) => y - 1); setCalMonth(11); }
    else setCalMonth((m) => m - 1);
  };
  const nextMonth = () => {
    if (calMonth === 11) { setCalYear((y) => y + 1); setCalMonth(0); }
    else setCalMonth((m) => m + 1);
  };
  const goToday = () => {
    const t = new Date();
    setCalYear(t.getFullYear());
    setCalMonth(t.getMonth());
  };

  const isCurrentMonth = calYear === now.getFullYear() && calMonth === now.getMonth();
  const todayStr = iso(now);

  const filteredReviews = useMemo(() => {
    if (phaseFilter === "全部") return reviews;
    return reviews.filter((r) => r.market_sentiment === phaseFilter);
  }, [reviews, phaseFilter]);

  const phases = useMemo(() => {
    const set = new Set<string>();
    for (const r of reviews) if (r.market_sentiment) set.add(r.market_sentiment);
    return ["全部", ...Array.from(set)];
  }, [reviews]);

  const monthStats = useMemo(() => {
    let total = 0, confirmed = 0;
    const phaseCount: Record<string, number> = {};
    for (const cell of calendarCells) {
      if (!cell) continue;
      const r = reviewMap.get(iso(cell));
      if (r) {
        total++;
        if (r.is_confirmed) confirmed++;
        if (r.market_sentiment) phaseCount[r.market_sentiment] = (phaseCount[r.market_sentiment] || 0) + 1;
      }
    }
    return { total, confirmed, phaseCount };
  }, [calendarCells, reviewMap]);

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

          {/* 月历视图 */}
          <div className="bg-card rounded-xl p-5 border border-edge">
            {/* 月份导航 */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <button onClick={prevMonth} className="w-8 h-8 flex items-center justify-center rounded-lg bg-input hover:bg-card-hover transition text-sm">&lt;</button>
                <h3 className="text-base font-semibold tabular-nums min-w-[120px] text-center">
                  {calYear} 年 {calMonth + 1} 月
                </h3>
                <button onClick={nextMonth} className="w-8 h-8 flex items-center justify-center rounded-lg bg-input hover:bg-card-hover transition text-sm">&gt;</button>
                {!isCurrentMonth && (
                  <button onClick={goToday} className="ml-2 px-3 py-1 text-xs rounded-lg bg-blue-500/15 text-blue-300 border border-blue-500/30 hover:bg-blue-500/25 transition">
                    回到本月
                  </button>
                )}
              </div>
              <div className="flex items-center gap-4 text-xs text-dim">
                <span>复盘 {monthStats.total} 天</span>
                <span>已确认 {monthStats.confirmed} 天</span>
                {Object.entries(monthStats.phaseCount).map(([p, c]) => (
                  <span key={p} className={phaseColors[p]?.split(" ")[1] || "text-dim"}>
                    {p} {c}
                  </span>
                ))}
              </div>
            </div>

            {/* 星期表头 */}
            <div className="grid grid-cols-7 gap-2 mb-2">
              {WEEKDAYS.map((w, i) => (
                <div key={w} className={`text-center text-xs font-medium py-1 ${i >= 5 ? "text-dim/50" : "text-muted"}`}>
                  {w}
                </div>
              ))}
            </div>

            {/* 日期格子 */}
            <div className="grid grid-cols-7 gap-2">
              {calendarCells.map((cell, idx) => {
                if (!cell) {
                  return <div key={`empty-${idx}`} className="h-[72px]" />;
                }
                const key = iso(cell);
                const r = reviewMap.get(key);
                const phase = r?.market_sentiment || "";
                const isWeekend = cell.getDay() === 0 || cell.getDay() === 6;
                const isFuture = key > todayStr;
                const isToday = key === todayStr;
                const isTradeDay = !isWeekend && !isFuture;

                const bgCls = phase
                  ? (phaseColors[phase] || "bg-input text-secondary border-edge")
                  : isWeekend
                    ? "bg-base/50 text-dim/40 border-transparent"
                    : isFuture
                      ? "bg-base text-dim/40 border-gray-800/50"
                      : "bg-base text-dim border-gray-800 border-dashed";

                const todayRing = isToday ? "ring-2 ring-blue-500/40" : "";
                const clickable = isTradeDay && (phaseFilter === "全部" || !r || phase === phaseFilter);

                return (
                  <button
                    key={key}
                    onClick={() => clickable && navigate(`/review?date=${key}`)}
                    className={`h-[72px] rounded-lg border p-2 text-left transition ${bgCls} ${todayRing} ${clickable ? "hover:bg-card-hover cursor-pointer" : isWeekend || isFuture ? "cursor-default" : "opacity-50 cursor-default"}`}
                    disabled={!clickable}
                    title={r ? `${key} ${phase} 高度${r.market_height}板` : isTradeDay ? `${key} 点击补充复盘` : key}
                  >
                    <div className="flex items-center justify-between">
                      <span className={`text-xs font-mono ${isToday ? "text-blue-400 font-bold" : ""}`}>
                        {cell.getDate()}
                      </span>
                      {r?.is_confirmed && (
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                      )}
                    </div>
                    {r ? (
                      <div className="mt-1.5 space-y-0.5">
                        <div className="text-[11px] truncate">{phase}</div>
                        <div className="text-[10px] text-secondary/70">{r.market_height}板</div>
                      </div>
                    ) : isTradeDay ? (
                      <div className="mt-2 text-[11px] text-dim/50">补盘</div>
                    ) : null}
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
