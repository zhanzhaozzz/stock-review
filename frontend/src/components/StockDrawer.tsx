import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";
import MiniKLine from "./charts/MiniKLine";
import RadarChart from "./charts/RadarChart";

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

function valColor(val: number | null, thresholds: [number, string][], fallback = "text-gray-300"): string {
  if (val == null) return fallback;
  for (const [t, c] of thresholds) {
    if (val < t) return c;
  }
  return fallback;
}

function ChgBadge({ value, label }: { value: number | null; label: string }) {
  if (value == null) return null;
  const color = value > 0 ? "text-red-400" : value < 0 ? "text-green-400" : "text-gray-400";
  return (
    <div className="flex flex-col items-center bg-gray-800/60 rounded-lg px-2.5 py-1.5">
      <span className="text-[10px] text-gray-500">{label}</span>
      <span className={`text-xs font-mono font-medium ${color}`}>
        {value > 0 ? "+" : ""}{value.toFixed(2)}%
      </span>
    </div>
  );
}

export default function StockDrawer({ code, name, sector, onClose }: Props) {
  const navigate = useNavigate();
  const [kline, setKline] = useState<KLinePoint[]>([]);
  const [rating, setRating] = useState<RatingInfo | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisBrief | null>(null);
  const [quote, setQuote] = useState<QuoteInfo | null>(null);
  const [fund, setFund] = useState<FundamentalInfo | null>(null);
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    if (!code) return;
    setLoading(true);
    try {
      const [kRes, rRes, aRes, qRes, fRes] = await Promise.allSettled([
        api.get(`/market/stock/${code}/daily?days=60`),
        api.get(`/ratings/history/${code}?limit=1`),
        api.get(`/analysis/history?code=${code}&limit=1`),
        api.get(`/market/quote/${code}`),
        api.get(`/market/fundamental/${code}`),
      ]);

      if (kRes.status === "fulfilled") {
        setKline((kRes.value.data?.data || []) as KLinePoint[]);
      }
      if (rRes.status === "fulfilled" && rRes.value.data?.length > 0) {
        setRating(rRes.value.data[0]);
      }
      if (aRes.status === "fulfilled" && aRes.value.data?.length > 0) {
        const item = aRes.value.data[0];
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
        setAnalysis({ id: item.id, summary, signal, score, date: item.date });
      }
      if (qRes.status === "fulfilled" && qRes.value.data && !qRes.value.data.error) {
        setQuote(qRes.value.data);
      }
      if (fRes.status === "fulfilled" && fRes.value.data) {
        const d = fRes.value.data;
        if (d.pe_ttm != null || d.pb_mrq != null || d.main_net_inflow != null) {
          setFund(d as FundamentalInfo);
        }
      }
    } finally {
      setLoading(false);
    }
  }, [code]);

  useEffect(() => {
    loadData();
  }, [loadData]);

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
    "观望": "text-gray-400 bg-gray-500/10 border-gray-500/30",
    "卖出": "text-green-400 bg-green-500/10 border-green-500/30",
  };

  const hasValuation = fund && (fund.pe_ttm != null || fund.pb_mrq != null || fund.roe != null);
  const hasMoneyFlow = fund && fund.main_net_inflow != null;
  const hasChgData = fund && (fund.chg_5d != null || fund.chg_20d != null || fund.chg_year != null);
  const hasMicroData = fund && (fund.vol_ratio != null || fund.swing != null || fund.committee != null);

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end"
      onClick={onClose}
    >
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />

      <div
        className="relative w-[480px] max-w-[90vw] h-full bg-gray-950 border-l border-gray-800 shadow-2xl overflow-y-auto animate-slide-in-right"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 头部 */}
        <div className="sticky top-0 z-10 bg-gray-950/95 backdrop-blur border-b border-gray-800 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-lg font-bold">{displayName}</div>
              <div className="text-sm text-gray-400 flex items-center gap-2">
                <span className="font-mono">{code}</span>
                {sector && <span className="text-xs px-2 py-0.5 rounded bg-gray-800 border border-gray-700">{sector}</span>}
              </div>
            </div>
            <div className="flex items-center gap-3">
              {latestPrice != null && (
                <div className="text-right">
                  <div className="text-lg font-mono font-bold">{latestPrice.toFixed(2)}</div>
                  {changePct != null && (
                    <div className={`text-sm font-mono ${changePct >= 0 ? "text-red-400" : "text-green-400"}`}>
                      {changePct >= 0 ? "+" : ""}{changePct.toFixed(2)}%
                    </div>
                  )}
                </div>
              )}
              <button
                onClick={onClose}
                className="w-8 h-8 flex items-center justify-center rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-white transition"
              >
                &times;
              </button>
            </div>
          </div>
        </div>

        {loading ? (
          <div className="text-gray-500 text-center py-20">加载中...</div>
        ) : (
          <div className="p-6 space-y-4">
            {/* 走势图 */}
            <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
              <h3 className="text-sm font-semibold text-gray-400 mb-3">近60日走势</h3>
              <MiniKLine data={kline} height={200} />
            </div>

            {/* 核心估值 */}
            {hasValuation && (
              <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
                <h3 className="text-sm font-semibold text-gray-400 mb-3">核心估值</h3>
                <div className="grid grid-cols-3 gap-3">
                  {fund.pe_ttm != null && (
                    <div className="text-center">
                      <div className="text-[10px] text-gray-500">PE(TTM)</div>
                      <div className={`text-sm font-mono font-medium ${valColor(fund.pe_ttm, [[0, "text-red-400"], [30, "text-green-400"], [50, "text-orange-400"]])}`}>
                        {fund.pe_ttm.toFixed(2)}
                      </div>
                    </div>
                  )}
                  {fund.pb_mrq != null && (
                    <div className="text-center">
                      <div className="text-[10px] text-gray-500">PB(MRQ)</div>
                      <div className={`text-sm font-mono font-medium ${fund.pb_mrq < 1 ? "text-blue-400" : "text-gray-300"}`}>
                        {fund.pb_mrq.toFixed(3)}
                        {fund.pb_mrq < 1 && fund.pb_mrq > 0 && <span className="text-[10px] ml-0.5">破净</span>}
                      </div>
                    </div>
                  )}
                  {fund.market_cap != null && (
                    <div className="text-center">
                      <div className="text-[10px] text-gray-500">总市值</div>
                      <div className="text-sm font-mono font-medium text-gray-300">{formatMoney(fund.market_cap)}</div>
                    </div>
                  )}
                  {fund.roe != null && (
                    <div className="text-center">
                      <div className="text-[10px] text-gray-500">ROE</div>
                      <div className={`text-sm font-mono font-medium ${valColor(fund.roe, [[0, "text-red-400"], [8, "text-gray-300"]], "text-green-400")}`}>
                        {fund.roe.toFixed(2)}%
                      </div>
                    </div>
                  )}
                  {fund.eps != null && (
                    <div className="text-center">
                      <div className="text-[10px] text-gray-500">EPS</div>
                      <div className="text-sm font-mono font-medium text-gray-300">{fund.eps.toFixed(3)}</div>
                    </div>
                  )}
                  {fund.debt_ratio != null && (
                    <div className="text-center">
                      <div className="text-[10px] text-gray-500">资产负债率</div>
                      <div className={`text-sm font-mono font-medium ${valColor(fund.debt_ratio, [[70, "text-green-400"], [80, "text-orange-400"]], "text-red-400")}`}>
                        {fund.debt_ratio.toFixed(1)}%
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* 多周期涨跌幅 */}
            {hasChgData && (
              <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
                <h3 className="text-sm font-semibold text-gray-400 mb-3">多周期涨跌幅</h3>
                <div className="flex flex-wrap gap-2">
                  <ChgBadge value={fund.chg_5d} label="5日" />
                  <ChgBadge value={fund.chg_10d} label="10日" />
                  <ChgBadge value={fund.chg_20d} label="20日" />
                  <ChgBadge value={fund.chg_60d} label="60日" />
                  <ChgBadge value={fund.chg_year} label="年初至今" />
                </div>
              </div>
            )}

            {/* 资金流向 */}
            {hasMoneyFlow && (
              <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
                <h3 className="text-sm font-semibold text-gray-400 mb-3">资金流向</h3>
                <div className="space-y-3">
                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-gray-500">主力净流入</span>
                      <span className={fund.main_net_inflow! > 0 ? "text-red-400" : "text-green-400"}>
                        {fund.main_net_inflow! > 0 ? "+" : ""}{formatMoney(fund.main_net_inflow)}
                      </span>
                    </div>
                    <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all"
                        style={{
                          width: `${Math.min(Math.abs(fund.main_net_inflow || 0) / 5e8 * 100, 100)}%`,
                          backgroundColor: (fund.main_net_inflow || 0) > 0 ? "rgb(248 113 113)" : "rgb(74 222 128)",
                        }}
                      />
                    </div>
                  </div>
                  {fund.retail_net_inflow != null && (
                    <div className="flex justify-between text-xs">
                      <span className="text-gray-500">散户净流入</span>
                      <span className={fund.retail_net_inflow > 0 ? "text-red-400" : "text-green-400"}>
                        {fund.retail_net_inflow > 0 ? "+" : ""}{formatMoney(fund.retail_net_inflow)}
                      </span>
                    </div>
                  )}
                  {fund.large_net_inflow != null && (
                    <div className="flex justify-between text-xs">
                      <span className="text-gray-500">超大单净流入</span>
                      <span className={fund.large_net_inflow > 0 ? "text-red-400" : "text-green-400"}>
                        {fund.large_net_inflow > 0 ? "+" : ""}{formatMoney(fund.large_net_inflow)}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* 市场微观 */}
            {hasMicroData && (
              <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
                <h3 className="text-sm font-semibold text-gray-400 mb-3">市场微观</h3>
                <div className="grid grid-cols-3 gap-3">
                  {fund.vol_ratio != null && (
                    <div className="text-center">
                      <div className="text-[10px] text-gray-500">量比</div>
                      <div className={`text-sm font-mono font-medium ${valColor(fund.vol_ratio, [[1, "text-gray-300"], [2, "text-orange-400"]], "text-red-400")}`}>
                        {fund.vol_ratio.toFixed(2)}
                      </div>
                    </div>
                  )}
                  {fund.turnover_ratio != null && (
                    <div className="text-center">
                      <div className="text-[10px] text-gray-500">换手率</div>
                      <div className="text-sm font-mono font-medium text-gray-300">{fund.turnover_ratio.toFixed(2)}%</div>
                    </div>
                  )}
                  {fund.committee != null && (
                    <div className="text-center">
                      <div className="text-[10px] text-gray-500">委比</div>
                      <div className={`text-sm font-mono font-medium ${fund.committee > 0 ? "text-red-400" : "text-green-400"}`}>
                        {fund.committee > 0 ? "+" : ""}{fund.committee.toFixed(2)}%
                      </div>
                    </div>
                  )}
                  {fund.swing != null && (
                    <div className="text-center">
                      <div className="text-[10px] text-gray-500">振幅</div>
                      <div className="text-sm font-mono font-medium text-gray-300">{fund.swing.toFixed(2)}%</div>
                    </div>
                  )}
                  {fund.rise_day_count != null && fund.rise_day_count !== 0 && (
                    <div className="text-center">
                      <div className="text-[10px] text-gray-500">{fund.rise_day_count > 0 ? "连涨" : "连跌"}</div>
                      <div className={`text-sm font-mono font-medium ${fund.rise_day_count > 0 ? "text-red-400" : "text-green-400"}`}>
                        {Math.abs(fund.rise_day_count)}天
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* 量化评级 */}
            {rating && (
              <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
                <h3 className="text-sm font-semibold text-gray-400 mb-3">量化评级</h3>
                <div className="flex items-center gap-4 mb-3">
                  <div className="text-2xl font-bold">{rating.total_score?.toFixed(0)}</div>
                  <div className="text-sm font-medium">{rating.rating}</div>
                </div>
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
                {rating.reason && (
                  <p className="mt-2 text-xs text-gray-400 line-clamp-3">{rating.reason}</p>
                )}
              </div>
            )}

            {/* AI 分析摘要 */}
            {analysis && (
              <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-semibold text-gray-400">AI 分析</h3>
                  {analysis.signal && (
                    <span className={`px-2 py-0.5 text-xs rounded-full border ${signalColor[analysis.signal] || "text-gray-400 border-gray-700"}`}>
                      {analysis.signal} {analysis.score > 0 && `· ${analysis.score}分`}
                    </span>
                  )}
                </div>
                {analysis.summary && (
                  <p className="text-sm text-gray-300">{analysis.summary}</p>
                )}
                <div className="text-xs text-gray-600 mt-2">分析日期: {analysis.date}</div>
              </div>
            )}

            {!rating && !analysis && kline.length === 0 && !fund && (
              <div className="text-gray-500 text-center py-8 text-sm">
                暂无该股票的评级与分析数据
              </div>
            )}

            <button
              onClick={() => { onClose(); navigate(`/stock/${code}`); }}
              className="w-full py-2.5 text-sm bg-blue-600 hover:bg-blue-500 rounded-lg transition text-center"
            >
              查看完整分析
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
