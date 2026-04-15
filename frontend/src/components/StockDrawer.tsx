import { useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import MiniKLine from "./charts/MiniKLine";
import RadarChart from "./charts/RadarChart";
import {
  useStockDaily,
  useStockQuote,
  useStockFundamental,
  useRatingHistory,
  useAnalysisHistory,
} from "../hooks/useMarketData";

interface KLinePoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface RatingInfo {
  total_score: number;
  rating: string;
  trend_score: number;
  momentum_score: number;
  volatility_score: number;
  volume_score: number;
  value_score: number;
  sentiment_score: number;
  reason: string;
}

interface AnalysisBrief {
  id: number;
  summary: string;
  signal: string;
  score: number;
  date: string;
}

interface QuoteInfo {
  name: string;
  price: number;
  change_pct: number;
}

interface FundamentalInfo {
  date: string;
  pe_ttm: number | null;
  pb_mrq: number | null;
  roe: number | null;
  eps: number | null;
  market_cap: number | null;
  circulating_cap: number | null;
  debt_ratio: number | null;
  main_net_inflow: number | null;
  retail_net_inflow: number | null;
  large_net_inflow: number | null;
  vol_ratio: number | null;
  turnover_ratio: number | null;
  committee: number | null;
  swing: number | null;
  rise_day_count: number | null;
  chg_5d: number | null;
  chg_10d: number | null;
  chg_20d: number | null;
  chg_60d: number | null;
  chg_year: number | null;
}

interface Props {
  code: string;
  name?: string;
  sector?: string;
  onClose: () => void;
}

function formatMoney(val: number | null): string {
  if (val == null) return "--";
  const abs = Math.abs(val);
  if (abs >= 1e8) return `${(val / 1e8).toFixed(1)}亿`;
  if (abs >= 1e4) return `${(val / 1e4).toFixed(0)}万`;
  return `${val.toFixed(0)}元`;
}

function valColor(val: number | null, thresholds: [number, string][], fallback = "text-secondary"): string {
  if (val == null) return fallback;
  for (const [t, c] of thresholds) {
    if (val < t) return c;
  }
  return fallback;
}

function ScoreItem({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="bg-card-hover rounded-lg px-3 py-2 text-center">
      <div className="text-[10px] text-dim mb-0.5">{label}</div>
      <div className={`text-sm font-mono font-semibold ${color || "text-primary"}`}>{value}</div>
    </div>
  );
}

function ChgBadge({ value, label }: { value: number | null; label: string }) {
  if (value == null) return null;
  const color = value > 0 ? "text-red-400" : value < 0 ? "text-green-400" : "text-muted";
  return (
    <div className="bg-card-hover rounded-lg px-2 py-1.5 text-center min-w-[60px]">
      <span className="text-[10px] text-dim block">{label}</span>
      <span className={`text-xs font-mono font-semibold ${color}`}>
        {value > 0 ? "+" : ""}{value.toFixed(2)}%
      </span>
    </div>
  );
}

function MoneyFlowBar({ label, value, maxRef }: { label: string; value: number; maxRef: number }) {
  const isPositive = value > 0;
  const pct = Math.min((Math.abs(value) / maxRef) * 100, 100);
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-dim">{label}</span>
        <span className={isPositive ? "text-red-400" : "text-green-400"}>
          {isPositive ? "+" : ""}{formatMoney(value)}
        </span>
      </div>
      <div className="h-1.5 bg-input rounded-full overflow-hidden flex">
        {isPositive ? (
          <>
            <div className="h-full flex-1" />
            <div
              className="h-full rounded-full bg-red-400/80"
              style={{ width: `${pct / 2}%`, minWidth: pct > 0 ? 2 : 0 }}
            />
          </>
        ) : (
          <>
            <div
              className="h-full rounded-full bg-green-400/80 ml-auto"
              style={{ width: `${pct / 2}%`, minWidth: pct > 0 ? 2 : 0 }}
            />
            <div className="h-full flex-1" />
          </>
        )}
      </div>
    </div>
  );
}

function SourceBadge({ text }: { text: string }) {
  return (
    <span className="text-[10px] px-1.5 py-0.5 rounded bg-accent/10 text-accent border border-accent/20 font-medium">
      {text}
    </span>
  );
}

function getScoreGradient(score: number): string {
  if (score >= 80) return "from-emerald-600/90 to-emerald-800/80";
  if (score >= 60) return "from-blue-600/90 to-blue-800/80";
  if (score >= 40) return "from-amber-600/90 to-amber-800/80";
  return "from-red-600/90 to-red-800/80";
}

