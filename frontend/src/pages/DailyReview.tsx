import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useCombatDesk, useCandidates, usePostMarketReview, useUpdateCandidate } from "../hooks/useCombatData";
import type { BattleBrief, PostMarketReview, CandidatePoolEntry } from "../hooks/useCombatData";

const toneColors: Record<string, string> = {
  "可做": "border-emerald-500/30 bg-emerald-500/5 text-emerald-400",
  "轻仓试错": "border-yellow-500/30 bg-yellow-500/5 text-yellow-400",
  "防守观察": "border-orange-500/30 bg-orange-500/5 text-orange-400",
  "不做": "border-red-500/30 bg-red-500/5 text-red-400",
};

const gradeColors: Record<string, string> = {
  "成功": "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
  "部分成功": "text-yellow-400 bg-yellow-500/10 border-yellow-500/30",
  "失败": "text-red-400 bg-red-500/10 border-red-500/30",
};

const outcomeColors: Record<string, string> = {
  "逻辑兑现": "text-emerald-400",
  "时机未到": "text-yellow-400",
  "逻辑证伪": "text-red-400",
  "纪律拦截正确": "text-blue-400",
  "待复盘": "text-dim",
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

function JudgmentReplayBlock({ brief }: { brief: BattleBrief | null }) {
  if (!brief) {
    return (
      <div className="bg-card rounded-xl p-5 border border-edge">
        <h3 className="text-sm font-semibold text-muted mb-3">今日判断回放</h3>
        <div className="text-sm text-dim text-center py-6">今日作战简报尚未生成</div>
      </div>
    );
  }

  const toneCls = brief.status_tone ? (toneColors[brief.status_tone] || "border-edge bg-card") : "border-edge bg-card";
  const narratives = renderListItems(brief.main_narrative);
  const risks = renderListItems(brief.risk_tips);

  return (
    <div className={`rounded-xl p-5 border ${toneCls}`}>
      <h3 className="text-sm font-semibold mb-3">今日判断回放</h3>
      <div className="space-y-3">
        <div className="flex items-center gap-3">
          <span className="text-lg font-bold">{brief.status_tone || "--"}</span>
          {brief.suggested_position && (
            <span className="text-xs px-2 py-0.5 rounded bg-card border border-edge text-muted">
              仓位: {brief.suggested_position}
            </span>
          )}
        </div>
        {brief.overall_conclusion && (
          <div className="text-sm text-secondary">{brief.overall_conclusion}</div>
        )}
        {narratives.length > 0 && (
          <div>
            <div className="text-xs text-dim mb-1">早盘主叙事</div>
            <div className="text-sm text-secondary space-y-0.5">
              {narratives.map((n, i) => <div key={i}>• {n}</div>)}
            </div>
          </div>
        )}
        {risks.length > 0 && (
          <div>
            <div className="text-xs text-dim mb-1">早盘风险提示</div>
            <div className="text-sm text-yellow-300 space-y-0.5">
              {risks.map((r, i) => <div key={i}>• {r}</div>)}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function MarketResultBlock({ brief, review }: { brief: BattleBrief | null; review: PostMarketReview | null }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* 左：早盘判断 */}
      <div className="bg-card rounded-xl p-5 border border-edge">
        <h3 className="text-sm font-semibold text-muted mb-3">早盘判断</h3>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-dim">定调</span>
            <span className="text-secondary">{brief?.status_tone || "--"}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-dim">仓位建议</span>
            <span className="text-secondary">{brief?.suggested_position || "--"}</span>
          </div>
          {brief?.overall_conclusion && (
            <div className="pt-2 border-t border-edge-light">
              <div className="text-xs text-dim mb-1">结论</div>
              <div className="text-secondary">{brief.overall_conclusion}</div>
            </div>
          )}
        </div>
      </div>

      {/* 右：实际结果 */}
      <div className="bg-card rounded-xl p-5 border border-edge">
        <h3 className="text-sm font-semibold text-muted mb-3">实际结果</h3>
        {review ? (
          <div className="space-y-2 text-sm">
            <div className="flex justify-between items-center">
              <span className="text-dim">简报评分</span>
              {review.brief_grade && (
                <span className={`text-xs px-2 py-0.5 rounded-full border ${gradeColors[review.brief_grade] || "border-edge text-muted"}`}>
                  {review.brief_grade}
                </span>
              )}
            </div>
            {review.grade_reason && (
              <div className="pt-2 border-t border-edge-light">
                <div className="text-xs text-dim mb-1">评分理由</div>
                <div className="text-secondary">{review.grade_reason}</div>
              </div>
            )}
            {review.actual_market_trend && (
              <div className="pt-2 border-t border-edge-light">
                <div className="text-xs text-dim mb-1">实际市场走向</div>
                <div className="text-secondary">{review.actual_market_trend}</div>
              </div>
            )}
          </div>
        ) : (
          <div className="text-sm text-dim text-center py-6">盘后复盘尚未生成</div>
        )}
      </div>
    </div>
  );
}

function CandidateVerifyCard({ entry }: { entry: CandidatePoolEntry }) {
  const updateMutation = useUpdateCandidate();
  const [editingNote, setEditingNote] = useState(false);
  const [noteValue, setNoteValue] = useState(entry.review_note || "");

  const outcomeCls = outcomeColors[entry.review_outcome || "待复盘"] || "text-dim";

  function handleOutcome(outcome: string) {
    updateMutation.mutate({ id: entry.id, data: { review_outcome: outcome } });
  }

  function handleSaveNote() {
    updateMutation.mutate({ id: entry.id, data: { review_note: noteValue } });
    setEditingNote(false);
  }

  return (
    <div className="bg-card rounded-xl p-4 border border-edge">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="font-medium text-sm">{entry.name}</span>
          <span className="text-xs text-dim font-mono">{entry.code}</span>
          {entry.theme && (
            <span className="text-xs px-1.5 py-0.5 rounded bg-badge text-dim">{entry.theme}</span>
          )}
        </div>
        <span className={`text-sm font-medium ${outcomeCls}`}>
          {entry.review_outcome || "待复盘"}
        </span>
      </div>

      {entry.thesis && (
        <div className="text-xs text-dim mb-2">{entry.thesis}</div>
      )}

      {/* 复盘备注 */}
      <div className="mb-2">
        {editingNote ? (
          <div className="flex gap-2">
            <input
              className="flex-1 bg-input border border-edge rounded-lg px-3 py-1.5 text-sm"
              value={noteValue}
              onChange={(e) => setNoteValue(e.target.value)}
              placeholder="一句归因说明..."
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
            className="text-xs text-muted cursor-pointer hover:text-primary transition"
            onClick={() => setEditingNote(true)}
          >
            {entry.review_note || "点击添加归因说明..."}
          </div>
        )}
      </div>

      {/* 快速标记按钮 */}
      <div className="flex flex-wrap gap-1.5">
        {outcomeOptions.map((opt) => (
          <button
            key={opt.value}
            onClick={() => handleOutcome(opt.value)}
            disabled={updateMutation.isPending || entry.review_outcome === opt.value}
            className={`px-2.5 py-1 text-xs rounded-lg transition disabled:opacity-40 ${
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
  );
}

function CandidateVerifyBlock({ candidates }: { candidates: CandidatePoolEntry[] }) {
  return (
    <div className="bg-card rounded-xl border border-edge">
      <div className="px-5 py-3 border-b border-edge">
        <h3 className="text-sm font-semibold text-muted">候选池验证</h3>
      </div>
      {candidates.length === 0 ? (
        <div className="text-sm text-dim text-center py-8">今日暂无候选标的需要验证</div>
      ) : (
        <div className="p-4 space-y-3">
          {candidates.map((entry) => (
            <CandidateVerifyCard key={entry.id} entry={entry} />
          ))}
        </div>
      )}
    </div>
  );
}

function NextDayBlock({ review }: { review: PostMarketReview | null }) {
  if (!review) {
    return (
      <div className="bg-card rounded-xl p-5 border border-edge">
        <h3 className="text-sm font-semibold text-muted mb-3">明日承接</h3>
        <div className="text-sm text-dim text-center py-6">盘后复盘尚未生成</div>
      </div>
    );
  }

  const carryThemes = renderListItems(review.carry_over_themes);
  const seeds = renderListItems(review.next_day_seeds);
  const eliminated = renderListItems(review.eliminated_directions);

  const hasContent = carryThemes.length > 0 || seeds.length > 0 || eliminated.length > 0;

  return (
    <div className="bg-card rounded-xl p-5 border border-edge">
      <h3 className="text-sm font-semibold text-muted mb-4">明日承接</h3>
      {hasContent ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <div className="text-xs text-dim mb-2">带走的主题</div>
            {carryThemes.length > 0 ? (
              <div className="space-y-1">
                {carryThemes.map((t, i) => (
                  <div key={i} className="text-sm px-2 py-1 rounded bg-emerald-500/10 text-emerald-300">
                    {t}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-dim">--</div>
            )}
          </div>
          <div>
            <div className="text-xs text-dim mb-2">明日种子</div>
            {seeds.length > 0 ? (
              <div className="space-y-1">
                {seeds.map((s, i) => (
                  <div key={i} className="text-sm px-2 py-1 rounded bg-blue-500/10 text-blue-300">
                    {s}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-dim">--</div>
            )}
          </div>
          <div>
            <div className="text-xs text-dim mb-2">剔除的方向</div>
            {eliminated.length > 0 ? (
              <div className="space-y-1">
                {eliminated.map((e, i) => (
                  <div key={i} className="text-sm px-2 py-1 rounded bg-red-500/10 text-red-300">
                    {e}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-dim">--</div>
            )}
          </div>
        </div>
      ) : (
        <div className="text-sm text-dim text-center py-4">暂无明日承接内容</div>
      )}
    </div>
  );
}

export default function DailyReview() {
  const [searchParams] = useSearchParams();
  const dateParam = searchParams.get("date");
  const isHistoryMode = !!dateParam;

  const { data: combatData, isLoading: loadingCombat } = useCombatDesk();
  const { data: candidates = [], isLoading: loadingCandidates } = useCandidates();
  const { data: postReview, isLoading: loadingReview } = usePostMarketReview();

  const loading = loadingCombat || loadingCandidates || loadingReview;
  const brief = combatData?.battle_brief ?? null;

  if (isHistoryMode) {
    return (
      <div className="space-y-5">
        <h2 className="text-xl font-bold">盘后复盘（历史：{dateParam}）</h2>
        <div className="bg-card rounded-xl p-8 border border-edge text-center">
          <p className="text-muted">V1 暂不支持按日期查看历史盘后复盘</p>
          <p className="text-xs text-dim mt-2">请通过"历史复盘"页面查看旧格式复盘记录</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return <div className="text-dim text-center py-20">加载中...</div>;
  }

  return (
    <div className="space-y-5">
      <h2 className="text-xl font-bold">盘后复盘</h2>

      <JudgmentReplayBlock brief={brief} />
      <MarketResultBlock brief={brief} review={postReview ?? null} />
      <CandidateVerifyBlock candidates={candidates} />
      <NextDayBlock review={postReview ?? null} />
    </div>
  );
}
