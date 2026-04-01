import { useEffect, useState, useCallback } from "react";
import { useParams } from "react-router-dom";
import api from "../api/client";
import RadarChart from "../components/charts/RadarChart";
import MiniKLine from "../components/charts/MiniKLine";

interface AnalysisResult {
  code: string;
  name: string;
  market: string;
  date: string;
  summary: string;
  signal: string;
  score: number;
  target_price: number | null;
  stop_loss: number | null;
  technical_view: string;
  fundamental_view: string;
  news_impact: string;
  key_points: string[];
  risk_warnings: string[];
  sentiment_context: {
    current_cycle: string;
    applicable_strategy: string;
    strategy_reason: string;
  } | null;
  position_advice: {
    suggested_size: string;
    entry_type: string;
    stop_condition: string;
  } | null;
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

interface KLinePoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
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

function ChgBadge({ value, label }: { value: number | null; label: string }) {
  if (value == null) return null;
  const color = value > 0 ? "text-red-400" : value < 0 ? "text-green-400" : "text-muted";
  return (
    <div className="flex flex-col items-center bg-card-hover rounded-lg px-3 py-2">
      <span className="text-[10px] text-dim">{label}</span>
      <span className={`text-sm font-mono font-medium ${color}`}>
        {value > 0 ? "+" : ""}{value.toFixed(2)}%
      </span>
    </div>
  );
}

function MetricCard({ label, value, unit, colorClass }: { label: string; value: string; unit?: string; colorClass?: string }) {
  return (
    <div className="bg-card-hover rounded-lg p-3 text-center">
      <div className="text-[11px] text-dim mb-1">{label}</div>
      <div className={`text-base font-mono font-semibold ${colorClass || "text-primary"}`}>
        {value}{unit && <span className="text-xs font-normal text-dim ml-0.5">{unit}</span>}
      </div>
    </div>
  );
}

export default function StockDetail() {
  const { code } = useParams<{ code: string }>();
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [rating, setRating] = useState<RatingInfo | null>(null);
  const [kline, setKline] = useState<KLinePoint[]>([]);
  const [fund, setFund] = useState<FundamentalInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);

