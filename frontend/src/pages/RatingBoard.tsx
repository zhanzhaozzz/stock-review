import { useEffect, useState } from "react";
import api from "../api/client";
import StockDrawer from "../components/StockDrawer";

interface RatingItem {
  code: string;
  name: string;
  market: string;
  date: string;
  trend_score: number;
  momentum_score: number;
  volatility_score: number;
  volume_score: number;
  value_score: number;
  sentiment_score: number;
  fundamental_score: number | null;
  ai_score: number;
  total_score: number;
  rating: string;
  reason: string;
  pe: number | null;
  pb: number | null;
  roe: number | null;
  price?: number;
  change_pct?: number;
}

const RATING_COLORS: Record<string, string> = {
  "强烈推荐": "text-red-400 bg-red-950",
  "推荐": "text-orange-400 bg-orange-950",
  "中性": "text-yellow-400 bg-yellow-950",
  "谨慎": "text-blue-400 bg-blue-950",
  "回避": "text-gray-400 bg-gray-800",
};

const SORT_OPTIONS = [
  { key: "total_score", label: "综合评分" },
  { key: "trend_score", label: "趋势" },
  { key: "momentum_score", label: "动量" },
  { key: "ai_score", label: "AI评分" },
];

export default function RatingBoard() {
  const [ratings, setRatings] = useState<RatingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [selectedStock, setSelectedStock] = useState<{ code: string; name: string } | null>(null);
  const [sortBy, setSortBy] = useState("total_score");
  const [stockInput, setStockInput] = useState("");

  useEffect(() => {
    loadRatings();
  }, [sortBy]);

  async function loadRatings() {
    setLoading(true);
    try {
      const res = await api.get("/ratings/latest", {
        params: { limit: 50, sort_by: sortBy },
      });
      setRatings(res.data || []);
    } catch {
      /* empty */
    } finally {
      setLoading(false);
    }
  }

  async function runRating() {
    if (!stockInput.trim()) return;
    setRunning(true);
    try {
      const codes = stockInput.split(/[,，\s]+/).filter(Boolean);
      const res = await api.post("/ratings/run", { codes });
      if (res.data?.results) {
        setRatings(res.data.results);
      }
    } catch {
      /* empty */
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">量化评级</h2>
        <div className="flex items-center gap-3">
          <div className="flex gap-1">
            {SORT_OPTIONS.map((opt) => (
              <button
                key={opt.key}
                onClick={() => setSortBy(opt.key)}
                className={`px-2 py-1 text-xs rounded transition ${
                  sortBy === opt.key
                    ? "bg-blue-600 text-white"
                    : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
          <button
            onClick={loadRatings}
            className="px-3 py-1.5 text-sm bg-gray-800 hover:bg-gray-700 rounded-lg transition"
          >
            刷新
          </button>
        </div>
      </div>

      {/* 执行评级 */}
      <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
        <div className="flex gap-3">
          <input
            value={stockInput}
            onChange={(e) => setStockInput(e.target.value)}
            placeholder="输入股票代码，多只用逗号分隔，如 600519,000001,hk00700"
            className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
          />
          <button
            onClick={runRating}
            disabled={running}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 text-sm font-medium rounded-lg transition"
          >
            {running ? "评级中..." : "执行评级"}
          </button>
        </div>
      </div>

      {loading ? (
        <div className="text-gray-500 text-center py-20">加载中...</div>
      ) : ratings.length === 0 ? (
        <div className="text-gray-500 text-center py-20">
          暂无评级数据，请先执行评级
        </div>
      ) : (
        <div className="bg-gray-900 rounded-xl border border-gray-800">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-500 border-b border-gray-800">
                  <th className="text-left px-4 py-3">排名</th>
                  <th className="text-left px-4 py-3">股票</th>
                  <th className="text-right px-4 py-3">综合评分</th>
                  <th className="text-center px-4 py-3">评级</th>
                  <th className="text-right px-4 py-3">趋势</th>
                  <th className="text-right px-4 py-3">动量</th>
                  <th className="text-right px-4 py-3">波动</th>
                  <th className="text-right px-4 py-3">成交</th>
                  <th className="text-right px-4 py-3">AI</th>
                  <th className="text-right px-4 py-3">基本面</th>
                </tr>
              </thead>
              <tbody>
                {ratings.map((r, i) => (
                    <tr
                      key={r.code}
                      className="border-b border-gray-800/50 hover:bg-gray-800/30 cursor-pointer"
                      onClick={() => setSelectedStock({ code: r.code, name: r.name })}
                    >
                      <td className="px-4 py-3 text-gray-500">{i + 1}</td>
                      <td className="px-4 py-3">
                        <div className="font-medium">{r.name}</div>
                        <div className="text-xs text-gray-500">{r.code}</div>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className="text-lg font-bold text-yellow-400">
                          {r.total_score.toFixed(1)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span
                          className={`px-2 py-0.5 rounded text-xs font-medium ${
                            RATING_COLORS[r.rating] || "bg-gray-800"
                          }`}
                        >
                          {r.rating}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-gray-300">
                        {r.trend_score.toFixed(0)}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-gray-300">
                        {r.momentum_score.toFixed(0)}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-gray-300">
                        {r.volatility_score.toFixed(0)}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-gray-300">
                        {r.volume_score.toFixed(0)}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-blue-400">
                        {r.ai_score.toFixed(0)}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-gray-300">
                        {r.fundamental_score?.toFixed(0) ?? "--"}
                      </td>
                    </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {selectedStock && (
        <StockDrawer
          code={selectedStock.code}
          name={selectedStock.name}
          onClose={() => setSelectedStock(null)}
        />
      )}
    </div>
  );
}
