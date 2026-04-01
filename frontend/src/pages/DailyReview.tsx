import { useEffect, useMemo, useState, useCallback } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import api from "../api/client";
import StockDrawer from "../components/StockDrawer";

interface ReviewItem {
  id: number;
  date: string;
  market_sentiment: string;
  market_height: number;
  market_leader: string;
  total_limit_up: number;
  first_board_count: number;
  broken_board_count: number;
  sentiment_detail: string;
  main_sector: string;
  sub_sector: string;
  broken_boards: string;
  review_summary: string;
  next_day_plan: string;
  applicable_strategy: string;
  suggested_position: string;
  ai_review_draft: string;
  ai_next_day_suggestion: string;
  market_action: string;
  market_result: string;
  is_confirmed: boolean;
}

interface LimitUpStock {
  code: string;
  name: string;
  sector: string;
  change_pct: number;
  turnover: number;
}

interface LimitUpData {
  date: string;
  market_height: number;
  market_leader: { code: string; name: string; board_count: number; sector: string } | null;
  ladder: { level: number; count: number; stocks: LimitUpStock[] }[];
  first_board_count: number;
  broken_boards: { code: string; name: string; change_pct: number }[];
}

const phaseOptions = ["冰点", "启动", "发酵", "高潮", "高位混沌", "分歧", "退潮"];

const phaseColors: Record<string, string> = {
  "冰点": "text-blue-300 bg-blue-500/10 border-blue-500/30",
  "启动": "text-cyan-300 bg-cyan-500/10 border-cyan-500/30",
  "发酵": "text-lime-300 bg-lime-500/10 border-lime-500/30",
  "高潮": "text-red-300 bg-red-500/10 border-red-500/30",
  "高位混沌": "text-yellow-300 bg-yellow-500/10 border-yellow-500/30",
  "分歧": "text-purple-300 bg-purple-500/10 border-purple-500/30",
  "退潮": "text-orange-300 bg-orange-500/10 border-orange-500/30",
};

