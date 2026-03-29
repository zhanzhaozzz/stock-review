import { useEffect, useState, useCallback } from "react";
import api from "../api/client";

interface ReviewItem {
  id: number;
  date: string;
  market_sentiment: string;
  market_height: number;
  total_limit_up: number;
  first_board_count: number;
  broken_board_count: number;
  main_sector: string;
  sub_sector: string;
  review_summary: string;
  next_day_plan: string;
  applicable_strategy: string;
  suggested_position: string;
  is_confirmed: boolean;
}

const phaseColors: Record<string, string> = {
  "冰点": "text-blue-400 bg-blue-500/10",
  "启动": "text-cyan-400 bg-cyan-500/10",
  "发酵": "text-yellow-400 bg-yellow-500/10",
  "高潮": "text-red-400 bg-red-500/10",
  "高位混沌": "text-orange-400 bg-orange-500/10",
  "分歧": "text-purple-400 bg-purple-500/10",
  "退潮": "text-green-400 bg-green-500/10",
};

export default function Review() {
  const [reviews, setReviews] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [selected, setSelected] = useState<ReviewItem | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get("/review/list?limit=30");
      setReviews(res.data || []);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  async function handleRun() {
    setRunning(true);
    try {
      await api.post("/review/run");
      await loadData();
    } catch (e: any) {
      if (e.response?.status === 409) {
        alert("今日复盘已存在");
      }
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">每日复盘</h2>
        <button
          onClick={handleRun}
          disabled={running}
          className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg transition"
        >
          {running ? "复盘中..." : "执行复盘"}
        </button>
      </div>

      {loading ? (
        <div className="text-gray-500 text-center py-20">加载中...</div>
      ) : reviews.length === 0 ? (
        <div className="text-gray-500 text-center py-20">
          <p>暂无复盘数据</p>
          <p className="text-xs mt-2 text-gray-600">点击"执行复盘"生成今日复盘报告</p>
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-4">
          {/* 左侧列表 */}
          <div className="col-span-1 space-y-2">
            {reviews.map((r) => (
              <div
                key={r.id}
                onClick={() => setSelected(r)}
                className={`p-3 rounded-lg border cursor-pointer transition ${
                  selected?.id === r.id
                    ? "border-blue-500 bg-blue-500/5"
                    : "border-gray-800 bg-gray-900 hover:bg-gray-800"
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium">{r.date}</span>
                  <span className={`text-xs px-2 py-0.5 rounded ${phaseColors[r.market_sentiment] || "text-gray-400 bg-gray-500/10"}`}>
                    {r.market_sentiment}
                  </span>
                </div>
                <div className="text-xs text-gray-500">
                  高度{r.market_height}板 · 涨停{r.total_limit_up} · 炸板{r.broken_board_count}
                </div>
              </div>
            ))}
          </div>

          {/* 右侧详情 */}
          <div className="col-span-2">
            {selected ? (
              <div className="space-y-4">
                <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
                  <div className="flex items-center gap-3 mb-4">
                    <span className="text-lg font-bold">{selected.date}</span>
                    <span className={`text-sm px-3 py-1 rounded-full ${phaseColors[selected.market_sentiment] || "text-gray-400 bg-gray-500/10"}`}>
                      {selected.market_sentiment}
                    </span>
                  </div>

                  <div className="grid grid-cols-4 gap-4 mb-4">
                    <div className="text-center">
                      <div className="text-2xl font-bold">{selected.market_height}</div>
                      <div className="text-xs text-gray-500">市场高度</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-up">{selected.total_limit_up}</div>
                      <div className="text-xs text-gray-500">涨停数</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold">{selected.first_board_count}</div>
                      <div className="text-xs text-gray-500">首板数</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-yellow-400">{selected.broken_board_count}</div>
                      <div className="text-xs text-gray-500">炸板数</div>
                    </div>
                  </div>

                  {selected.main_sector && (
                    <div className="mb-3">
                      <span className="text-xs text-gray-500">主线板块: </span>
                      <span className="text-sm">{selected.main_sector}</span>
                    </div>
                  )}
                  {selected.sub_sector && (
                    <div className="mb-3">
                      <span className="text-xs text-gray-500">支线板块: </span>
                      <span className="text-sm text-gray-400">{selected.sub_sector}</span>
                    </div>
                  )}
                </div>

                {selected.review_summary && (
                  <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
                    <h3 className="text-sm font-semibold text-gray-400 mb-2">复盘总结</h3>
                    <p className="text-sm whitespace-pre-line">{selected.review_summary}</p>
                  </div>
                )}

                {selected.next_day_plan && (
                  <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
                    <h3 className="text-sm font-semibold text-gray-400 mb-2">次日计划</h3>
                    <p className="text-sm whitespace-pre-line">{selected.next_day_plan}</p>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
                    <h4 className="text-xs text-gray-500 mb-1">适用策略</h4>
                    <p className="text-sm">{selected.applicable_strategy || "—"}</p>
                  </div>
                  <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
                    <h4 className="text-xs text-gray-500 mb-1">建议仓位</h4>
                    <p className="text-sm">{selected.suggested_position || "—"}</p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-gray-500 text-center py-20">
                选择左侧的日期查看复盘详情
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