function getRatingBadge(rating: string): string {
  switch (rating) {
    case "强烈推荐": return "bg-red-500/20 text-red-300 border-red-500/30";
    case "推荐": return "bg-orange-500/20 text-orange-300 border-orange-500/30";
    case "中性": return "bg-yellow-500/20 text-yellow-300 border-yellow-500/30";
    case "谨慎": return "bg-blue-500/20 text-blue-300 border-blue-500/30";
    case "回避": return "bg-gray-500/20 text-gray-400 border-gray-500/30";
    default: return "bg-gray-500/20 text-gray-400 border-gray-500/30";
  }
}

export default function StockDrawer({ code, name, sector, onClose }: Props) {
  const navigate = useNavigate();

  const { data: klineData, isLoading: loadingK } = useStockDaily(code, 60);
  const { data: ratingData, isLoading: loadingR } = useRatingHistory(code, 1);
  const { data: analysisData } = useAnalysisHistory(code, 1);
  const { data: quoteData, isLoading: loadingQ } = useStockQuote(code);
  const { data: fundData } = useStockFundamental(code);

  const loading = loadingK || loadingR || loadingQ;

  const kline: KLinePoint[] = klineData?.data || [];
  const rating: RatingInfo | null = ratingData?.length > 0 ? ratingData[0] : null;

  const analysis: AnalysisBrief | null = useMemo(() => {
    if (!analysisData?.length) return null;
    const item = analysisData[0];
    let summary = "";
    let signal = "";
    let score = 0;
    if (item.raw_result) {
      try {
        const parsed = JSON.parse(item.raw_result);
        summary = parsed.summary || "";
        signal = parsed.signal || item.advice || "";
        score = parsed.score || item.score || 0;
      } catch {
        summary = "";
        signal = item.advice || "";
        score = item.score || 0;
      }
    } else {
      signal = item.advice || "";
      score = item.score || 0;
    }
    return { id: item.id, summary, signal, score, date: item.date };
  }, [analysisData]);

  const quote: QuoteInfo | null = quoteData || null;

  const fund: FundamentalInfo | null = useMemo(() => {
    if (!fundData) return null;
    const d = fundData;
    if (d.pe_ttm != null || d.pb_mrq != null || d.main_net_inflow != null) {
      return d as FundamentalInfo;
    }
    return null;
  }, [fundData]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const displayName = quote?.name || name || code;
  const changePct = quote?.change_pct;
  const latestPrice = quote?.price ?? (kline.length > 0 ? kline[kline.length - 1].close : null);

  const signalColor: Record<string, string> = {
    "买入": "text-red-400 bg-red-500/10 border-red-500/30",
    "持有": "text-orange-400 bg-orange-500/10 border-orange-500/30",
    "观望": "text-muted bg-gray-500/10 border-gray-500/30",
    "卖出": "text-green-400 bg-green-500/10 border-green-500/30",
  };

  const hasValuation = fund && (fund.pe_ttm != null || fund.pb_mrq != null || fund.roe != null);
  const hasMoneyFlow = fund && fund.main_net_inflow != null;
  const hasChgData = fund && (fund.chg_5d != null || fund.chg_20d != null || fund.chg_year != null);
  const hasMicroData = fund && (fund.vol_ratio != null || fund.swing != null || fund.committee != null);

  const moneyMax = fund
    ? Math.max(
        Math.abs(fund.main_net_inflow || 0),
        Math.abs(fund.retail_net_inflow || 0),
        Math.abs(fund.large_net_inflow || 0),
        1
      )
    : 1;

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end"
      onClick={onClose}
    >
      <div className="absolute inset-0 bg-overlay backdrop-blur-sm" />

      <div
        className="relative w-[520px] max-w-[90vw] h-full bg-drawer border-l border-edge shadow-2xl overflow-y-auto animate-slide-in-right"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 头部 */}
        <div className="sticky top-0 z-10 bg-drawer/95 backdrop-blur border-b border-edge px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-lg font-bold">{displayName}</div>
              <div className="text-sm text-muted flex items-center gap-2">
                <span className="font-mono">{code}</span>
                {sector && <span className="text-xs px-2 py-0.5 rounded bg-input border border-edge">{sector}</span>}
              </div>
            </div>
            <div className="flex items-center gap-3">
              {latestPrice != null && (
                <div className="text-right">
                  <div className="text-xl font-mono font-bold">{latestPrice.toFixed(2)}</div>
                  {changePct != null && (
                    <div className={`text-sm font-mono font-semibold ${changePct >= 0 ? "text-red-400" : "text-green-400"}`}>
                      {changePct >= 0 ? "+" : ""}{changePct.toFixed(2)}%
                    </div>
                  )}
                </div>
              )}
              <button
                onClick={onClose}
                className="w-8 h-8 flex items-center justify-center rounded-lg bg-input hover:bg-card-hover text-muted hover:text-primary transition"
              >
                &times;
              </button>
            </div>
          </div>
        </div>

        {loading ? (
          <div className="text-dim text-center py-20">加载中...</div>
        ) : (
          <div className="p-5 space-y-3">

            {/* ═══ 总评分卡片 ═══ */}
            {rating && (
              <div className={`rounded-xl p-4 bg-gradient-to-br ${getScoreGradient(rating.total_score)} text-white`}>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-3xl font-bold font-mono">{rating.total_score?.toFixed(1)}</div>
                    <div className="text-xs opacity-75 mt-1">综合评分</div>
                  </div>
                  <span className={`px-3 py-1 text-sm rounded-full border font-medium ${getRatingBadge(rating.rating)}`}>
                    {rating.rating}
                  </span>
                </div>
                <div className="mt-3 text-xs opacity-70 leading-relaxed">
                  趋势 {(rating.trend_score || 0).toFixed(0)}×25% +
                  动量 {(rating.momentum_score || 0).toFixed(0)}×20% +
                  波动 {(rating.volatility_score || 0).toFixed(0)}×15% +
                  成交 {(rating.volume_score || 0).toFixed(0)}×20% +
                  价值 {(rating.value_score || 0).toFixed(0)}×20%
                </div>
              </div>
            )}

            {/* ═══ 走势图 ═══ */}
            <div className="bg-card rounded-xl p-4 border border-edge">
              <h3 className="text-sm font-semibold text-muted mb-2">近60日走势</h3>
              {kline.length > 0 ? (
                <MiniKLine data={kline} height={180} />
              ) : (
                <div className="text-dim text-center py-8 text-xs">暂无K线数据</div>
              )}
            </div>

            {/* ═══ 核心估值 ═══ */}
            {hasValuation && (
              <div className="bg-card rounded-xl p-4 border border-edge">
                <div className="flex items-center gap-2 mb-3">
                  <h3 className="text-sm font-semibold text-muted">核心估值</h3>
                  <SourceBadge text="东财" />
                </div>
                <div className="grid grid-cols-3 gap-2">
                  {fund.pe_ttm != null && (
                    <ScoreItem
                      label="PE(TTM)"
                      value={fund.pe_ttm.toFixed(2)}
                      color={valColor(fund.pe_ttm, [[0, "text-red-400"], [30, "text-green-400"], [50, "text-orange-400"]])}
                    />
                  )}
                  {fund.pb_mrq != null && (
                    <ScoreItem
                      label="PB(MRQ)"
                      value={`${fund.pb_mrq.toFixed(3)}${fund.pb_mrq < 1 && fund.pb_mrq > 0 ? " 破净" : ""}`}
                      color={fund.pb_mrq < 1 ? "text-blue-400" : undefined}
                    />
                  )}
                  {fund.market_cap != null && (
                    <ScoreItem label="总市值" value={formatMoney(fund.market_cap)} />
                  )}
                  {fund.roe != null && (
                    <ScoreItem
                      label="ROE"
                      value={`${fund.roe.toFixed(2)}%`}
                      color={valColor(fund.roe, [[0, "text-red-400"], [8, "text-secondary"]], "text-green-400")}
                    />
                  )}
                  {fund.eps != null && (
                    <ScoreItem label="EPS" value={fund.eps.toFixed(3)} />
                  )}
                  {fund.debt_ratio != null && (
                    <ScoreItem
                      label="资产负债率"
                      value={`${fund.debt_ratio.toFixed(1)}%`}
                      color={valColor(fund.debt_ratio, [[70, "text-green-400"], [80, "text-orange-400"]], "text-red-400")}
                    />
                  )}
                </div>
              </div>
            )}

            {/* ═══ 多周期涨跌幅 ═══ */}
            {hasChgData && (
              <div className="bg-card rounded-xl p-4 border border-edge">
                <div className="flex items-center gap-2 mb-3">
                  <h3 className="text-sm font-semibold text-muted">多周期涨跌幅</h3>
                  {fund.rise_day_count != null && fund.rise_day_count !== 0 && (
                    <span className={`text-xs px-1.5 py-0.5 rounded font-mono ${
                      fund.rise_day_count > 0 ? "bg-red-500/10 text-red-400" : "bg-green-500/10 text-green-400"
                    }`}>
                      {fund.rise_day_count > 0 ? "连涨" : "连跌"}{Math.abs(fund.rise_day_count)}天
                    </span>
                  )}
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <ChgBadge value={fund.chg_5d} label="5日" />
                  <ChgBadge value={fund.chg_10d} label="10日" />
                  <ChgBadge value={fund.chg_20d} label="20日" />
                  <ChgBadge value={fund.chg_60d} label="60日" />
                  <ChgBadge value={fund.chg_year} label="年初至今" />
                </div>
              </div>
            )}

            {/* ═══ 资金流向 ═══ */}
            {hasMoneyFlow && (
              <div className="bg-card rounded-xl p-4 border border-edge">
                <div className="flex items-center gap-2 mb-3">
                  <h3 className="text-sm font-semibold text-muted">资金流向</h3>
                  <SourceBadge text="东财" />
                </div>
                <div className="space-y-2.5">
                  <MoneyFlowBar label="主力净流入" value={fund.main_net_inflow!} maxRef={moneyMax} />
                  {fund.large_net_inflow != null && (
                    <MoneyFlowBar label="超大单净流入" value={fund.large_net_inflow} maxRef={moneyMax} />
                  )}
                  {fund.retail_net_inflow != null && (
                    <MoneyFlowBar label="散户净流入" value={fund.retail_net_inflow} maxRef={moneyMax} />
                  )}
                </div>
              </div>
            )}

            {/* ═══ 市场微观 ═══ */}
            {hasMicroData && (
              <div className="bg-card rounded-xl p-4 border border-edge">
                <h3 className="text-sm font-semibold text-muted mb-3">市场微观</h3>
                <div className="grid grid-cols-3 gap-2">
                  {fund.vol_ratio != null && (
                    <ScoreItem
                      label="量比"
                      value={fund.vol_ratio.toFixed(2)}
                      color={valColor(fund.vol_ratio, [[1, "text-secondary"], [2, "text-orange-400"]], "text-red-400")}
                    />
                  )}
                  {fund.turnover_ratio != null && (
                    <ScoreItem label="换手率" value={`${fund.turnover_ratio.toFixed(2)}%`} />
                  )}
                  {fund.committee != null && (
                    <ScoreItem
                      label="委比"
                      value={`${fund.committee > 0 ? "+" : ""}${fund.committee.toFixed(2)}%`}
                      color={fund.committee > 0 ? "text-red-400" : "text-green-400"}
                    />
                  )}
                  {fund.swing != null && (
                    <ScoreItem label="振幅" value={`${fund.swing.toFixed(2)}%`} />
                  )}
                  {fund.circulating_cap != null && (
                    <ScoreItem label="流通市值" value={formatMoney(fund.circulating_cap)} />
                  )}
                </div>
              </div>
            )}

            {/* ═══ 维度评分（雷达图） ═══ */}
            {rating && (
              <div className="bg-card rounded-xl p-4 border border-edge">
                <h3 className="text-sm font-semibold text-muted mb-2">维度评分</h3>
                <div className="flex justify-center">
                  <RadarChart
                    data={[
                      { label: "趋势", value: rating.trend_score || 0 },
                      { label: "动量", value: rating.momentum_score || 0 },
                      { label: "波动", value: rating.volatility_score || 0 },
                      { label: "成交量", value: rating.volume_score || 0 },
                      { label: "价值", value: rating.value_score || 0 },
                      { label: "情绪", value: rating.sentiment_score || 0 },
                    ]}
                    size={200}
                  />
                </div>
                {rating.reason && (
                  <p className="mt-2 text-xs text-muted leading-relaxed line-clamp-3">{rating.reason}</p>
                )}
              </div>
            )}

            {/* ═══ AI 分析 ═══ */}
            {analysis && (
              <div className="bg-card rounded-xl p-4 border border-edge">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-semibold text-muted">AI 分析</h3>
                  {analysis.signal && (
                    <span className={`px-2.5 py-0.5 text-xs rounded-full border font-medium ${signalColor[analysis.signal] || "text-muted border-edge"}`}>
                      {analysis.signal} {analysis.score > 0 && `· ${analysis.score}分`}
                    </span>
                  )}
                </div>
                {analysis.summary && (
                  <p className="text-sm text-secondary leading-relaxed">{analysis.summary}</p>
                )}
                <div className="text-xs text-dim mt-2">分析日期: {analysis.date}</div>
              </div>
            )}

            {!rating && !analysis && kline.length === 0 && !fund && (
              <div className="text-dim text-center py-8 text-sm">
                暂无该股票的评级与分析数据
              </div>
            )}

            {/* 底部操作 */}
            <button
              onClick={() => { onClose(); navigate(`/stock/${code}`); }}
              className="w-full py-2.5 text-sm bg-accent hover:bg-accent-hover text-white rounded-lg transition text-center font-medium"
            >
              查看完整分析
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
