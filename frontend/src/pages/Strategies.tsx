import { useEffect, useState, useCallback } from "react";
import api from "../api/client";

interface StrategyItem {
  id: number;
  name: string;
  applicable_cycles: string[];
  conditions: string;
  entry_rules: string;
  exit_rules: string;
  position_rules: string;
  buy_point_rules: string;
  is_active: boolean;
  sort_order: number;
}

const CYCLE_OPTIONS = ["冰点", "启动", "发酵", "高潮", "高位混沌", "分歧", "退潮"];

export default function Strategies() {
  const [strategies, setStrategies] = useState<StrategyItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<Partial<StrategyItem> | null>(null);
  const [saving, setSaving] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get("/strategies/list");
      setStrategies(res.data || []);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  function handleNew() {
    setEditing({
      name: "",
      applicable_cycles: [],
      conditions: "",
      entry_rules: "",
      exit_rules: "",
      position_rules: "",
      buy_point_rules: "",
    });
  }

  async function handleSave() {
    if (!editing?.name) return;
    setSaving(true);
    try {
      if (editing.id) {
        await api.put(`/strategies/${editing.id}`, editing);
      } else {
        await api.post("/strategies/create", editing);
      }
      setEditing(null);
      await loadData();
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("确认删除?")) return;
    await api.delete(`/strategies/${id}`);
    await loadData();
  }

  function toggleCycle(cycle: string) {
    if (!editing) return;
    const cycles = editing.applicable_cycles || [];
    const next = cycles.includes(cycle) ? cycles.filter((c) => c !== cycle) : [...cycles, cycle];
    setEditing({ ...editing, applicable_cycles: next });
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">战法库</h2>
        <button
          onClick={handleNew}
          className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-500 rounded-lg transition"
        >
          新增战法
        </button>
      </div>

      {/* 编辑弹窗 */}
      {editing && (
        <div className="bg-gray-900 rounded-xl p-5 border border-blue-500/30 space-y-4">
          <input
            className="w-full bg-gray-800 rounded-lg px-3 py-2 text-sm"
            placeholder="战法名称"
            value={editing.name || ""}
            onChange={(e) => setEditing({ ...editing, name: e.target.value })}
          />
          <div>
            <label className="text-xs text-gray-500 block mb-1">适用情绪周期</label>
            <div className="flex flex-wrap gap-2">
              {CYCLE_OPTIONS.map((c) => (
                <button
                  key={c}
                  onClick={() => toggleCycle(c)}
                  className={`px-3 py-1 text-xs rounded-full border transition ${
                    (editing.applicable_cycles || []).includes(c)
                      ? "border-blue-500 bg-blue-500/20 text-blue-300"
                      : "border-gray-700 text-gray-500 hover:border-gray-500"
                  }`}
                >
                  {c}
                </button>
              ))}
            </div>
          </div>
          {[
            { key: "conditions", label: "适用条件" },
            { key: "entry_rules", label: "进场规则" },
            { key: "exit_rules", label: "出场规则" },
            { key: "position_rules", label: "仓位管理" },
            { key: "buy_point_rules", label: "买点描述" },
          ].map((f) => (
            <div key={f.key}>
              <label className="text-xs text-gray-500 block mb-1">{f.label}</label>
              <textarea
                className="w-full bg-gray-800 rounded-lg px-3 py-2 text-sm min-h-[60px]"
                value={(editing as any)[f.key] || ""}
                onChange={(e) => setEditing({ ...editing, [f.key]: e.target.value })}
              />
            </div>
          ))}
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
      ) : strategies.length === 0 ? (
        <div className="text-gray-500 text-center py-20">
          <p>暂无战法</p>
          <p className="text-xs mt-2 text-gray-600">点击"新增战法"添加您的第一个交易策略</p>
        </div>
      ) : (
        <div className="space-y-4">
          {strategies.map((s) => (
            <div key={s.id} className="bg-gray-900 rounded-xl p-5 border border-gray-800">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <h3 className="text-base font-semibold">{s.name}</h3>
                  <div className="flex gap-1">
                    {s.applicable_cycles.map((c) => (
                      <span key={c} className="text-xs px-2 py-0.5 rounded bg-gray-800 text-gray-400">
                        {c}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setEditing(s)}
                    className="px-3 py-1 text-xs bg-gray-800 hover:bg-gray-700 rounded-lg"
                  >
                    编辑
                  </button>
                  <button
                    onClick={() => handleDelete(s.id)}
                    className="px-3 py-1 text-xs bg-red-900/50 hover:bg-red-800/50 text-red-400 rounded-lg"
                  >
                    删除
                  </button>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
                {s.conditions && (
                  <div><span className="text-gray-500">适用条件: </span>{s.conditions}</div>
                )}
                {s.entry_rules && (
                  <div><span className="text-gray-500">进场规则: </span>{s.entry_rules}</div>
                )}
                {s.exit_rules && (
                  <div><span className="text-gray-500">出场规则: </span>{s.exit_rules}</div>
                )}
                {s.position_rules && (
                  <div><span className="text-gray-500">仓位管理: </span>{s.position_rules}</div>
                )}
                {s.buy_point_rules && (
                  <div className="col-span-2"><span className="text-gray-500">买点描述: </span>{s.buy_point_rules}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
