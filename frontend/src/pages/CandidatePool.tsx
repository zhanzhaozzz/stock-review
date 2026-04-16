import { useState, useMemo } from "react";
import { useCandidates, useUpdateCandidate } from "../hooks/useCombatData";
import type { CandidatePoolEntry } from "../hooks/useCombatData";

const GATE_FILTERS = ["通过", "观察", "拦截"] as const;

const gateColors: Record<string, string> = {
  "通过": "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
  "观察": "text-yellow-400 bg-yellow-500/10 border-yellow-500/30",
  "拦截": "text-red-400 bg-red-500/10 border-red-500/30",
};

const sourceColors: Record<string, string> = {
  "梯队": "text-blue-300 bg-blue-500/10",
  "事件": "text-purple-300 bg-purple-500/10",
  "观察池": "text-cyan-300 bg-cyan-500/10",
};

const outcomeOptions = [
  { value: "逻辑兑现", label: "逻辑兑现", color: "bg-emerald-600 hover:bg-emerald-500" },
  { value: "时机未到", label: "时机未到", color: "bg-yellow-600 hover:bg-yellow-500" },
  { value: "逻辑证伪", label: "逻辑证伪", color: "bg-red-600 hover:bg-red-500" },
  { value: "纪律拦截正确", label: "纪律拦截正确", color: "bg-blue-600 hover:bg-blue-500" },
] as const;

function renderListItems(items: unknown[] | null | undefined): string[] {
  if (!items) return [];
  if (!Array.isArray(items)) return [String(items)];
  return items.map((item) => (typeof item === "string" ? item : JSON.stringify(item)));
}

