import { useEffect, useState, useCallback } from "react";
import api from "../api/client";
import { getPctColor, formatPct } from "../utils/stockColor";
import StockDrawer from "../components/StockDrawer";

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

interface ConstituentStock {
  code: string;
  name: string;
  price: number;
  change_pct: number;
  volume: number;
  amount: number;
  turnover_rate: number;
}

export default function Dashboard() {
  const [indices, setIndices] = useState<IndexQuote[]>([]);
  const [breadth, setBreadth] = useState<Breadth | null>(null);
  const [sectors, setSectors] = useState<SectorItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  const [expandedSector, setExpandedSector] = useState<string | null>(null);
  const [constituents, setConstituents] = useState<ConstituentStock[]>([]);
  const [loadingCons, setLoadingCons] = useState(false);
  const [selectedStock, setSelectedStock] = useState<{ code: string; name: string } | null>(null);

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

  async function toggleSector(name: string) {
    if (expandedSector === name) {
      setExpandedSector(null);
      setConstituents([]);
      return;
    }
    setExpandedSector(name);
    setLoadingCons(true);
    setConstituents([]);
    try {
      const res = await api.get(`/market/sectors/${encodeURIComponent(name)}/constituents?limit=30`);
      setConstituents(res.data || []);
    } catch {
      setConstituents([]);
    } finally {
      setLoadingCons(false);
    }
  }

  function formatAmount(val: number): string {
    if (!val) return "--";
    if (val >= 1e8) return (val / 1e8).toFixed(2) + "亿";
    if (val >= 1e4) return (val / 1e4).toFixed(0) + "万";
    return val.toFixed(0);
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
            className="px-3 py-1.5 text-sm bg-input hover:bg-card-hover rounded-lg transition"
          >
            刷新
          </button>
        </div>
      </div>

      {loading ? (
        <div className="text-dim text-center py-20">加载中...</div>
      ) : !hasData ? (
        <div className="text-dim text-center py-20">
          <p>暂无市场数据</p>
          <p className="text-xs mt-2 text-dim">
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
                className="bg-card rounded-xl p-4 border border-edge"
              >
                <div className="text-sm text-muted mb-1">{idx.name}</div>
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
            <div className="bg-card rounded-xl p-4 border border-edge">
              <h3 className="text-sm font-semibold text-muted mb-3">涨跌面统计</h3>
              <div className="flex items-center gap-6">
                <div className="flex items-center gap-2">
                  <span className="text-up font-bold text-lg">{breadth.up}</span>
                  <span className="text-dim text-sm">上涨</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-down font-bold text-lg">{breadth.down}</span>
                  <span className="text-dim text-sm">下跌</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-flat font-bold text-lg">{breadth.flat}</span>
                  <span className="text-dim text-sm">平盘</span>
                </div>
                <div className="h-6 w-px bg-input" />
                <div className="flex items-center gap-2">
                  <span className="text-up font-bold">{breadth.limit_up}</span>
                  <span className="text-dim text-sm">涨停</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-down font-bold">{breadth.limit_down}</span>
                  <span className="text-dim text-sm">跌停</span>
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
          <div className="bg-card rounded-xl border border-edge">
            <div className="px-4 py-3 border-b border-edge">
              <h3 className="text-sm font-semibold text-muted">概念板块排行（点击展开成分股）</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-dim border-b border-edge">
                    <th className="text-left px-4 py-2">排名</th>
                    <th className="text-left px-4 py-2">板块名称</th>
                    <th className="text-right px-4 py-2">涨跌幅</th>
                    <th className="text-right px-4 py-2">上涨</th>
                    <th className="text-right px-4 py-2">下跌</th>
                  </tr>
                </thead>
                <tbody>
                  {sectors.map((s, i) => (
                    <>
                      <tr
                        key={s.name}
                        className={`border-b border-edge-light cursor-pointer transition ${
                          expandedSector === s.name ? "bg-card-hover" : "hover:bg-card-hover"
                        }`}
                        onClick={() => toggleSector(s.name)}
                      >
                        <td className="px-4 py-2 text-dim">{i + 1}</td>
                        <td className="px-4 py-2 font-medium">
                          <span className="mr-1.5 text-xs text-dim">
                            {expandedSector === s.name ? "▼" : "▶"}
                          </span>
                          {s.name}
                        </td>
                        <td className={`px-4 py-2 text-right font-mono ${getPctColor(s.change_pct)}`}>
                          {formatPct(s.change_pct)}
                        </td>
                        <td className="px-4 py-2 text-right text-up">{s.up_count}</td>
                        <td className="px-4 py-2 text-right text-down">{s.down_count}</td>
                      </tr>

                      {/* 成分股展开区域 */}
                      {expandedSector === s.name && (
                        <tr key={`${s.name}-cons`}>
                          <td colSpan={5} className="p-0">
                            <div className="bg-base border-b border-edge">
                              {loadingCons ? (
                                <div className="text-dim text-center py-6 text-xs">加载成分股中...</div>
                              ) : constituents.length === 0 ? (
                                <div className="text-dim text-center py-6 text-xs">暂无成分股数据</div>
                              ) : (
                                <div className="px-4 py-3">
                                  <div className="grid grid-cols-5 gap-2 text-xs text-dim mb-2 px-2">
                                    <span>代码 / 名称</span>
                                    <span className="text-right">最新价</span>
                                    <span className="text-right">涨跌幅</span>
                                    <span className="text-right">成交额</span>
                                    <span className="text-right">换手率</span>
                                  </div>
                                  <div className="max-h-80 overflow-y-auto space-y-0.5">
                                    {constituents.map((stock) => (
                                      <div
                                        key={stock.code}
                                        className="grid grid-cols-5 gap-2 items-center px-2 py-1.5 rounded hover:bg-card-hover cursor-pointer transition text-sm"
                                        onClick={(e) => {
                                          e.stopPropagation();
                                          setSelectedStock({ code: stock.code, name: stock.name });
                                        }}
                                      >
                                        <div>
                                          <div className="font-medium">{stock.name}</div>
                                          <div className="text-xs text-dim font-mono">{stock.code}</div>
                                        </div>
                                        <div className="text-right font-mono">
                                          {stock.price?.toFixed(2) || "--"}
                                        </div>
                                        <div className={`text-right font-mono ${getPctColor(stock.change_pct)}`}>
                                          {formatPct(stock.change_pct)}
                                        </div>
                                        <div className="text-right text-muted">
                                          {formatAmount(stock.amount)}
                                        </div>
                                        <div className="text-right text-muted">
                                          {stock.turnover_rate ? stock.turnover_rate.toFixed(2) + "%" : "--"}
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
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