  const loadData = useCallback(async () => {
    if (!code) return;
    setLoading(true);
    try {
      const [analysisRes, ratingRes, kRes, fRes] = await Promise.allSettled([
        api.get(`/analysis/history?code=${code}&limit=1`),
        api.get(`/ratings/history/${code}?limit=1`),
        api.get(`/market/stock/${code}/daily?days=90`),
        api.get(`/market/fundamental/${code}`),
      ]);
      if (analysisRes.status === "fulfilled" && analysisRes.value.data?.length > 0) {
        const latest = analysisRes.value.data[0];
        if (latest.id) {
          const detailRes = await api.get(`/analysis/${latest.id}`);
          const d = detailRes.data;
          setAnalysis({
            code: d.code,
            name: d.name,
            market: d.market,
            date: d.date,
            summary: d.raw_result ? JSON.parse(d.raw_result)?.summary || "" : "",
            signal: d.advice || "",
            score: d.score || 0,
            target_price: d.target_price,
            stop_loss: d.stop_loss,
            technical_view: d.raw_result ? JSON.parse(d.raw_result)?.technical_view || "" : "",
            fundamental_view: d.raw_result ? JSON.parse(d.raw_result)?.fundamental_view || "" : "",
            news_impact: d.raw_result ? JSON.parse(d.raw_result)?.news_impact || "" : "",
            key_points: d.key_levels?.key_points || [],
            risk_warnings: d.raw_result ? JSON.parse(d.raw_result)?.risk_warnings || [] : [],
            sentiment_context: d.sentiment_context,
            position_advice: d.position_advice,
          });
        }
      }
      if (ratingRes.status === "fulfilled" && ratingRes.value.data?.length > 0) {
        setRating(ratingRes.value.data[0]);
      }
      if (kRes.status === "fulfilled") {
        setKline((kRes.value.data?.data || []) as KLinePoint[]);
      }
      if (fRes.status === "fulfilled" && fRes.value.data) {
        const d = fRes.value.data;
        if (d.pe_ttm != null || d.pb_mrq != null || d.main_net_inflow != null) {
          setFund(d as FundamentalInfo);
        }
      }
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  }, [code]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  async function handleAnalyze() {
    if (!code) return;
    setAnalyzing(true);
    try {
      const res = await api.post("/analysis/analyze", { codes: [code] });
      if (res.data.results?.length > 0) {
        setAnalysis(res.data.results[0]);
      }
    } catch {
      /* ignore */
    } finally {
      setAnalyzing(false);
    }
  }

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
  const hasFundData = hasValuation || hasMoneyFlow || hasChgData || hasMicroData;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">{code} 个股分析</h2>
        <button
          onClick={handleAnalyze}
          disabled={analyzing}
          className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg transition"
        >
          {analyzing ? "分析中..." : "运行 AI 分析"}
        </button>
      </div>

      {loading ? (
        <div className="text-dim text-center py-20">加载中...</div>
      ) : !analysis && !rating && !hasFundData ? (
        <div className="text-dim text-center py-20">
          <p>暂无分析数据</p>
          <p className="text-xs mt-2 text-dim">点击"运行 AI 分析"获取深度分析报告</p>
        </div>
      ) : (
        <>
          {/* K线 + 雷达 */}
          {rating && (
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-card rounded-xl p-5 border border-edge">
                <h3 className="text-sm font-semibold text-muted mb-3">近90日收盘走势</h3>
                <MiniKLine data={kline} height={260} />
              </div>
              <div className="bg-card rounded-xl p-5 border border-edge">
                <h3 className="text-sm font-semibold text-muted mb-3">六维评分雷达图</h3>
                <RadarChart
                  data={[
                    { label: "趋势", value: rating.trend_score || 0 },
                    { label: "动量", value: rating.momentum_score || 0 },
                    { label: "波动", value: rating.volatility_score || 0 },
                    { label: "成交量", value: rating.volume_score || 0 },
                    { label: "价值", value: rating.value_score || 0 },
                    { label: "情绪", value: rating.sentiment_score || 0 },
                  ]}
                  size={260}
                />
              </div>
            </div>
          )}

          {/* 基本面数据区块 */}
          {hasFundData && (
            <div className="grid grid-cols-2 gap-4">
              {/* 核心估值 */}
              {hasValuation && (
                <div className="bg-card rounded-xl p-5 border border-edge">
                  <h3 className="text-sm font-semibold text-muted mb-4">核心估值</h3>
                  <div className="grid grid-cols-3 gap-3">
                    {fund.pe_ttm != null && (
                      <MetricCard
                        label="PE(TTM)"
                        value={fund.pe_ttm.toFixed(2)}
                        colorClass={valColor(fund.pe_ttm, [[0, "text-red-400"], [30, "text-green-400"], [50, "text-orange-400"]])}
                      />
                    )}
                    {fund.pb_mrq != null && (
                      <MetricCard
                        label="PB(MRQ)"
                        value={`${fund.pb_mrq.toFixed(3)}${fund.pb_mrq < 1 && fund.pb_mrq > 0 ? " 破净" : ""}`}
                        colorClass={fund.pb_mrq < 1 ? "text-blue-400" : "text-primary"}
                      />
                    )}
                    {fund.market_cap != null && (
                      <MetricCard label="总市值" value={formatMoney(fund.market_cap)} />
                    )}
                    {fund.roe != null && (
                      <MetricCard
                        label="ROE"
                        value={fund.roe.toFixed(2)}
                        unit="%"
                        colorClass={valColor(fund.roe, [[0, "text-red-400"], [8, "text-primary"]], "text-green-400")}
                      />
                    )}
                    {fund.eps != null && (
                      <MetricCard label="EPS" value={fund.eps.toFixed(3)} />
                    )}
                    {fund.debt_ratio != null && (
                      <MetricCard
                        label="资产负债率"
                        value={fund.debt_ratio.toFixed(1)}
                        unit="%"
                        colorClass={valColor(fund.debt_ratio, [[70, "text-green-400"], [80, "text-orange-400"]], "text-red-400")}
                      />
                    )}
                  </div>
                </div>
              )}

              {/* 资金流向 */}
              {hasMoneyFlow && (
                <div className="bg-card rounded-xl p-5 border border-edge">
                  <h3 className="text-sm font-semibold text-muted mb-4">资金流向</h3>
                  <div className="space-y-4">
                    <div>
                      <div className="flex justify-between text-sm mb-1.5">
                        <span className="text-muted">主力净流入</span>
                        <span className={`font-mono font-medium ${(fund.main_net_inflow || 0) > 0 ? "text-red-400" : "text-green-400"}`}>
                          {(fund.main_net_inflow || 0) > 0 ? "+" : ""}{formatMoney(fund.main_net_inflow)}
                        </span>
                      </div>
                      <div className="h-2 bg-input rounded-full overflow-hidden">
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
                      <div className="flex justify-between text-sm">
                        <span className="text-muted">散户净流入</span>
                        <span className={`font-mono font-medium ${fund.retail_net_inflow > 0 ? "text-red-400" : "text-green-400"}`}>
                          {fund.retail_net_inflow > 0 ? "+" : ""}{formatMoney(fund.retail_net_inflow)}
                        </span>
                      </div>
                    )}
                    {fund.large_net_inflow != null && (
                      <div className="flex justify-between text-sm">
                        <span className="text-muted">超大单净流入</span>
                        <span className={`font-mono font-medium ${fund.large_net_inflow > 0 ? "text-red-400" : "text-green-400"}`}>
                          {fund.large_net_inflow > 0 ? "+" : ""}{formatMoney(fund.large_net_inflow)}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* 多周期涨跌幅 */}
              {hasChgData && (
                <div className="bg-card rounded-xl p-5 border border-edge">
                  <h3 className="text-sm font-semibold text-muted mb-4">多周期涨跌幅</h3>
                  <div className="flex flex-wrap gap-2.5">
                    <ChgBadge value={fund.chg_5d} label="5日" />
                    <ChgBadge value={fund.chg_10d} label="10日" />
                    <ChgBadge value={fund.chg_20d} label="20日" />
                    <ChgBadge value={fund.chg_60d} label="60日" />
                    <ChgBadge value={fund.chg_year} label="年初至今" />
                  </div>
                </div>
              )}

              {/* 市场微观 */}
              {hasMicroData && (
                <div className="bg-card rounded-xl p-5 border border-edge">
                  <h3 className="text-sm font-semibold text-muted mb-4">市场微观数据</h3>
                  <div className="grid grid-cols-3 gap-3">
                    {fund.vol_ratio != null && (
                      <MetricCard
                        label="量比"
                        value={fund.vol_ratio.toFixed(2)}
                        colorClass={valColor(fund.vol_ratio, [[1, "text-primary"], [2, "text-orange-400"]], "text-red-400")}
                      />
                    )}
                    {fund.turnover_ratio != null && (
                      <MetricCard label="换手率" value={fund.turnover_ratio.toFixed(2)} unit="%" />
                    )}
                    {fund.committee != null && (
                      <MetricCard
                        label="委比"
                        value={`${fund.committee > 0 ? "+" : ""}${fund.committee.toFixed(2)}`}
                        unit="%"
                        colorClass={fund.committee > 0 ? "text-red-400" : "text-green-400"}
                      />
                    )}
                    {fund.swing != null && (
                      <MetricCard label="振幅" value={fund.swing.toFixed(2)} unit="%" />
                    )}
                    {fund.rise_day_count != null && fund.rise_day_count !== 0 && (
                      <MetricCard
                        label={fund.rise_day_count > 0 ? "连涨" : "连跌"}
                        value={`${Math.abs(fund.rise_day_count)}`}
                        unit="天"
                        colorClass={fund.rise_day_count > 0 ? "text-red-400" : "text-green-400"}
                      />
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* 评级概览 */}
          {rating && (
            <div className="bg-card rounded-xl p-5 border border-edge">
              <h3 className="text-sm font-semibold text-muted mb-3">量化评级</h3>
              <div className="flex items-center gap-6">
                <div className="text-3xl font-bold">{rating.total_score?.toFixed(0)}</div>
                <div className="text-lg font-medium">{rating.rating}</div>
                <div className="flex-1 grid grid-cols-6 gap-2 text-xs text-center">
                  {[
                    { label: "趋势", v: rating.trend_score },
                    { label: "动量", v: rating.momentum_score },
                    { label: "波动", v: rating.volatility_score },
                    { label: "成交量", v: rating.volume_score },
                    { label: "价值", v: rating.value_score },
                    { label: "情绪", v: rating.sentiment_score },
                  ].map((d) => (
                    <div key={d.label}>
                      <div className="text-dim">{d.label}</div>
                      <div className="text-sm font-mono">{d.v?.toFixed(0) || "--"}</div>
                    </div>
                  ))}
                </div>
              </div>
              {rating.reason && (
                <p className="mt-3 text-sm text-muted">{rating.reason}</p>
              )}
            </div>
          )}

          {/* AI 分析报告 */}
          {analysis && (
            <>
              <div className="bg-card rounded-xl p-5 border border-edge">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold text-muted">AI 分析报告</h3>
                  <span className={`px-3 py-1 text-sm rounded-full border ${signalColor[analysis.signal] || "text-muted"}`}>
                    {analysis.signal} · {analysis.score?.toFixed(0)}分
                  </span>
                </div>
                <p className="text-sm">{analysis.summary}</p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                {analysis.target_price != null && (
                  <div className="bg-card rounded-xl p-4 border border-edge">
                    <div className="text-xs text-dim mb-1">目标价</div>
                    <div className="text-xl font-bold text-up">{analysis.target_price.toFixed(2)}</div>
                  </div>
                )}
                {analysis.stop_loss != null && (
                  <div className="bg-card rounded-xl p-4 border border-edge">
                    <div className="text-xs text-dim mb-1">止损价</div>
                    <div className="text-xl font-bold text-down">{analysis.stop_loss.toFixed(2)}</div>
                  </div>
                )}
              </div>

              {/* 技术面 / 基本面 / 新闻 */}
              <div className="grid grid-cols-3 gap-4">
                {[
                  { title: "技术面", content: analysis.technical_view },
                  { title: "基本面", content: analysis.fundamental_view },
                  { title: "新闻影响", content: analysis.news_impact },
                ].map((sec) => (
                  <div key={sec.title} className="bg-card rounded-xl p-4 border border-edge">
                    <h4 className="text-xs font-semibold text-dim mb-2">{sec.title}</h4>
                    <p className="text-sm text-secondary whitespace-pre-line">{sec.content || "暂无"}</p>
                  </div>
                ))}
              </div>

              {/* 要点 & 风险 */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-card rounded-xl p-4 border border-edge">
                  <h4 className="text-xs font-semibold text-dim mb-2">关键要点</h4>
                  <ul className="space-y-1">
                    {(analysis.key_points || []).map((p, i) => (
                      <li key={i} className="text-sm text-secondary">• {p}</li>
                    ))}
                  </ul>
                </div>
                <div className="bg-card rounded-xl p-4 border border-edge">
                  <h4 className="text-xs font-semibold text-dim mb-2">风险提示</h4>
                  <ul className="space-y-1">
                    {(analysis.risk_warnings || []).map((w, i) => (
                      <li key={i} className="text-sm text-yellow-400/80">⚠ {w}</li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* 情绪 & 仓位建议 */}
              {(analysis.sentiment_context || analysis.position_advice) && (
                <div className="grid grid-cols-2 gap-4">
                  {analysis.sentiment_context && (
                    <div className="bg-card rounded-xl p-4 border border-edge">
                      <h4 className="text-xs font-semibold text-dim mb-2">情绪周期</h4>
                      <div className="text-sm space-y-1">
                        <div>当前周期: <span className="font-medium">{analysis.sentiment_context.current_cycle}</span></div>
                        <div>建议策略: {analysis.sentiment_context.applicable_strategy}</div>
                        <div className="text-dim">{analysis.sentiment_context.strategy_reason}</div>
                      </div>
                    </div>
                  )}
                  {analysis.position_advice && (
                    <div className="bg-card rounded-xl p-4 border border-edge">
                      <h4 className="text-xs font-semibold text-dim mb-2">仓位建议</h4>
                      <div className="text-sm space-y-1">
                        <div>建议仓位: <span className="font-medium">{analysis.position_advice.suggested_size}</span></div>
                        <div>进场方式: {analysis.position_advice.entry_type}</div>
                        <div>止损条件: {analysis.position_advice.stop_condition}</div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