function CandidateCard({
  entry,
  expanded,
  onToggle,
}: {
  entry: CandidatePoolEntry;
  expanded: boolean;
  onToggle: () => void;
}) {
  const updateMutation = useUpdateCandidate();
  const [editingNote, setEditingNote] = useState(false);
  const [noteValue, setNoteValue] = useState(entry.review_note || "");

  const riskItems = renderListItems(entry.risk_flags);

  function handleOutcome(outcome: string) {
    updateMutation.mutate({ id: entry.id, data: { review_outcome: outcome } });
  }

  function handleSaveNote() {
    updateMutation.mutate({ id: entry.id, data: { review_note: noteValue } });
    setEditingNote(false);
  }

  return (
    <div className="bg-card rounded-xl border border-edge">
      {/* 卡片头部 - 可点击展开 */}
      <div className="p-4 cursor-pointer" onClick={onToggle}>
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="font-medium">{entry.name}</span>
            <span className="text-xs text-dim font-mono">{entry.code}</span>
            {entry.source_type && (
              <span className={`text-xs px-1.5 py-0.5 rounded ${sourceColors[entry.source_type] || "bg-badge text-dim"}`}>
                {entry.source_type}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {entry.gate_status && (
              <span className={`text-xs px-2 py-0.5 rounded-full border ${gateColors[entry.gate_status] || "border-edge text-muted"}`}>
                {entry.gate_status}
              </span>
            )}
            {entry.action_hint && (
              <span className="text-xs px-2 py-0.5 rounded bg-badge text-dim">
                {entry.action_hint}
              </span>
            )}
            <span className="text-xs text-dim">{expanded ? "▼" : "▶"}</span>
          </div>
        </div>

        {entry.theme && (
          <div className="mb-1.5">
            <span className="text-xs px-1.5 py-0.5 rounded bg-badge text-muted">{entry.theme}</span>
          </div>
        )}

        {entry.thesis && (
          <div className={`text-sm text-secondary ${expanded ? "" : "line-clamp-2"}`}>{entry.thesis}</div>
        )}
      </div>

      {/* 展开详情 */}
      {expanded && (
        <div className="border-t border-edge px-4 py-3 space-y-3">
          {entry.gate_reason && (
            <div>
              <div className="text-xs text-dim mb-1">门控理由</div>
              <div className="text-sm text-secondary">{entry.gate_reason}</div>
            </div>
          )}

          {entry.source_reason && (
            <div>
              <div className="text-xs text-dim mb-1">来源理由</div>
              <div className="text-sm text-secondary">{entry.source_reason}</div>
            </div>
          )}

          {riskItems.length > 0 && (
            <div>
              <div className="text-xs text-dim mb-1">风险标签</div>
              <div className="flex flex-wrap gap-1.5">
                {riskItems.map((r, i) => (
                  <span key={i} className="text-xs px-2 py-0.5 rounded bg-red-500/10 text-red-300 border border-red-500/20">
                    {r}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* 当前复盘状态 */}
          <div>
            <div className="text-xs text-dim mb-1">复盘状态</div>
            <span className="text-sm text-muted">{entry.review_outcome || "待复盘"}</span>
          </div>

          {/* 复盘备注 */}
          <div>
            <div className="text-xs text-dim mb-1">复盘备注</div>
            {editingNote ? (
              <div className="flex gap-2">
                <input
                  className="flex-1 bg-input border border-edge rounded-lg px-3 py-1.5 text-sm"
                  value={noteValue}
                  onChange={(e) => setNoteValue(e.target.value)}
                  placeholder="输入复盘备注..."
                  autoFocus
                />
                <button
                  onClick={handleSaveNote}
                  disabled={updateMutation.isPending}
                  className="px-3 py-1.5 text-xs bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg transition"
                >
                  保存
                </button>
                <button
                  onClick={() => { setEditingNote(false); setNoteValue(entry.review_note || ""); }}
                  className="px-3 py-1.5 text-xs bg-input hover:bg-card-hover rounded-lg transition"
                >
                  取消
                </button>
              </div>
            ) : (
              <div
                className="text-sm text-muted cursor-pointer hover:text-primary transition"
                onClick={() => setEditingNote(true)}
              >
                {entry.review_note || "点击添加备注..."}
              </div>
            )}
          </div>

          {/* 操作按钮 */}
          <div className="flex flex-wrap gap-2 pt-1">
            {outcomeOptions.map((opt) => (
              <button
                key={opt.value}
                onClick={() => handleOutcome(opt.value)}
                disabled={updateMutation.isPending || entry.review_outcome === opt.value}
                className={`px-3 py-1.5 text-xs rounded-lg transition disabled:opacity-40 ${
                  entry.review_outcome === opt.value
                    ? "ring-2 ring-white/30 " + opt.color
                    : opt.color
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function CandidatePool() {
  const { data: candidates = [], isLoading } = useCandidates();
  const [activeFilters, setActiveFilters] = useState<Set<string>>(new Set(["通过", "观察"]));
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const counts = useMemo(() => {
    const map: Record<string, number> = { "通过": 0, "观察": 0, "拦截": 0 };
    for (const c of candidates) {
      const status = c.gate_status || "观察";
      if (status in map) map[status]++;
    }
    return map;
  }, [candidates]);

  const filtered = useMemo(() => {
    if (activeFilters.size === 0) return candidates;
    return candidates.filter((c) => activeFilters.has(c.gate_status || "观察"));
  }, [candidates, activeFilters]);

  function toggleFilter(f: string) {
    setActiveFilters((prev) => {
      const next = new Set(prev);
      if (next.has(f)) {
        next.delete(f);
      } else {
        next.add(f);
      }
      return next;
    });
  }

  if (isLoading) {
    return <div className="text-dim text-center py-20">加载中...</div>;
  }

  return (
    <div className="space-y-5">
      <h2 className="text-xl font-bold">候选池</h2>

      {/* Block 1: 状态过滤器 */}
      <div className="flex items-center gap-2">
        {GATE_FILTERS.map((f) => {
          const active = activeFilters.has(f);
          return (
            <button
              key={f}
              onClick={() => toggleFilter(f)}
              className={`px-4 py-2 text-sm rounded-lg border transition ${
                active
                  ? gateColors[f] + " border-current"
                  : "border-edge text-dim hover:text-muted hover:border-edge"
              }`}
            >
              {f}
              <span className="ml-1.5 text-xs opacity-70">{counts[f]}</span>
            </button>
          );
        })}
        <span className="text-xs text-dim ml-3">共 {candidates.length} 只候选</span>
      </div>

      {/* Block 2: 候选卡片流 */}
      {filtered.length === 0 ? (
        <div className="text-dim text-center py-16">
          <p>当前筛选条件下暂无候选标的</p>
          {candidates.length === 0 && (
            <p className="text-xs mt-2">今日候选池尚未生成，请先在后端执行生成任务</p>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((entry) => (
            <CandidateCard
              key={entry.id}
              entry={entry}
              expanded={expandedId === entry.id}
              onToggle={() => setExpandedId(expandedId === entry.id ? null : entry.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
