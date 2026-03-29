"""情绪周期判断引擎 — 基于涨停梯队数据 + 规则 + AI 辅助推断情绪周期阶段。

情绪周期:
  冰点 → 启动 → 发酵 → 高潮 → (高位混沌) → 分歧 → 退潮 → 冰点

判断依据:
  - 市场高度 (连板层数)
  - 涨停数量
  - 炸板率
  - 龙头状态 (加速/断板)
  - 板块轮动程度
"""
import logging
from typing import Optional

from app.config import get_settings
from app.llm.client import chat

logger = logging.getLogger(__name__)

CYCLE_PHASES = [
    "冰点", "启动", "发酵", "高潮", "高位混沌", "分歧", "退潮",
]


def judge_cycle_by_rules(limit_up_data: dict, prev_phases: list[str] = None) -> dict:
    """基于规则的情绪周期判断。"""
    height = limit_up_data.get("market_height", 0)
    first_board = limit_up_data.get("first_board_count", 0)
    broken = len(limit_up_data.get("broken_boards", []))
    ladder = limit_up_data.get("ladder", [])

    total_zt = sum(l.get("count", 0) for l in ladder)
    high_board_count = sum(1 for l in ladder if l.get("level", 0) >= 3)

    prev = prev_phases[-1] if prev_phases else None
    confidence = 50

    if total_zt <= 20 and height <= 2:
        phase = "冰点"
        confidence = 75
    elif total_zt >= 80 and height >= 5 and high_board_count >= 3:
        phase = "高潮"
        confidence = 70
    elif height >= 4 and total_zt >= 50 and broken <= 3:
        phase = "发酵"
        confidence = 60
    elif prev in ("冰点", None) and total_zt >= 30 and height >= 3:
        phase = "启动"
        confidence = 55
    elif prev in ("高潮", "高位混沌") and broken >= 5:
        phase = "分歧"
        confidence = 65
    elif prev in ("高潮", "高位混沌") and total_zt < 50 and broken <= 2:
        phase = "高位混沌"
        confidence = 50
    elif prev in ("分歧",) and total_zt < 30:
        phase = "退潮"
        confidence = 60
    elif prev in ("分歧",) and total_zt >= 40:
        phase = "发酵"
        confidence = 45
    else:
        phase = prev or "震荡"
        confidence = 35

    return {
        "phase": phase,
        "confidence": confidence,
        "height": height,
        "total_limit_up": total_zt,
        "first_board_count": first_board,
        "broken_count": broken,
        "high_board_count": high_board_count,
        "method": "rules",
    }


async def judge_cycle_with_ai(
    limit_up_data: dict,
    market_overview: dict = None,
    prev_phases: list[str] = None,
) -> dict:
    """AI 辅助情绪周期判断: 先跑规则，再让 AI 校正。"""
    rule_result = judge_cycle_by_rules(limit_up_data, prev_phases)

    context_parts = [
        f"市场高度: {rule_result['height']}板",
        f"涨停数: {rule_result['total_limit_up']}",
        f"首板数: {rule_result['first_board_count']}",
        f"炸板数: {rule_result['broken_count']}",
        f"3板以上股票: {rule_result['high_board_count']}只",
        f"规则判断: {rule_result['phase']} (置信度{rule_result['confidence']}%)",
    ]

    if prev_phases:
        context_parts.append(f"前几日情绪: {' → '.join(prev_phases[-5:])}")

    leader = limit_up_data.get("market_leader")
    if leader:
        context_parts.append(f"市场龙头: {leader.get('name', '')}({leader.get('board_count', 0)}板)")

    if market_overview:
        breadth = market_overview.get("breadth", {})
        if breadth:
            context_parts.append(f"涨跌面: 涨{breadth.get('up', 0)} 跌{breadth.get('down', 0)} 平{breadth.get('flat', 0)}")

    prompt = f"""请根据以下市场数据判断当前的情绪周期阶段。

{chr(10).join(context_parts)}

情绪周期阶段（只能选一个）:
冰点 / 启动 / 发酵 / 高潮 / 高位混沌 / 分歧 / 退潮

请输出 JSON（不要输出其他内容）:
{{"phase": "<阶段>", "confidence": <0-100置信度>, "reason": "<50字判断依据>"}}"""

    settings = get_settings()
    model = settings.utility_llm_model or "zhipu/glm-4-flash"

    try:
        raw = await chat(model=model, prompt=prompt, temperature=0.1, timeout=30)
        if raw:
            import json, re
            text = raw.strip()
            match = re.search(r"\{[\s\S]*?\}", text)
            if match:
                data = json.loads(match.group())
                if "phase" in data and data["phase"] in CYCLE_PHASES:
                    return {
                        **rule_result,
                        "phase": data["phase"],
                        "confidence": data.get("confidence", 60),
                        "ai_reason": data.get("reason", ""),
                        "method": "ai",
                    }
    except Exception as e:
        logger.warning("AI sentiment judge failed: %s", e)

    return rule_result
