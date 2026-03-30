import { useEffect, useState, useCallback } from "react";
import api from "../api/client";

interface NewsItem {
  title: string;
  url: string;
  source: string;
  summary: string;
  publish_time: string | null;
}

const SOURCE_COLORS: Record<string, string> = {
  "财联社": "bg-red-900/50 text-red-300",
  "财联社(东财)": "bg-red-900/50 text-red-300",
  "东方财富": "bg-orange-900/50 text-orange-300",
  "新浪财经": "bg-blue-900/50 text-blue-300",
};

type TabType = "latest" | "flash";

export default function News() {
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [activeTab, setActiveTab] = useState<TabType>("latest");
  const [stockCode, setStockCode] = useState("");
  const [stockNews, setStockNews] = useState<NewsItem[]>([]);
  const [searchingStock, setSearchingStock] = useState(false);

  const loadNews = useCallback(async () => {
    setLoading(true);
    try {
      const endpoint = activeTab === "flash" ? "/news/flash" : "/news/latest";
      const res = await api.get(endpoint, { params: { limit: 50 } });
      setNews(res.data || []);
    } catch {
      setNews([]);
    } finally {
      setLoading(false);
    }
  }, [activeTab]);

  useEffect(() => {
    loadNews();
  }, [loadNews]);

  async function handleSync() {
    setSyncing(true);
    try {
      await api.post("/news/sync");
      await loadNews();
    } catch {
      /* sync failed, still show cached data */
    } finally {
      setSyncing(false);
    }
  }

  async function searchStockNews() {
    if (!stockCode.trim()) return;
    setSearchingStock(true);
    try {
      const res = await api.get(`/news/stock/${stockCode.trim()}`);
      setStockNews(res.data || []);
    } finally {
      setSearchingStock(false);
    }
  }

  function formatTime(t: string | null): string {
    if (!t) return "";
    try {
      const d = new Date(t);
      const now = new Date();
      const diff = now.getTime() - d.getTime();
      if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
      if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
      return d.toLocaleDateString("zh-CN", {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return t.slice(0, 16);
    }
  }

  function renderNewsItem(item: NewsItem, idx: number) {
    return (
      <div
        key={`${item.url}-${idx}`}
        className="px-4 py-3 border-b border-gray-800/50 hover:bg-gray-800/30 transition"
      >
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 mt-1">
            <span
              className={`px-1.5 py-0.5 text-[10px] rounded font-medium ${
                SOURCE_COLORS[item.source] || "bg-gray-800 text-gray-400"
              }`}
            >
              {item.source}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <a
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm font-medium text-gray-200 hover:text-white transition leading-snug block"
            >
              {item.title}
            </a>
            {item.summary && (
              <p className="text-xs text-gray-500 mt-1 line-clamp-2">
                {item.summary}
              </p>
            )}
          </div>
          <div className="flex-shrink-0 text-xs text-gray-600 whitespace-nowrap">
            {formatTime(item.publish_time)}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">新闻聚合</h2>
        <div className="flex items-center gap-2">
          <button
            onClick={handleSync}
            disabled={syncing}
            className="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg transition"
          >
            {syncing ? "采集中..." : "采集新闻"}
          </button>
          <button
            onClick={loadNews}
            className="px-3 py-1.5 text-sm bg-gray-800 hover:bg-gray-700 rounded-lg transition"
          >
            刷新
          </button>
        </div>
      </div>

      {/* 标签切换 + 个股搜索 */}
      <div className="flex items-center justify-between">
        <div className="flex gap-2">
          <button
            onClick={() => setActiveTab("latest")}
            className={`px-3 py-1.5 text-sm rounded-lg transition ${
              activeTab === "latest"
                ? "bg-blue-600 text-white"
                : "bg-gray-800 text-gray-400 hover:bg-gray-700"
            }`}
          >
            综合资讯
          </button>
          <button
            onClick={() => setActiveTab("flash")}
            className={`px-3 py-1.5 text-sm rounded-lg transition ${
              activeTab === "flash"
                ? "bg-blue-600 text-white"
                : "bg-gray-800 text-gray-400 hover:bg-gray-700"
            }`}
          >
            财联社快讯
          </button>
        </div>
        <div className="flex gap-2">
          <input
            value={stockCode}
            onChange={(e) => setStockCode(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && searchStockNews()}
            placeholder="个股代码"
            className="w-32 bg-gray-800 border border-gray-700 rounded-lg px-2 py-1 text-sm focus:outline-none focus:border-blue-500"
          />
          <button
            onClick={searchStockNews}
            disabled={searchingStock}
            className="px-3 py-1 text-sm bg-gray-700 hover:bg-gray-600 rounded-lg transition"
          >
            搜索
          </button>
        </div>
      </div>

      <div className="flex gap-6">
        {/* 主新闻列表 */}
        <div className="flex-1 bg-gray-900 rounded-xl border border-gray-800">
          <div className="px-4 py-3 border-b border-gray-800">
            <h3 className="text-sm font-semibold text-gray-400">
              {activeTab === "flash" ? "财联社7x24快讯" : "综合财经资讯"}
            </h3>
          </div>
          {loading ? (
            <div className="text-gray-500 text-center py-20">加载中...</div>
          ) : news.length === 0 ? (
            <div className="text-gray-500 text-center py-20">
              <p>暂无新闻数据</p>
              <p className="text-xs mt-2">点击"采集新闻"从外部源获取最新资讯</p>
            </div>
          ) : (
            <div className="max-h-[70vh] overflow-y-auto">
              {news.map((item, i) => renderNewsItem(item, i))}
            </div>
          )}
        </div>

        {/* 个股新闻侧栏 */}
        {stockNews.length > 0 && (
          <div className="w-80 bg-gray-900 rounded-xl border border-gray-800">
            <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-gray-400">
                个股新闻: {stockCode}
              </h3>
              <button
                onClick={() => setStockNews([])}
                className="text-xs text-gray-500 hover:text-gray-300"
              >
                关闭
              </button>
            </div>
            <div className="max-h-[70vh] overflow-y-auto">
              {stockNews.map((item, i) => (
                <div
                  key={`stock-${item.url}-${i}`}
                  className="px-4 py-3 border-b border-gray-800/50"
                >
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-gray-200 hover:text-white block leading-snug"
                  >
                    {item.title}
                  </a>
                  <div className="text-xs text-gray-600 mt-1">
                    {item.source} · {formatTime(item.publish_time)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
