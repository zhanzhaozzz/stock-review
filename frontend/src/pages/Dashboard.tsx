import { useEffect, useState, useCallback } from "react";
import api from "../api/client";
import { getPctColor, formatPct } from "../utils/stockColor";

interface IndexQuote {
  code: string;
  name: string;
  price: number;
  change: number;
  change_pct: number;
}

interface Breadth {
  up: number;
  down: number;
  flat: number;
  limit_up: number;
  limit_down: number;
  total: number;
}

interface SectorItem {
  name: string;
  change_pct: number;
  up_count: number;
  down_count: number;
}

export default function Dashboard() {
  const [indices, setIndices] = useState<IndexQuote[]>([]);
  const [breadth, setBreadth] = useState<Breadth | null>(null);
  const [sectors, setSectors] = useState<SectorItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [overviewRes, sectorsRes] = await Promise.allSettled([
        api.get("/market/overview"),
        api.get("/market/sectors?sector_type=concept&limit=20"),
      ]);
      if (overviewRes.status === "fulfilled") {
        const data = overviewRes.value.data;
        setIndices(data.indices || []);
        setBreadth(data.breadth || null);
      }
      if (sectorsRes.status === "fulfilled") {
        setSectors(sectorsRes.value.data || []);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  async function handleSync() {
    setSyncing(true);
    try {
      await api.post("/sync/market");
      await loadData();
    } catch {
      /* sync failed */
    } finally {
      setSyncing(false);
    }
  }

  const hasData = indices.length > 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">市场总览</h2>
        <div className="flex items-center gap-2">
          <button
            onClick={handleSync}
            disabled={syncing}
            className="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg transition"
          >
            {syncing ? "同步中..." : "同步数据"}
          </button>
          <button
            onClick={loadData}
            className="px-3 py-1.5 text-sm bg-gray-800 hover:bg-gray-700 rounded-lg transition"
          >
            刷新
          </button>
        </div>
      </div>

      {loading ? (
        <div className="text-gray-500 text-center py-20">加载中...</div>
      ) : !hasData ? (
        <div className="text-gray-500 text-center py-20">
          <p>暂无市场数据</p>
          <p className="text-xs mt-2 text-gray-600">
            点击"同步数据"从外部接口采集并存入数据库
          </p>
        </div>
      ) : (
        <>
          {/* 大盘指数卡片 */}
          <div className="grid grid-cols-4 gap-4">
            {indices.map((idx) => (
              <div
                key={idx.code}
                className="bg-gray-900 rounded-xl p-4 border border-gray-800"
              >
                <div className="text-sm text-gray-400 mb-1">{idx.name}</div>
                <div className={`text-2xl font-bold ${getPctColor(idx.change_pct)}`}>
                  {idx.price?.toFixed(2) || "--"}
                </div>
                <div className={`text-sm mt-1 ${getPctColor(idx.change_pct)}`}>
                  {formatPct(idx.change_pct)} ({idx.change >= 0 ? "+" : ""}{idx.change?.toFixed(2)})
                </div>
              </div>
            ))}
          </div>

          {/* 涨跌面统计 */}
          {breadth && breadth.total > 0 && (
            <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
              <h3 className="text-sm font-semibold text-gray-400 mb-3">涨跌面统计</h3>
              <div className="flex items-center gap-6">
                <div className="flex items-center gap-2">
                  <span className="text-up font-bold text-lg">{breadth.up}</span>
                  <span className="text-gray-500 text-sm">上涨</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-down font-bold text-lg">{breadth.down}</span>
                  <span className="text-gray-500 text-sm">下跌</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-flat font-bold text-lg">{breadth.flat}</span>
                  <span className="text-gray-500 text-sm">平盘</span>
                </div>
                <div className="h-6 w-px bg-gray-700" />
                <div className="flex items-center gap-2">
                  <span className="text-up font-bold">{breadth.limit_up}</span>
                  <span className="text-gray-500 text-sm">涨停</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-down font-bold">{breadth.limit_down}</span>
                  <span className="text-gray-500 text-sm">跌停</span>
                </div>
                {/* 涨跌比例条 */}
                <div className="flex-1 h-3 rounded-full overflow-hidden flex">
                  <div
                    className="bg-red-500 h-full"
                    style={{ width: `${(breadth.up / breadth.total) * 100}%` }}
                  />
                  <div
                    className="bg-gray-600 h-full"
                    style={{ width: `${(breadth.flat / breadth.total) * 100}%` }}
                  />
                  <div
                    className="bg-green-500 h-full"
                    style={{ width: `${(breadth.down / breadth.total) * 100}%` }}
                  />
                </div>
              </div>
            </div>
          )}

          {/* 板块排行 */}
          <div className="bg-gray-900 rounded-xl border border-gray-800">
            <div className="px-4 py-3 border-b border-gray-800">
              <h3 className="text-sm font-semibold text-gray-400">概念板块排行</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-gray-500 border-b border-gray-800">
                    <th className="text-left px-4 py-2">排名</th>
                    <th className="text-left px-4 py-2">板块名称</th>
                    <th className="text-right px-4 py-2">涨跌幅</th>
                    <th className="text-right px-4 py-2">上涨</th>
                    <th className="text-right px-4 py-2">下跌</th>
                  </tr>
                </thead>
                <tbody>
                  {sectors.map((s, i) => (
                    <tr key={s.name} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                      <td className="px-4 py-2 text-gray-500">{i + 1}</td>
                      <td className="px-4 py-2 font-medium">{s.name}</td>
                      <td className={`px-4 py-2 text-right font-mono ${getPctColor(s.change_pct)}`}>
                        {formatPct(s.change_pct)}
                      </td>
                      <td className="px-4 py-2 text-right text-up">{s.up_count}</td>
                      <td className="px-4 py-2 text-right text-down">{s.down_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
