import { useEffect, useState } from "react";
import api from "../api/client";
import { getPctColor, formatPct } from "../utils/stockColor";
import StockDrawer from "../components/StockDrawer";

interface WatchlistItem {
  id: number;
  code: string;
  name: string;
  market: string;
  group_name: string;
  note: string | null;
  latest_rating: number | null;
  latest_label: string | null;
  price: number | null;
  change_pct: number | null;
}

interface SearchResult {
  code: string;
  name: string;
  market: string;
}

const RATING_COLORS: Record<string, string> = {
  "强烈推荐": "text-red-400",
  "推荐": "text-orange-400",
  "中性": "text-yellow-400",
  "谨慎": "text-blue-400",
  "回避": "text-dim",
};

export default function Watchlist() {
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [groups, setGroups] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [activeGroup, setActiveGroup] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [showSearch, setShowSearch] = useState(false);
  const [selectedStock, setSelectedStock] = useState<{ code: string; name: string } | null>(null);

  useEffect(() => {
    loadData();
  }, [activeGroup]);

  async function loadData() {
    setLoading(true);
    try {
      const params: Record<string, string> = {};
      if (activeGroup) params.group = activeGroup;
      const [itemsRes, groupsRes] = await Promise.allSettled([
        api.get("/watchlist", { params }),
        api.get("/watchlist/groups"),
      ]);
      if (itemsRes.status === "fulfilled") setItems(itemsRes.value.data || []);
      if (groupsRes.status === "fulfilled") setGroups(groupsRes.value.data || []);
    } finally {
      setLoading(false);
    }
  }

  async function handleSyncQuotes() {
    setSyncing(true);
    try {
      await api.post("/sync/watchlist-quotes");
      await loadData();
    } catch {
      /* sync failed */
    } finally {
      setSyncing(false);
    }
  }

  async function handleSearch() {
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const res = await api.get("/watchlist/search", {
        params: { q: searchQuery },
      });
      setSearchResults(res.data || []);
    } finally {
      setSearching(false);
    }
  }

  async function addStock(code: string) {
    try {
      await api.post("/watchlist", { codes: [code] });
      setSearchResults(searchResults.filter((r) => r.code !== code));
      await loadData();
    } catch {
      /* empty */
    }
  }

  async function removeStock(code: string) {
    try {
      await api.delete(`/watchlist/${code}`);
      setItems(items.filter((i) => i.code !== code));
    } catch {
      /* empty */
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">自选股</h2>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowSearch(!showSearch)}
            className="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-500 rounded-lg transition"
          >
            {showSearch ? "收起" : "添加股票"}
          </button>
          <button
            onClick={handleSyncQuotes}
            disabled={syncing}
            className="px-3 py-1.5 text-sm bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 rounded-lg transition"
          >
            {syncing ? "同步中..." : "同步行情"}
          </button>
          <button
            onClick={loadData}
            className="px-3 py-1.5 text-sm bg-input hover:bg-card-hover rounded-lg transition"
          >
            刷新
          </button>
        </div>
      </div>

      {/* 搜索添加 */}
      {showSearch && (
        <div className="bg-card rounded-xl p-4 border border-edge space-y-3">
          <div className="flex gap-3">
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              placeholder="搜索股票代码或名称"
              className="flex-1 bg-input border border-edge rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
            />
            <button
              onClick={handleSearch}
              disabled={searching}
              className="px-4 py-2 bg-input hover:bg-card-hover text-sm rounded-lg transition"
            >
              {searching ? "搜索中..." : "搜索"}
            </button>
          </div>
          {searchResults.length > 0 && (
            <div className="max-h-60 overflow-y-auto space-y-1">
              {searchResults.map((r) => (
                <div
                  key={r.code}
                  className="flex items-center justify-between px-3 py-2 bg-card-hover rounded hover:bg-input"
                >
                  <div>
                    <span className="font-medium">{r.name}</span>
                    <span className="text-xs text-dim ml-2">{r.code}</span>
                  </div>
                  <button
                    onClick={() => addStock(r.code)}
                    className="px-2 py-1 text-xs bg-blue-600/30 text-blue-400 rounded hover:bg-blue-600/50"
                  >
                    加自选
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 分组标签 */}
      {groups.length > 1 && (
        <div className="flex gap-2">
          <button
            onClick={() => setActiveGroup(null)}
            className={`px-3 py-1 text-sm rounded-lg transition ${
              !activeGroup
                ? "bg-blue-600 text-white"
                : "bg-input text-muted hover:bg-card-hover"
            }`}
          >
            全部
          </button>
          {groups.map((g) => (
            <button
              key={g}
              onClick={() => setActiveGroup(g)}
              className={`px-3 py-1 text-sm rounded-lg transition ${
                activeGroup === g
                  ? "bg-blue-600 text-white"
                  : "bg-input text-muted hover:bg-card-hover"
              }`}
            >
              {g}
            </button>
          ))}
        </div>
      )}

      {loading ? (
        <div className="text-dim text-center py-20">加载中...</div>
      ) : items.length === 0 ? (
        <div className="text-dim text-center py-20">
          <p>自选股为空，点击"添加股票"开始添加</p>
          <p className="text-xs mt-2 text-dim">
            添加后点击"同步行情"从外部采集行情数据存入数据库
          </p>
        </div>
      ) : (
        <div className="bg-card rounded-xl border border-edge">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-dim border-b border-edge">
                  <th className="text-left px-4 py-3">股票</th>
                  <th className="text-right px-4 py-3">最新价</th>
                  <th className="text-right px-4 py-3">涨跌幅</th>
                  <th className="text-right px-4 py-3">评分</th>
                  <th className="text-center px-4 py-3">评级</th>
                  <th className="text-left px-4 py-3">分组</th>
                  <th className="text-center px-4 py-3">操作</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr
                    key={item.code}
                    className="border-b border-edge-light hover:bg-card-hover cursor-pointer"
                    onClick={() => setSelectedStock({ code: item.code, name: item.name })}
                  >
                    <td className="px-4 py-3">
                      <div className="font-medium">{item.name}</div>
                      <div className="text-xs text-dim">{item.code}</div>
                    </td>
                    <td className="px-4 py-3 text-right font-mono">
                      {item.price?.toFixed(2) ?? "--"}
                    </td>
                    <td
                      className={`px-4 py-3 text-right font-mono ${
                        item.change_pct != null
                          ? getPctColor(item.change_pct)
                          : "text-dim"
                      }`}
                    >
                      {item.change_pct != null
                        ? formatPct(item.change_pct)
                        : "--"}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-yellow-400">
                      {item.latest_rating?.toFixed(1) ?? "--"}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {item.latest_label ? (
                        <span
                          className={`text-xs font-medium ${
                            RATING_COLORS[item.latest_label] || "text-muted"
                          }`}
                        >
                          {item.latest_label}
                        </span>
                      ) : (
                        <span className="text-xs text-dim">未评级</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs text-dim">
                      {item.group_name}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          removeStock(item.code);
                        }}
                        className="px-2 py-1 text-xs text-red-400 hover:bg-red-950 rounded transition"
                      >
                        删除
                      </button>
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
