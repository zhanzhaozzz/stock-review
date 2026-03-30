import { useEffect, useState } from "react";
import api from "../api/client";
import { useAppStore } from "../stores/useAppStore";

export default function Settings() {
  const [health, setHealth] = useState<{ status: string; app: string } | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState("");
  const { cyclePhase, suggestedPosition, matchedStrategies, loadingRecommend, refreshRecommend } = useAppStore();

  useEffect(() => {
    api.get("/health").then((r) => setHealth(r.data)).catch(() => {});
  }, []);

  useEffect(() => {
    refreshRecommend();
  }, [refreshRecommend]);

  async function handleSyncAll() {
    setSyncing(true);
    setSyncResult("");
    try {
      const res = await api.post("/sync/all");
      setSyncResult(JSON.stringify(res.data, null, 2));
    } catch (e: any) {
      setSyncResult("同步失败: " + (e.message || "未知错误"));
    } finally {
      setSyncing(false);
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold">系统设置</h2>

      {/* 系统状态 */}
      <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
        <h3 className="text-sm font-semibold text-gray-400 mb-3">系统状态</h3>
        {health ? (
          <div className="flex items-center gap-3">
            <span className="w-2 h-2 rounded-full bg-green-500" />
            <span className="text-sm">{health.app} — {health.status}</span>
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <span className="w-2 h-2 rounded-full bg-red-500" />
            <span className="text-sm text-red-400">后端连接失败</span>
          </div>
        )}
      </div>

      {/* 数据同步 */}
      <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
        <h3 className="text-sm font-semibold text-gray-400 mb-3">数据同步</h3>
        <p className="text-xs text-gray-500 mb-4">
          手动触发全量数据同步 (市场数据 + 新闻 + 自选股行情)
        </p>
        <button
          onClick={handleSyncAll}
          disabled={syncing}
          className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg transition"
        >
          {syncing ? "同步中..." : "全量同步"}
        </button>
        {syncResult && (
          <pre className="mt-4 text-xs bg-gray-800 rounded-lg p-3 overflow-auto max-h-60">
            {syncResult}
          </pre>
        )}
      </div>

      {/* 定时任务说明 */}
      <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
        <h3 className="text-sm font-semibold text-gray-400 mb-3">定时任务</h3>
        <div className="text-sm space-y-2 text-gray-400">
          <div className="flex items-center gap-3">
            <span className="font-mono text-xs bg-gray-800 px-2 py-0.5 rounded">15:30</span>
            <span>同步市场数据</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="font-mono text-xs bg-gray-800 px-2 py-0.5 rounded">每小时</span>
            <span>同步新闻数据 (9:00-20:00)</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="font-mono text-xs bg-gray-800 px-2 py-0.5 rounded">15:35</span>
            <span>同步自选股行情</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="font-mono text-xs bg-gray-800 px-2 py-0.5 rounded">15:40</span>
            <span>自选股评级</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="font-mono text-xs bg-gray-800 px-2 py-0.5 rounded">15:50</span>
            <span>每日复盘</span>
          </div>
        </div>
      </div>

      {/* 今日推荐 */}
      <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-gray-400">今日推荐（情绪周期→战法）</h3>
          <button
            onClick={refreshRecommend}
            disabled={loadingRecommend}
            className="px-3 py-1 text-xs bg-gray-800 hover:bg-gray-700 disabled:opacity-50 rounded-lg"
          >
            {loadingRecommend ? "刷新中..." : "刷新"}
          </button>
        </div>
        <div className="text-sm text-gray-400 space-y-2">
          <div>当前情绪: <span className="text-gray-200 font-medium">{cyclePhase || "—"}</span></div>
          <div>建议仓位: <span className="text-gray-200 font-medium">{suggestedPosition || "—"}</span></div>
          <div className="text-xs text-gray-500">
            适用战法: {matchedStrategies.length ? matchedStrategies.join("、") : "—"}
          </div>
        </div>
      </div>

      {/* 关于 */}
      <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
        <h3 className="text-sm font-semibold text-gray-400 mb-3">关于</h3>
        <div className="text-sm text-gray-400 space-y-1">
          <div>Stock Review — 个人每日股票分析复盘系统</div>
          <div>版本: 0.2.0 (Sprint 3)</div>
          <div>覆盖: A股 + 港股</div>
        </div>
      </div>
    </div>
  );
}
