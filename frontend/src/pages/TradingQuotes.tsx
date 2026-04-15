import { useEffect, useState, useCallback } from "react";
import api from "../api/client";

interface QuoteItem {
  id: number;
  date: string;
  content: string;
  created_at: string;
}

export default function TradingQuotes() {
  const [quotes, setQuotes] = useState<QuoteItem[]>([]);
  const [loading, setLoading] = useState(true);

  const [newDate, setNewDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [newContent, setNewContent] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const [editingId, setEditingId] = useState<number | null>(null);
  const [editContent, setEditContent] = useState("");

  const loadQuotes = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get("/quotes/list");
      setQuotes(res.data);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadQuotes();
  }, [loadQuotes]);

  async function handleCreate() {
    if (!newContent.trim()) return;
    setSubmitting(true);
    try {
      await api.post("/quotes/create", { date: newDate, content: newContent.trim() });
      setNewContent("");
      await loadQuotes();
    } finally {
      setSubmitting(false);
    }
  }

  async function handleUpdate(id: number) {
    if (!editContent.trim()) return;
    try {
      await api.put(`/quotes/${id}`, { content: editContent.trim() });
      setEditingId(null);
      setEditContent("");
      await loadQuotes();
    } catch {
      alert("更新失败");
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("确定删除此条语录？")) return;
    try {
      await api.delete(`/quotes/${id}`);
      await loadQuotes();
    } catch {
      alert("删除失败");
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold">交易语录</h2>

      <div className="bg-card rounded-xl p-5 border border-edge space-y-3">
        <h3 className="text-sm font-semibold text-muted">新增语录</h3>
        <div className="flex gap-3">
          <input
            type="date"
            className="bg-input border border-edge rounded-lg px-3 py-2 text-sm w-40"
            value={newDate}
            onChange={(e) => setNewDate(e.target.value)}
          />
          <button
            onClick={handleCreate}
            disabled={submitting || !newContent.trim()}
            className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg transition whitespace-nowrap"
          >
            {submitting ? "添加中..." : "添加"}
          </button>
        </div>
        <textarea
          className="w-full bg-input border border-edge rounded-lg px-3 py-2 text-sm min-h-[80px]"
          value={newContent}
          onChange={(e) => setNewContent(e.target.value)}
          placeholder="记录你的交易心得、规则或感悟..."
        />
      </div>

      {loading ? (
        <div className="text-dim text-center py-20">加载中...</div>
      ) : quotes.length === 0 ? (
        <div className="text-dim text-center py-20">暂无语录，添加一条开始积累吧</div>
      ) : (
        <div className="space-y-3">
          {quotes.map((q) => (
            <div key={q.id} className="bg-card rounded-xl p-5 border border-edge">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="text-xs text-dim mb-2 font-mono">{q.date}</div>
                  {editingId === q.id ? (
                    <div className="space-y-2">
                      <textarea
                        className="w-full bg-input border border-edge rounded-lg px-3 py-2 text-sm min-h-[80px]"
                        value={editContent}
                        onChange={(e) => setEditContent(e.target.value)}
                      />
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleUpdate(q.id)}
                          className="px-3 py-1 text-xs bg-emerald-700 hover:bg-emerald-600 rounded-lg transition"
                        >
                          保存
                        </button>
                        <button
                          onClick={() => { setEditingId(null); setEditContent(""); }}
                          className="px-3 py-1 text-xs bg-input hover:bg-card-hover rounded-lg transition"
                        >
                          取消
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="text-sm text-muted whitespace-pre-line">{q.content}</div>
                  )}
                </div>
                {editingId !== q.id && (
                  <div className="flex gap-1 shrink-0">
                    <button
                      onClick={() => { setEditingId(q.id); setEditContent(q.content); }}
                      className="px-2 py-1 text-xs text-dim hover:text-white bg-input hover:bg-card-hover rounded transition"
                    >
                      编辑
                    </button>
                    <button
                      onClick={() => handleDelete(q.id)}
                      className="px-2 py-1 text-xs text-dim hover:text-red-400 bg-input hover:bg-card-hover rounded transition"
                    >
                      删除
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
