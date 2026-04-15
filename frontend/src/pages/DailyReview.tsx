import { useEffect, useMemo, useState, useCallback } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import api from "../api/client";
import StockDrawer from "../components/StockDrawer";

interface ReviewItem {
  id: number;
  date: string;
  status: string;
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
  sentiment_cycle_sub: string;
  index_sentiment_sh: string;
  index_sentiment_csm: string;
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
  limit_down_count?: number;
  promotion_rate_text?: string;
}

const phaseOptions = ["启动期", "发酵期", "高潮期", "高位混沌期", "退潮期", "低位混沌期"];
const quadrantOptions = ["情指共振", "情好指差", "情差指好", "情指双杀"];

function ComboBox({
  value,
  onChange,
  options,
  placeholder = "",
}: {
  value: string;
  onChange: (v: string) => void;
  options: string[];
  placeholder?: string;
}) {
  const [open, setOpen] = useState(false);
  const filtered = options.filter(
    (o) => !value || o.includes(value),
  );
  return (
    <div className="relative">
      <input
        className="w-full bg-input border border-edge rounded-lg px-3 py-2 text-sm"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        placeholder={placeholder || "可选择或输入"}
      />
      {open && filtered.length > 0 && (
        <ul className="absolute z-20 mt-1 w-full bg-card border border-edge rounded-lg shadow-lg max-h-48 overflow-y-auto">
          {filtered.map((o) => (
            <li
              key={o}
              className={`px-3 py-2 text-sm cursor-pointer hover:bg-card-hover transition ${o === value ? "text-blue-400" : ""}`}
              onMouseDown={(e) => {
                e.preventDefault();
                onChange(o);
                setOpen(false);
              }}
            >
              {o}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

const phaseColors: Record<string, string> = {
  "启动期": "text-cyan-300 bg-cyan-500/10 border-cyan-500/30",
  "发酵期": "text-lime-300 bg-lime-500/10 border-lime-500/30",
  "高潮期": "text-red-300 bg-red-500/10 border-red-500/30",
  "高位混沌期": "text-yellow-300 bg-yellow-500/10 border-yellow-500/30",
  "退潮期": "text-orange-300 bg-orange-500/10 border-orange-500/30",
  "低位混沌期": "text-blue-300 bg-blue-500/10 border-blue-500/30",
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
      const params = dateParam ? `?target_date=${dateParam}` : "";
      await api.post(`/review/generate${params}`);
      await loadData();
    } catch (e: any) {
      const status = e.response?.status;
      const detail = e.response?.data?.detail || e.message || "未知错误";
      if (status === 409) {
        alert("该日期复盘已存在，可直接编辑确认");
      } else {
        alert(`生成复盘失败: ${detail}`);
      }
    } finally {
      setGenerating(false);
    }
  }

  async function handleSave(confirm: boolean) {
    if (!review?.id) return;
    setSaving(true);
    try {
      const nextDayPlan = [form.next_day_prediction, form.next_day_mode].filter(Boolean).join("\n");
      const targetStatus = confirm ? "published" : (form.status || review.status || "draft");
      const sentimentCycleMain = form.sentiment_cycle_main || undefined;
      const conclusionQuadrant = form.conclusion_quadrant || undefined;
      await api.put(`/review/${review.id}`, {
        status: targetStatus,
        sentiment_cycle_main: sentimentCycleMain,
        market_sentiment: form.market_sentiment,
        dragon_stock: form.dragon_stock,
        core_middle_stock: form.core_middle_stock,
        market_ladder: form.market_ladder,
        total_volume: form.total_volume,
        main_sectors: form.main_sectors,
        sub_sectors: form.sub_sectors,
        market_style: form.market_style,
        broken_high_stock: form.broken_high_stock,
        sentiment_cycle_sub: form.sentiment_cycle_sub,
        index_sentiment_sh: form.index_sentiment_sh,
        index_sentiment_csm: form.index_sentiment_csm,
        conclusion_quadrant: conclusionQuadrant,
        next_day_prediction: form.next_day_prediction,
        next_day_mode: form.next_day_mode,
        market_action: form.market_action,
        market_result: form.market_result,
        review_summary: form.review_summary,
        next_day_plan: nextDayPlan || form.next_day_plan,
        applicable_strategy: form.applicable_strategy,
        suggested_position: form.suggested_position,
        is_confirmed: targetStatus === "published",
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
      next_day_prediction: (p.ai_next_day_suggestion || p.next_day_prediction || "").trim(),
      next_day_plan: (p.ai_next_day_suggestion || p.next_day_plan || "").trim(),
    }));
  }

  const phase = form.sentiment_cycle_main || form.market_sentiment || review?.sentiment_cycle_main || review?.market_sentiment || "";
  const status = form.status || review?.status || "draft";

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
          <h2 className="text-xl font-bold">{isHistoryMode ? `历史复盘 (${dateParam})` : "每日复盘工作台"}</h2>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg transition"
          >
            {generating ? "生成中..." : isHistoryMode ? "补充复盘" : "生成草稿"}
          </button>
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
            {saving ? "发布中..." : "定稿发布"}
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
              <p className="text-xs mt-2 text-dim">点击上方"补充复盘"按钮为该日期生成复盘草稿</p>
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
          <div className="bg-card rounded-xl p-5 border border-edge">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="font-mono text-sm">{review.date}</span>
                {phase && (
                  <span className={`px-3 py-1 text-sm rounded-full border ${phaseColors[phase] || "border-edge text-muted"}`}>
                    {phase}
                  </span>
                )}
                {status === "published" && (
                  <span className="text-xs px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
                    已定稿
                  </span>
                )}
              </div>
              <div className="text-xs text-dim">
                主线: {review.main_sectors || review.main_sector || "—"} · 龙头: {review.dragon_stock || review.market_leader || ladder?.market_leader?.name || "—"}
              </div>
            </div>
            {review.sentiment_detail && (
              <div className="mt-3 text-sm text-muted whitespace-pre-line">
                {review.sentiment_detail}
              </div>
            )}
          </div>
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            <div className="space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
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

              <div className="bg-card rounded-xl p-4 border border-edge">
                <h3 className="text-sm font-semibold text-muted mb-3">盘面快照</h3>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <div className="text-dim text-xs">沪深成交额及增量</div>
                    <div className="mt-1">{form.total_volume || review.total_volume || "—"}</div>
                  </div>
                  <div>
                    <div className="text-dim text-xs">连板晋级率</div>
                    <div className="mt-1">{ladder?.promotion_rate_text || "—"}</div>
                  </div>
                  <div>
                    <div className="text-dim text-xs">市场高度</div>
                    <div className="mt-1">{review.market_height || ladder?.market_height || "—"}板</div>
                  </div>
                  <div>
                    <div className="text-dim text-xs">龙头</div>
                    <div className="mt-1">{review.dragon_stock || review.market_leader || ladder?.market_leader?.name || "—"}</div>
                  </div>
                  <div>
                    <div className="text-dim text-xs">涨停数 / 首板 / 炸板</div>
                    <div className="mt-1">
                      <span className="text-up">{review.total_limit_up || "—"}</span>
                      {" / "}
                      <span>{review.first_board_count || "—"}</span>
                      {" / "}
                      <span className="text-yellow-300">{review.broken_board_count || "—"}</span>
                    </div>
                  </div>
                  <div>
                    <div className="text-dim text-xs">跌停数</div>
                    <div className="mt-1 text-down">{ladder?.limit_down_count ?? "—"}</div>
                  </div>
                </div>
              </div>

              <div className="bg-card rounded-xl border border-edge overflow-hidden">
                <div className="px-5 py-3 border-b border-edge flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-muted">左侧盘面看板（涨停/连板梯队）</h3>
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
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
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
                  {(review.ai_next_day_suggestion || review.next_day_prediction || review.next_day_plan || "暂无").trim()}
                </div>
              </div>
            </div>

            <div className="bg-card rounded-xl p-5 border border-edge space-y-4">
              <h3 className="text-sm font-semibold text-muted">右侧人工审阅表单</h3>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-dim block mb-1">情绪周期</label>
                  <ComboBox
                    value={form.sentiment_cycle_main || ""}
                    onChange={(v) => setForm((p) => ({ ...p, sentiment_cycle_main: v, market_sentiment: v }))}
                    options={phaseOptions}
                    placeholder="选择或输入情绪周期"
                  />
                </div>
                <div>
                  <label className="text-xs text-dim block mb-1">四象限结论</label>
                  <ComboBox
                    value={form.conclusion_quadrant || ""}
                    onChange={(v) => setForm((p) => ({ ...p, conclusion_quadrant: v }))}
                    options={quadrantOptions}
                    placeholder="选择或输入四象限结论"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs text-dim block mb-1">情绪周期次线</label>
                <input
                  className="w-full bg-input border border-edge rounded-lg px-3 py-2 text-sm"
                  value={form.sentiment_cycle_sub || ""}
                  onChange={(e) => setForm((p) => ({ ...p, sentiment_cycle_sub: e.target.value }))}
                  placeholder="如：启动、发酵、高潮延伸"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-dim block mb-1">上证情绪阶段</label>
                  <input
                    className="w-full bg-input border border-edge rounded-lg px-3 py-2 text-sm"
                    value={form.index_sentiment_sh || ""}
                    onChange={(e) => setForm((p) => ({ ...p, index_sentiment_sh: e.target.value }))}
                    placeholder="如：下跌一阶混沌修复"
                  />
                </div>
                <div>
                  <label className="text-xs text-dim block mb-1">中小创情绪阶段</label>
                  <input
                    className="w-full bg-input border border-edge rounded-lg px-3 py-2 text-sm"
                    value={form.index_sentiment_csm || ""}
                    onChange={(e) => setForm((p) => ({ ...p, index_sentiment_csm: e.target.value }))}
                    placeholder="如：高位混沌分歧转修复"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-dim block mb-1">市场龙头</label>
                  <input
                    className="w-full bg-input border border-edge rounded-lg px-3 py-2 text-sm"
                    value={form.dragon_stock || ""}
                    onChange={(e) => setForm((p) => ({ ...p, dragon_stock: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="text-xs text-dim block mb-1">核心中军</label>
                  <input
                    className="w-full bg-input border border-edge rounded-lg px-3 py-2 text-sm"
                    value={form.core_middle_stock || ""}
                    onChange={(e) => setForm((p) => ({ ...p, core_middle_stock: e.target.value }))}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-dim block mb-1">主线板块</label>
                  <input
                    className="w-full bg-input border border-edge rounded-lg px-3 py-2 text-sm"
                    value={form.main_sectors || ""}
                    onChange={(e) => setForm((p) => ({ ...p, main_sectors: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="text-xs text-dim block mb-1">次线板块</label>
                  <input
                    className="w-full bg-input border border-edge rounded-lg px-3 py-2 text-sm"
                    value={form.sub_sectors || ""}
                    onChange={(e) => setForm((p) => ({ ...p, sub_sectors: e.target.value }))}
                  />
                </div>
              </div>

              <div>
                <label className="text-xs text-dim block mb-1">市场风格</label>
                <input
                  className="w-full bg-input border border-edge rounded-lg px-3 py-2 text-sm"
                  value={form.market_style || ""}
                  onChange={(e) => setForm((p) => ({ ...p, market_style: e.target.value }))}
                  placeholder="例如：连板趋势对撞高切低"
                />
              </div>

              <div>
                <label className="text-xs text-dim block mb-1">断板高标</label>
                <input
                  className="w-full bg-input border border-edge rounded-lg px-3 py-2 text-sm"
                  value={form.broken_high_stock || ""}
                  onChange={(e) => setForm((p) => ({ ...p, broken_high_stock: e.target.value }))}
                />
              </div>

              <div>
                <label className="text-xs text-dim block mb-1">沪深成交额及增量</label>
                <input
                  className="w-full bg-input border border-edge rounded-lg px-3 py-2 text-sm"
                  value={form.total_volume || ""}
                  onChange={(e) => setForm((p) => ({ ...p, total_volume: e.target.value }))}
                  placeholder="例如：20061亿 +783亿"
                />
              </div>

              <div>
                <label className="text-xs text-dim block mb-1">市场梯队（几板几家）</label>
                <textarea
                  className="w-full bg-input border border-edge rounded-lg px-3 py-2 text-sm min-h-[80px]"
                  value={form.market_ladder || ""}
                  onChange={(e) => setForm((p) => ({ ...p, market_ladder: e.target.value }))}
                />
              </div>

              <div>
                <label className="text-xs text-dim block mb-1">次日推演预判</label>
                <textarea
                  className="w-full bg-input border border-edge rounded-lg px-3 py-2 text-sm min-h-[90px]"
                  value={form.next_day_prediction || ""}
                  onChange={(e) => setForm((p) => ({ ...p, next_day_prediction: e.target.value }))}
                />
              </div>

              <div>
                <label className="text-xs text-dim block mb-1">次日模式及标的</label>
                <textarea
                  className="w-full bg-input border border-edge rounded-lg px-3 py-2 text-sm min-h-[90px]"
                  value={form.next_day_mode || ""}
                  onChange={(e) => setForm((p) => ({ ...p, next_day_mode: e.target.value }))}
                  placeholder="需体现擒龙/补涨/缠龙/试错"
                />
              </div>

              <div>
                <label className="text-xs text-dim block mb-1">复盘总结</label>
                <textarea
                  className="w-full bg-input border border-edge rounded-lg px-3 py-2 text-sm min-h-[120px]"
                  value={form.review_summary || ""}
                  onChange={(e) => setForm((p) => ({ ...p, review_summary: e.target.value }))}
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-dim block mb-1">适用战法</label>
                  <input
                    className="w-full bg-input border border-edge rounded-lg px-3 py-2 text-sm"
                    value={form.applicable_strategy || ""}
                    onChange={(e) => setForm((p) => ({ ...p, applicable_strategy: e.target.value }))}
                  />
                </div>
                <div>
                  <label className="text-xs text-dim block mb-1">建议仓位</label>
                  <input
                    className="w-full bg-input border border-edge rounded-lg px-3 py-2 text-sm"
                    value={form.suggested_position || ""}
                    onChange={(e) => setForm((p) => ({ ...p, suggested_position: e.target.value }))}
                  />
                </div>
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
