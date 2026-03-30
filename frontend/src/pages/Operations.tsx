import { useEffect, useState, useCallback } from "react";
import api from "../api/client";
import { getPctColor, formatPct } from "../utils/stockColor";
import WinRatePie from "../components/charts/WinRatePie";

interface OperationItem {
  id: number;
  date: string;
  strategy_used: string;
  target_stock: string;
  action: string;
  entry_price: number | null;
  exit_price: number | null;
  pnl_pct: number | null;
  note: string;
  is_correct: boolean | null;
}

interface Stats {
  total: number;
  win_rate: number;
  avg_pnl: number;
  total_pnl: number;
  correct_rate: number;
  by_strategy?: { strategy: string; total: number; win_rate: number; avg_pnl: number }[];
  by_cycle?: { cycle: string; total: number; win_rate: number; avg_pnl: number }[];
}

export default function Operations() {
  const [records, setRecords] = useState<OperationItem[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<Partial<OperationItem> | null>(null);
  const [saving, setSaving] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [listRes, statsRes] = await Promise.allSettled([
        api.get("/operations/list"),
        api.get("/operations/stats"),
      ]);
      if (listRes.status === "fulfilled") setRecords(listRes.value.data || []);
      if (statsRes.status === "fulfilled") setStats(statsRes.value.data);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  function handleNew() {
    setEditing({
      date: new Date().toISOString().split("T")[0],
      strategy_used: "",
      target_stock: "",
      action: "买入",
      note: "",
    });
  }

  async function handleSave() {
    if (!editing?.target_stock) return;
    setSaving(true);
    try {
      if (editing.id) {
        await api.put(`/operations/${editing.id}`, editing);
      } else {
        await api.post("/operations/create", editing);
      }
      setEditing(null);
      await loadData();
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("确认删除?")) return;
    await api.delete(`/operations/${id}`);
    await loadData();
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">操作记录</h2>
        <button
          onClick={handleNew}
          className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-500 rounded-lg transition"
        >
          记录操作
        </button>
      </div>

      {/* 统计卡片 */}
      {stats && stats.total > 0 && (
        <>
          <div className="grid grid-cols-5 gap-4">
            <div className="bg-gray-900 rounded-xl p-4 border border-gray-800 text-center">
              <div className="text-2xl font-bold">{stats.total}</div>
              <div className="text-xs text-gray-500">总操作</div>
            </div>
            <div className="bg-gray-900 rounded-xl p-4 border border-gray-800 text-center">
              <div className={`text-2xl font-bold ${stats.win_rate >= 50 ? "text-up" : "text-down"}`}>
                {stats.win_rate}%
              </div>
              <div className="text-xs text-gray-500">胜率</div>
            </div>
            <div className="bg-gray-900 rounded-xl p-4 border border-gray-800 text-center">
              <div className={`text-2xl font-bold ${stats.avg_pnl >= 0 ? "text-up" : "text-down"}`}>
                {stats.avg_pnl >= 0 ? "+" : ""}{stats.avg_pnl}%
              </div>
              <div className="text-xs text-gray-500">平均盈亏</div>
            </div>
            <div className="bg-gray-900 rounded-xl p-4 border border-gray-800 text-center">
              <div className={`text-2xl font-bold ${stats.total_pnl >= 0 ? "text-up" : "text-down"}`}>
                {stats.total_pnl >= 0 ? "+" : ""}{stats.total_pnl}%
              </div>
              <div className="text-xs text-gray-500">累计盈亏</div>
            </div>
            <div className="bg-gray-900 rounded-xl p-4 border border-gray-800 text-center">
              <div className="text-2xl font-bold">{stats.correct_rate}%</div>
              <div className="text-xs text-gray-500">正确率</div>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
              <h3 className="text-sm font-semibold text-gray-400 mb-2">胜率结构</h3>
              <WinRatePie
                wins={Math.round((stats.win_rate / 100) * stats.total)}
                losses={stats.total - Math.round((stats.win_rate / 100) * stats.total)}
                size={220}
              />
            </div>
            <div className="bg-gray-900 rounded-xl p-4 border border-gray-800 col-span-2">
              <h3 className="text-sm font-semibold text-gray-400 mb-3">按战法统计</h3>
              <div className="grid grid-cols-3 gap-3 text-sm">
                {(stats.by_strategy || []).slice(0, 9).map((s) => (
                  <div key={s.strategy} className="bg-gray-950 border border-gray-800 rounded-lg p-3">
                    <div className="text-xs text-gray-500 mb-1 truncate">{s.strategy}</div>
                    <div className="text-sm">
                      胜率 <span className={s.win_rate >= 50 ? "text-up" : "text-down"}>{s.win_rate}%</span>
                    </div>
                    <div className="text-xs text-gray-500">样本 {s.total} · 均值 {s.avg_pnl}%</div>
                  </div>
                ))}
              </div>
              {(!stats.by_strategy || stats.by_strategy.length === 0) && (
                <div className="text-gray-500 text-center py-10">暂无按战法统计</div>
              )}
            </div>
          </div>

          <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
            <h3 className="text-sm font-semibold text-gray-400 mb-3">按情绪周期统计</h3>
            <div className="grid grid-cols-4 gap-3 text-sm">
              {(stats.by_cycle || []).slice(0, 12).map((c) => (
                <div key={c.cycle} className="bg-gray-950 border border-gray-800 rounded-lg p-3">
                  <div className="text-xs text-gray-500 mb-1">{c.cycle}</div>
                  <div className="text-sm">
                    胜率 <span className={c.win_rate >= 50 ? "text-up" : "text-down"}>{c.win_rate}%</span>
                  </div>
                  <div className="text-xs text-gray-500">样本 {c.total} · 均值 {c.avg_pnl}%</div>
                </div>
              ))}
            </div>
            {(!stats.by_cycle || stats.by_cycle.length === 0) && (
              <div className="text-gray-500 text-center py-10">暂无按周期统计（需要先有情绪周期日志）</div>
            )}
          </div>
        </>
      )}

      {/* 编辑表单 */}
      {editing && (
        <div className="bg-gray-900 rounded-xl p-5 border border-blue-500/30 space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <input
              type="date"
              className="bg-gray-800 rounded-lg px-3 py-2 text-sm"
              value={editing.date || ""}
              onChange={(e) => setEditing({ ...editing, date: e.target.value })}
            />
            <input
              className="bg-gray-800 rounded-lg px-3 py-2 text-sm"
              placeholder="股票代码/名称"
              value={editing.target_stock || ""}
              onChange={(e) => setEditing({ ...editing, target_stock: e.target.value })}
            />
            <select
              className="bg-gray-800 rounded-lg px-3 py-2 text-sm"
              value={editing.action || "买入"}
              onChange={(e) => setEditing({ ...editing, action: e.target.value })}
            >
              <option value="买入">买入</option>
              <option value="卖出">卖出</option>
              <option value="加仓">加仓</option>
              <option value="减仓">减仓</option>
              <option value="观望">观望</option>
            </select>
          </div>
          <div className="grid grid-cols-4 gap-3">
            <input
              type="number"
              step="0.01"
              className="bg-gray-800 rounded-lg px-3 py-2 text-sm"
              placeholder="买入价"
              value={editing.entry_price ?? ""}
              onChange={(e) => setEditing({ ...editing, entry_price: e.target.value ? +e.target.value : null })}
            />
            <input
              type="number"
              step="0.01"
              className="bg-gray-800 rounded-lg px-3 py-2 text-sm"
              placeholder="卖出价"
              value={editing.exit_price ?? ""}
              onChange={(e) => setEditing({ ...editing, exit_price: e.target.value ? +e.target.value : null })}
            />
            <input
              type="number"
              step="0.01"
              className="bg-gray-800 rounded-lg px-3 py-2 text-sm"
              placeholder="盈亏%"
              value={editing.pnl_pct ?? ""}
              onChange={(e) => setEditing({ ...editing, pnl_pct: e.target.value ? +e.target.value : null })}
            />
            <input
              className="bg-gray-800 rounded-lg px-3 py-2 text-sm"
              placeholder="使用战法"
              value={editing.strategy_used || ""}
              onChange={(e) => setEditing({ ...editing, strategy_used: e.target.value })}
            />
          </div>
          <textarea
            className="w-full bg-gray-800 rounded-lg px-3 py-2 text-sm min-h-[60px]"
            placeholder="备注"
            value={editing.note || ""}
            onChange={(e) => setEditing({ ...editing, note: e.target.value })}
          />
          <div className="flex gap-2">
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg"
            >
              {saving ? "保存中..." : "保存"}
            </button>
            <button
              onClick={() => setEditing(null)}
              className="px-4 py-2 text-sm bg-gray-800 hover:bg-gray-700 rounded-lg"
            >
              取消
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <div className="text-gray-500 text-center py-20">加载中...</div>
      ) : records.length === 0 ? (
        <div className="text-gray-500 text-center py-20">
          <p>暂无操作记录</p>
          <p className="text-xs mt-2 text-gray-600">点击"记录操作"添加您的交易记录</p>
        </div>
      ) : (
        <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-500 border-b border-gray-800">
                <th className="text-left px-4 py-3">日期</th>
                <th className="text-left px-4 py-3">标的</th>
                <th className="text-left px-4 py-3">操作</th>
                <th className="text-right px-4 py-3">买入价</th>
                <th className="text-right px-4 py-3">卖出价</th>
                <th className="text-right px-4 py-3">盈亏</th>
                <th className="text-left px-4 py-3">战法</th>
                <th className="text-left px-4 py-3">备注</th>
                <th className="text-center px-4 py-3">操作</th>
              </tr>
            </thead>
            <tbody>
              {records.map((r) => (
                <tr key={r.id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                  <td className="px-4 py-2">{r.date}</td>
                  <td className="px-4 py-2 font-medium">{r.target_stock}</td>
                  <td className="px-4 py-2">{r.action}</td>
                  <td className="px-4 py-2 text-right font-mono">{r.entry_price?.toFixed(2) || "—"}</td>
                  <td className="px-4 py-2 text-right font-mono">{r.exit_price?.toFixed(2) || "—"}</td>
                  <td className={`px-4 py-2 text-right font-mono ${r.pnl_pct != null ? getPctColor(r.pnl_pct) : ""}`}>
                    {r.pnl_pct != null ? formatPct(r.pnl_pct) : "—"}
                  </td>
                  <td className="px-4 py-2 text-gray-400">{r.strategy_used || "—"}</td>
                  <td className="px-4 py-2 text-gray-500 max-w-[200px] truncate">{r.note || "—"}</td>
                  <td className="px-4 py-2 text-center">
                    <div className="flex items-center justify-center gap-1">
                      <button
                        onClick={() => setEditing(r)}
                        className="px-2 py-1 text-xs bg-gray-800 hover:bg-gray-700 rounded"
                      >
                        编辑
                      </button>
                      <button
                        onClick={() => handleDelete(r.id)}
                        className="px-2 py-1 text-xs text-red-400 bg-red-900/30 hover:bg-red-800/30 rounded"
                      >
                        删除
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
