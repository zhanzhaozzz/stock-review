import { Link } from "react-router-dom";
import { useCombatDesk } from "../hooks/useCombatData";
import type { BattleBrief, MarketStateDaily, CandidatePoolEntry } from "../hooks/useCombatData";

const toneColors: Record<string, string> = {
  "可做": "border-emerald-500 bg-emerald-500/10 text-emerald-400",
  "轻仓试错": "border-yellow-500 bg-yellow-500/10 text-yellow-400",
  "防守观察": "border-orange-500 bg-orange-500/10 text-orange-400",
  "不做": "border-red-500 bg-red-500/10 text-red-400",
};

const toneLabels: Record<string, string> = {
  "可做": "今日可做",
  "轻仓试错": "轻仓试错",
  "防守观察": "防守观察",
  "不做": "今日不做",
};

const phaseColors: Record<string, string> = {
  "冰点": "text-blue-300 bg-blue-500/10",
  "启动": "text-cyan-300 bg-cyan-500/10",
  "发酵": "text-lime-300 bg-lime-500/10",
  "高潮": "text-red-300 bg-red-500/10",
  "高位混沌": "text-yellow-300 bg-yellow-500/10",
  "退潮": "text-orange-300 bg-orange-500/10",
};

const gateColors: Record<string, string> = {
  "通过": "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
  "观察": "text-yellow-400 bg-yellow-500/10 border-yellow-500/30",
  "拦截": "text-red-400 bg-red-500/10 border-red-500/30",
};

function renderListItems(items: unknown[] | null | undefined): string[] {
  if (!items) return [];
  if (!Array.isArray(items)) return [String(items)];
  return items.map((item) => (typeof item === "string" ? item : JSON.stringify(item)));
}

function formatVolume(val: number | null | undefined): string {
  if (!val) return "--";
  if (val >= 1e8) return (val / 1e8).toFixed(0) + "亿";
  if (val >= 1e4) return (val / 1e4).toFixed(0) + "万";
  return String(val);
}

