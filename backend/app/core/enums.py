"""V1 统一枚举定义。

Phase 0 规范：全系统只保留一套规范词，不再使用带"期"后缀的展示词。
"""

# ── 市场阶段（6 项规范词）──────────────────────────────
MARKET_PHASES = ["冰点", "启动", "发酵", "高潮", "高位混沌", "退潮"]

CYCLE_PHASES = MARKET_PHASES

# ── 四象限 ──────────────────────────────────────────
QUADRANTS = ["情指共振", "情好指差", "情差指好", "情指双杀"]

# ── 战法 ────────────────────────────────────────────
STRATEGIES = ["擒龙", "补涨套利", "缠龙低吸", "试错轻仓"]

# ── V1 新增规范常量 ─────────────────────────────────
STYLE_TAGS = ["接力优先", "趋势优先", "轮动试错", "防守观察"]
STATUS_TONES = ["可做", "轻仓试错", "防守观察", "不做"]
SOURCE_TYPES = ["梯队", "事件", "观察池"]
GATE_STATUSES = ["通过", "观察", "拦截"]
ACTION_HINTS = ["重点跟踪", "轻仓试错", "观察等待", "放弃"]
REVIEW_OUTCOMES = ["待复盘", "逻辑兑现", "时机未到", "逻辑证伪", "纪律拦截正确"]
BRIEF_GRADES = ["成功", "部分成功", "失败"]

# ── 旧词 → 规范词映射 ──────────────────────────────
_PHASE_ALIAS: dict[str, str] = {
    "低位混沌": "冰点",
    "低位混沌期": "冰点",
    "启动期": "启动",
    "上升期": "发酵",
    "发酵期": "发酵",
    "高潮期": "高潮",
    "高位混沌期": "高位混沌",
    "分歧": "高位混沌",
    "高位震荡": "高位混沌",
    "退潮期": "退潮",
}

_PHASE_EXPAND: dict[str, list[str]] = {
    "上升期": ["启动", "发酵", "高潮"],
}

_VALID_PHASES = set(MARKET_PHASES)


def normalize_market_phase(raw: str) -> str:
    """将旧阶段词规范化为 MARKET_PHASES 中的值。无法识别时返回原值。"""
    if not raw:
        return raw
    s = raw.strip()
    if s in _VALID_PHASES:
        return s
    return _PHASE_ALIAS.get(s, s)


def normalize_market_phase_list(raw_list: list[str]) -> list[str]:
    """将旧阶段词列表规范化：展开 '上升期'，去重，保序，只保留规范词。"""
    if not raw_list:
        return []
    result: list[str] = []
    seen: set[str] = set()
    for item in raw_list:
        s = item.strip() if isinstance(item, str) else str(item)
        if s in _PHASE_EXPAND:
            expanded = _PHASE_EXPAND[s]
        else:
            expanded = [normalize_market_phase(s)]
        for phase in expanded:
            if phase in _VALID_PHASES and phase not in seen:
                seen.add(phase)
                result.append(phase)
    return result