export default function DailyReview() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const dateParam = searchParams.get("date");
  const isHistoryMode = !!dateParam;

  const [review, setReview] = useState<ReviewItem | null>(null);
  const [ladder, setLadder] = useState<LimitUpData | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState<Partial<ReviewItem>>({});
  const [selectedStock, setSelectedStock] = useState<{ code: string; name: string; sector: string } | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const reviewUrl = dateParam ? `/review/date/${dateParam}` : "/review/today";
      const ladderDate = dateParam || "today";

      const [reviewRes, ladderRes] = await Promise.allSettled([
        api.get(reviewUrl),
        api.get(`/market/limit-up?date=${ladderDate}`),
      ]);
      if (reviewRes.status === "fulfilled") {
        setReview(reviewRes.value.data);
        setForm(reviewRes.value.data);
      } else {
        setReview(null);
        setForm({});
      }
      if (ladderRes.status === "fulfilled") setLadder(ladderRes.value.data);
    } finally {
      setLoading(false);
    }
  }, [dateParam]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  async function handleGenerate() {
    setGenerating(true);
    try {
      await api.post("/review/generate");
      await loadData();
    } catch (e: any) {
      if (e.response?.status === 409) {
        alert("今日复盘已存在，可直接编辑确认");
      }
    } finally {
      setGenerating(false);
    }
  }

  async function handleSave(confirm: boolean) {
    if (!review?.id) return;
    setSaving(true);
    try {
      await api.put(`/review/${review.id}`, {
        market_sentiment: form.market_sentiment,
        market_action: form.market_action,
        market_result: form.market_result,
        review_summary: form.review_summary,
        next_day_plan: form.next_day_plan,
        applicable_strategy: form.applicable_strategy,
        suggested_position: form.suggested_position,
        is_confirmed: confirm ? true : form.is_confirmed,
      });
      await loadData();
    } finally {
      setSaving(false);
    }
  }

  function adoptAiDraft() {
    setForm((p) => ({
      ...p,
      review_summary: (p.ai_review_draft || p.review_summary || "").trim(),
      next_day_plan: (p.ai_next_day_suggestion || p.next_day_plan || "").trim(),
    }));
  }

  const phase = form.market_sentiment || review?.market_sentiment || "";

  const ladderLevels = useMemo(() => {
    const items = ladder?.ladder || [];
    return [...items].sort((a, b) => b.level - a.level);
  }, [ladder]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {isHistoryMode && (
            <button
              onClick={() => navigate("/review/history")}
              className="px-3 py-1.5 text-sm bg-input hover:bg-card-hover rounded-lg transition"
            >
              &larr; 返回历史
            </button>
          )}
          <h2 className="text-xl font-bold">
            {isHistoryMode ? `历史复盘 (${dateParam})` : "每日复盘（结构化表单）"}
          </h2>
        </div>
        <div className="flex items-center gap-2">
          {!isHistoryMode && (
            <button
              onClick={handleGenerate}
              disabled={generating}
              className="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg transition"
            >
              {generating ? "生成中..." : "生成草稿"}
            </button>
          )}
          <button
            onClick={() => handleSave(false)}
            disabled={saving || !review}
            className="px-3 py-1.5 text-sm bg-input hover:bg-card-hover disabled:opacity-50 rounded-lg transition"
          >
            {saving ? "保存中..." : "保存"}
          </button>
          <button
            onClick={() => handleSave(true)}
            disabled={saving || !review}
            className="px-3 py-1.5 text-sm bg-emerald-700 hover:bg-emerald-600 disabled:opacity-50 rounded-lg transition"
          >
            {saving ? "确认中..." : "保存并确认"}
          </button>
        </div>
      </div>

      {loading ? (
        <div className="text-dim text-center py-20">加载中...</div>
      ) : !review ? (
        <div className="text-dim text-center py-20">
          {isHistoryMode ? (
            <>
              <p>{dateParam} 无复盘记录</p>
              <p className="text-xs mt-2 text-dim">该日期没有生成过复盘</p>
            </>
          ) : (
            <>
              <p>今日暂无复盘</p>
              <p className="text-xs mt-2 text-dim">点击"生成草稿"从梯队+情绪周期生成复盘草稿</p>
            </>
          )}
        </div>
      ) : (
        <>
          {/* 状态栏 */}
          <div className="bg-card rounded-xl p-5 border border-edge">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="font-mono text-sm">{review.date}</span>
                {phase && (
                  <span className={`px-3 py-1 text-sm rounded-full border ${phaseColors[phase] || "border-edge text-muted"}`}>
                    {phase}
                  </span>
                )}
                {review.is_confirmed && (
                  <span className="text-xs px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
                    已确认
                  </span>
                )}
              </div>
              <div className="text-xs text-dim">
                主线: {review.main_sector || "—"} · 龙头: {review.market_leader || ladder?.market_leader?.name || "—"}
              </div>
            </div>
            {review.sentiment_detail && (
              <div className="mt-3 text-sm text-muted whitespace-pre-line">
                {review.sentiment_detail}
              </div>
            )}
          </div>

          {/* 市场情绪区 */}
          <div className="grid grid-cols-4 gap-4">
            {[
              { label: "市场高度", value: review.market_height, cls: "text-white" },
              { label: "涨停数", value: review.total_limit_up, cls: "text-up" },
              { label: "首板数", value: review.first_board_count, cls: "text-white" },
              { label: "炸板数", value: review.broken_board_count, cls: "text-yellow-300" },
            ].map((c) => (
              <div key={c.label} className="bg-card rounded-xl p-4 border border-edge text-center">
                <div className={`text-2xl font-bold ${c.cls}`}>{c.value ?? 0}</div>
                <div className="text-xs text-dim">{c.label}</div>
              </div>
            ))}
          </div>

          {/* 情绪周期选择 + 盘面过程 */}
          <div className="bg-card rounded-xl p-5 border border-edge space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="text-xs text-dim block mb-1">情绪周期（可改）</label>
                <select
                  className="w-full bg-input border border-edge rounded-lg px-3 py-2 text-sm"
                  value={form.market_sentiment || ""}
                  onChange={(e) => setForm((p) => ({ ...p, market_sentiment: e.target.value }))}
                >
                  <option value="">未选择</option>
                  {phaseOptions.map((p) => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-dim block mb-1">行情类型</label>
                <select
                  className="w-full bg-input border border-edge rounded-lg px-3 py-2 text-sm"
                  value={form.market_action || ""}
                  onChange={(e) => setForm((p) => ({ ...p, market_action: e.target.value }))}
                >
                  <option value="">未选择</option>
                  <option value="普涨">普涨</option>
                  <option value="轮动">轮动</option>
                  <option value="抱团">抱团</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-dim block mb-1">盘面结果</label>
                <select
                  className="w-full bg-input border border-edge rounded-lg px-3 py-2 text-sm"
                  value={form.market_result || ""}
                  onChange={(e) => setForm((p) => ({ ...p, market_result: e.target.value }))}
                >
                  <option value="">未选择</option>
                  <option value="分歧">分歧</option>
                  <option value="修复">修复</option>
                  <option value="一致">一致</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-dim block mb-1">适用战法</label>
                <input
                  className="w-full bg-input border border-edge rounded-lg px-3 py-2 text-sm"
                  value={form.applicable_strategy || ""}
                  onChange={(e) => setForm((p) => ({ ...p, applicable_strategy: e.target.value }))}
                  placeholder="例如：擒龙/补涨套利/回流低吸/试错轻仓"
                />
              </div>
              <div>
                <label className="text-xs text-dim block mb-1">建议仓位</label>
                <input
                  className="w-full bg-input border border-edge rounded-lg px-3 py-2 text-sm"
                  value={form.suggested_position || ""}
                  onChange={(e) => setForm((p) => ({ ...p, suggested_position: e.target.value }))}
                  placeholder="例如：1/4仓、半仓"
                />
              </div>
            </div>
          </div>

          {/* 梯队数据 */}
          <div className="bg-card rounded-xl border border-edge overflow-hidden">
            <div className="px-5 py-3 border-b border-edge flex items-center justify-between">
              <h3 className="text-sm font-semibold text-muted">涨停/连板梯队（替代截图）</h3>
              <div className="text-xs text-dim">来源：AKShare → SQLite 快照</div>
            </div>
            {!ladderLevels.length ? (
              <div className="text-dim text-center py-16">暂无梯队数据（请先同步市场数据或执行复盘）</div>
            ) : (
              <div className="divide-y divide-edge">
                {ladderLevels.map((lv) => (
                  <div key={lv.level} className="p-5">
                    <div className="flex items-center justify-between mb-3">
                      <div className="text-sm font-semibold">
                        {lv.level} 板 <span className="text-dim text-xs">({lv.count}只)</span>
                      </div>
                      {ladder?.market_leader?.board_count === lv.level && (
                        <div className="text-xs px-2 py-0.5 rounded bg-red-500/10 text-red-300 border border-red-500/30">
                          龙头层
                        </div>
                      )}
                    </div>
                    <div className="grid grid-cols-4 gap-2">
                      {(lv.stocks || []).slice(0, 12).map((s) => (
                        <div
                          key={s.code}
                          className="bg-base border border-edge rounded-lg p-3 cursor-pointer hover:border-blue-500/50 hover:bg-card transition"
                          onClick={() => setSelectedStock({ code: s.code, name: s.name, sector: s.sector })}
                        >
                          <div className="text-sm font-mono">{s.code}</div>
                          <div className="text-sm font-medium truncate">{s.name}</div>
                          <div className="text-xs text-dim truncate">{s.sector || "—"}</div>
                          <div className="text-xs mt-1 text-up">+{(s.change_pct ?? 0).toFixed(1)}%</div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 复盘总结（AI 草稿对比 + 可编辑） */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-card rounded-xl p-5 border border-edge">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-semibold text-muted">AI 草稿</h3>
                <button
                  onClick={adoptAiDraft}
                  className="px-3 py-1 text-xs bg-input hover:bg-card-hover rounded-lg transition"
                >
                  采纳 AI 建议
                </button>
              </div>
              <div className="text-sm text-muted whitespace-pre-line">
                {(review.ai_review_draft || review.review_summary || "暂无").trim()}
              </div>
              <div className="mt-4 text-xs text-dim">次日建议：</div>
              <div className="text-sm text-muted whitespace-pre-line">
                {(review.ai_next_day_suggestion || review.next_day_plan || "暂无").trim()}
              </div>
            </div>
            <div className="bg-card rounded-xl p-5 border border-edge space-y-3">
              <h3 className="text-sm font-semibold text-muted">人工编辑区</h3>
              <div>
                <label className="text-xs text-dim block mb-1">复盘总结</label>
                <textarea
                  className="w-full bg-input border border-edge rounded-lg px-3 py-2 text-sm min-h-[140px]"
                  value={form.review_summary || ""}
                  onChange={(e) => setForm((p) => ({ ...p, review_summary: e.target.value }))}
                  placeholder="修改/补充你的最终复盘总结"
                />
              </div>
              <div>
                <label className="text-xs text-dim block mb-1">次日计划</label>
                <textarea
                  className="w-full bg-input border border-edge rounded-lg px-3 py-2 text-sm min-h-[120px]"
                  value={form.next_day_plan || ""}
                  onChange={(e) => setForm((p) => ({ ...p, next_day_plan: e.target.value }))}
                  placeholder="写下次日操作模式/计划/仓位控制"
                />
              </div>
            </div>
          </div>
        </>
      )}

      {selectedStock && (
        <StockDrawer
          code={selectedStock.code}
          name={selectedStock.name}
          sector={selectedStock.sector}
          onClose={() => setSelectedStock(null)}
        />
      )}
    </div>
  );
}
