import { useEffect, useState, useCallback } from "react";
import { useParams } from "react-router-dom";
import api from "../api/client";

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

export default function StockDetail() {
  const { code } = useParams<{ code: string }>();
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [rating, setRating] = useState<RatingInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);

  const loadData = useCallback(async () => {
    if (!code) return;
    setLoading(true);
    try {
      const [analysisRes, ratingRes] = await Promise.allSettled([
        api.get(`/analysis/history?code=${code}&limit=1`),
        api.get(`/ratings/history/${code}?limit=1`),
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
    "观望": "text-gray-400 bg-gray-500/10 border-gray-500/30",
    "卖出": "text-green-400 bg-green-500/10 border-green-500/30",
  };

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
        <div className="text-gray-500 text-center py-20">加载中...</div>
      ) : !analysis && !rating ? (
        <div className="text-gray-500 text-center py-20">
          <p>暂无分析数据</p>
          <p className="text-xs mt-2 text-gray-600">点击"运行 AI 分析"获取深度分析报告</p>
        </div>
      ) : (
        <>
          {/* 评级概览 */}
          {rating && (
            <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
              <h3 className="text-sm font-semibold text-gray-400 mb-3">量化评级</h3>
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
                      <div className="text-gray-500">{d.label}</div>
                      <div className="text-sm font-mono">{d.v?.toFixed(0) || "--"}</div>
                    </div>
                  ))}
                </div>
              </div>
              {rating.reason && (
                <p className="mt-3 text-sm text-gray-400">{rating.reason}</p>
              )}
            </div>
          )}

          {/* AI 分析报告 */}
          {analysis && (
            <>
              <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold text-gray-400">AI 分析报告</h3>
                  <span className={`px-3 py-1 text-sm rounded-full border ${signalColor[analysis.signal] || "text-gray-400"}`}>
                    {analysis.signal} · {analysis.score?.toFixed(0)}分
                  </span>
                </div>
                <p className="text-sm">{analysis.summary}</p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                {analysis.target_price != null && (
                  <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
                    <div className="text-xs text-gray-500 mb-1">目标价</div>
                    <div className="text-xl font-bold text-up">{analysis.target_price.toFixed(2)}</div>
                  </div>
                )}
                {analysis.stop_loss != null && (
                  <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
                    <div className="text-xs text-gray-500 mb-1">止损价</div>
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
                  <div key={sec.title} className="bg-gray-900 rounded-xl p-4 border border-gray-800">
                    <h4 className="text-xs font-semibold text-gray-500 mb-2">{sec.title}</h4>
                    <p className="text-sm text-gray-300 whitespace-pre-line">{sec.content || "暂无"}</p>
                  </div>
                ))}
              </div>

              {/* 要点 & 风险 */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
                  <h4 className="text-xs font-semibold text-gray-500 mb-2">关键要点</h4>
                  <ul className="space-y-1">
                    {(analysis.key_points || []).map((p, i) => (
                      <li key={i} className="text-sm text-gray-300">• {p}</li>
                    ))}
                  </ul>
                </div>
                <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
                  <h4 className="text-xs font-semibold text-gray-500 mb-2">风险提示</h4>
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
                    <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
                      <h4 className="text-xs font-semibold text-gray-500 mb-2">情绪周期</h4>
                      <div className="text-sm space-y-1">
                        <div>当前周期: <span className="font-medium">{analysis.sentiment_context.current_cycle}</span></div>
                        <div>建议策略: {analysis.sentiment_context.applicable_strategy}</div>
                        <div className="text-gray-500">{analysis.sentiment_context.strategy_reason}</div>
                      </div>
                    </div>
                  )}
                  {analysis.position_advice && (
                    <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
                      <h4 className="text-xs font-semibold text-gray-500 mb-2">仓位建议</h4>
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