function ToneBlock({ brief, marketState }: { brief: BattleBrief | null; marketState: MarketStateDaily | null }) {
  const tone = brief?.status_tone;
  const colorCls = tone ? (toneColors[tone] || "border-edge bg-card text-muted") : "border-edge bg-card text-muted";

  return (
    <div className={`rounded-xl p-6 border-2 ${colorCls}`}>
      <div className="flex items-start justify-between gap-6">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-3">
            <span className="text-2xl font-bold">
              {tone ? (toneLabels[tone] || tone) : "暂无定调"}
            </span>
            {brief?.suggested_position && (
              <span className="text-sm px-2 py-0.5 rounded bg-card border border-edge text-muted">
                仓位: {brief.suggested_position}
              </span>
            )}
          </div>
          {brief?.overall_conclusion && (
            <p className="text-sm opacity-90 leading-relaxed">{brief.overall_conclusion}</p>
          )}
          {!brief && (
            <p className="text-sm text-dim">今日作战简报尚未生成，请先在后端执行生成任务</p>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {marketState?.market_phase && (
            <span className={`text-xs px-2.5 py-1 rounded-full ${phaseColors[marketState.market_phase] || "bg-card text-muted"}`}>
              {marketState.market_phase}
            </span>
          )}
          {marketState?.style_tag && (
            <span className="text-xs px-2.5 py-1 rounded-full bg-card text-muted">
              {marketState.style_tag}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

function DisciplineBlock({ brief }: { brief: BattleBrief | null }) {
  const items = renderListItems(brief?.forbidden_actions).slice(0, 3);
  if (items.length === 0) return null;

  return (
    <div className="bg-red-500/5 border border-red-500/20 rounded-xl p-4">
      <h3 className="text-xs font-semibold text-red-400 mb-2">纪律警报</h3>
      <div className="space-y-1.5">
        {items.map((item, i) => (
          <div key={i} className="flex items-start gap-2 text-sm text-red-300">
            <span className="shrink-0 mt-0.5">⛔</span>
            <span>{item}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function MarketNarrativeBlock({ marketState, brief }: { marketState: MarketStateDaily | null; brief: BattleBrief | null }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* 左栏：客观市场状态 */}
      <div className="bg-card rounded-xl p-5 border border-edge">
        <h3 className="text-sm font-semibold text-muted mb-4">市场状态</h3>
        {marketState ? (
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-primary">{marketState.temperature_score ?? "--"}</div>
              <div className="text-xs text-dim mt-1">情绪温度</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-up">{marketState.limit_up_count ?? "--"}</div>
              <div className="text-xs text-dim mt-1">涨停</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-down">{marketState.limit_down_count ?? "--"}</div>
              <div className="text-xs text-dim mt-1">跌停</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-yellow-300">{marketState.boom_rate != null ? (marketState.boom_rate * 100).toFixed(0) + "%" : "--"}</div>
              <div className="text-xs text-dim mt-1">炸板率</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-primary">{marketState.highest_ladder ?? "--"}</div>
              <div className="text-xs text-dim mt-1">最高连板</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-primary">{formatVolume(marketState.total_volume)}</div>
              <div className="text-xs text-dim mt-1">成交额</div>
            </div>
          </div>
        ) : (
          <div className="text-sm text-dim text-center py-8">暂无市场状态数据</div>
        )}
      </div>

      {/* 右栏：今日叙事 */}
      <div className="bg-card rounded-xl p-5 border border-edge">
        <h3 className="text-sm font-semibold text-muted mb-4">今日叙事</h3>
        {brief ? (
          <div className="space-y-3 text-sm">
            <NarrativeSection label="宏观链路" items={brief.macro_context} />
            <NarrativeSection label="今日主叙事" items={brief.main_narrative} />
            <NarrativeSection label="偏多方向" items={brief.bullish_sectors} colorCls="text-up" />
            <NarrativeSection label="偏空方向" items={brief.bearish_sectors} colorCls="text-down" />
            <NarrativeSection label="风险提示" items={brief.risk_tips} colorCls="text-yellow-300" />
          </div>
        ) : (
          <div className="text-sm text-dim text-center py-8">暂无叙事数据</div>
        )}
      </div>
    </div>
  );
}

function NarrativeSection({ label, items, colorCls }: { label: string; items: unknown[] | null | undefined; colorCls?: string }) {
  const rendered = renderListItems(items);
  if (rendered.length === 0) return null;

  return (
    <div>
      <div className="text-xs text-dim mb-1">{label}</div>
      <div className={`space-y-0.5 ${colorCls || "text-secondary"}`}>
        {rendered.map((item, i) => (
          <div key={i}>• {item}</div>
        ))}
      </div>
    </div>
  );
}

function CandidatePreviewBlock({ candidates }: { candidates: CandidatePoolEntry[] }) {
  return (
    <div className="bg-card rounded-xl border border-edge">
      <div className="px-5 py-3 border-b border-edge flex items-center justify-between">
        <h3 className="text-sm font-semibold text-muted">候选池预览</h3>
        <Link to="/candidates" className="text-xs text-accent hover:text-accent-hover transition">
          查看全部候选 →
        </Link>
      </div>
      {candidates.length === 0 ? (
        <div className="text-sm text-dim text-center py-8">今日暂无候选标的</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3 p-4">
          {candidates.map((c) => (
            <div key={c.id} className="bg-base border border-edge rounded-lg p-3">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <span className="font-medium text-sm">{c.name}</span>
                  <span className="text-xs text-dim ml-2 font-mono">{c.code}</span>
                </div>
                {c.gate_status && (
                  <span className={`text-xs px-2 py-0.5 rounded-full border ${gateColors[c.gate_status] || "border-edge text-muted"}`}>
                    {c.gate_status}
                  </span>
                )}
              </div>
              {c.theme && (
                <div className="text-xs text-muted mb-1">
                  <span className="px-1.5 py-0.5 rounded bg-badge text-dim">{c.theme}</span>
                </div>
              )}
              {c.thesis && (
                <div className="text-xs text-dim mt-1 line-clamp-2">{c.thesis}</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Dashboard() {
  const { data, isLoading } = useCombatDesk();

  const marketState = data?.market_state ?? null;
  const brief = data?.battle_brief ?? null;
  const preview = data?.candidate_preview ?? [];

  if (isLoading) {
    return <div className="text-dim text-center py-20">加载中...</div>;
  }

  return (
    <div className="space-y-5">
      <h2 className="text-xl font-bold">AI 作战台</h2>

      <ToneBlock brief={brief} marketState={marketState} />
      <DisciplineBlock brief={brief} />
      <MarketNarrativeBlock marketState={marketState} brief={brief} />
      <CandidatePreviewBlock candidates={preview} />
    </div>
  );
}
