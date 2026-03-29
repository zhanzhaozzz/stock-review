"""每日复盘引擎 — 收集涨停梯队、情绪周期、主线板块等信息，生成复盘报告。

工作流:
  1. 获取涨停梯队数据 (limit_up_tracker)
  2. 获取市场总览快照
  3. 情绪周期判断 (sentiment_engine)
  4. 识别主线板块
  5. 可选: LLM 生成复盘总结
  6. 组装完整复盘结果 → 写入 daily_reviews 表
"""
import json
import logging
from datetime import date
from typing import Optional

from app.config import get_settings
from app.core.sentiment_engine import judge_cycle_with_ai
from app.llm.client import chat

logger = logging.getLogger(__name__)


async def generate_daily_review(
    limit_up_data: dict,
    market_overview: dict = None,
    prev_phases: list[str] = None,
) -> dict:
    """生成当天的复盘报告。"""

    cycle_result = await judge_cycle_with_ai(limit_up_data, market_overview, prev_phases)

    main_sectors = _extract_main_sectors(limit_up_data)
    sub_sectors = _extract_sub_sectors(limit_up_data)
    broken_boards = limit_up_data.get("broken_boards", [])

    summary = ""
    next_day_plan = ""
    try:
        summary, next_day_plan = await _generate_review_summary(
            cycle_result, limit_up_data, market_overview, main_sectors, broken_boards,
        )
    except Exception as e:
        logger.warning("AI review summary failed: %s", e)

    return {
        "date": str(date.today()),
        "market_sentiment": cycle_result.get("phase", "震荡"),
        "sentiment_confidence": cycle_result.get("confidence", 0),
        "market_height": cycle_result.get("height", 0),
        "total_limit_up": cycle_result.get("total_limit_up", 0),
        "first_board_count": cycle_result.get("first_board_count", 0),
        "broken_board_count": cycle_result.get("broken_count", 0),
        "main_sector": ", ".join(main_sectors[:3]) if main_sectors else "",
        "sub_sector": ", ".join(sub_sectors[:3]) if sub_sectors else "",
        "broken_boards": json.dumps(broken_boards[:10], ensure_ascii=False) if broken_boards else "",
        "review_summary": summary,
        "next_day_plan": next_day_plan,
        "applicable_strategy": _recommend_strategy(cycle_result.get("phase", "震荡")),
        "suggested_position": _suggest_position(cycle_result.get("phase", "震荡")),
        "cycle_result": cycle_result,
    }


def _extract_main_sectors(data: dict) -> list[str]:
    """从涨停梯队数据提取主线板块。"""
    sector_count: dict[str, int] = {}
    for item in data.get("ladder", []):
        for stock in item.get("stocks", []):
            sector = stock.get("sector", "")
            if sector:
                sector_count[sector] = sector_count.get(sector, 0) + 1

    sorted_sectors = sorted(sector_count.items(), key=lambda x: x[1], reverse=True)
    return [s[0] for s in sorted_sectors[:5]]


def _extract_sub_sectors(data: dict) -> list[str]:
    """从涨停梯队数据提取支线板块(出现 1 次的)。"""
    sector_count: dict[str, int] = {}
    for item in data.get("ladder", []):
        for stock in item.get("stocks", []):
            sector = stock.get("sector", "")
            if sector:
                sector_count[sector] = sector_count.get(sector, 0) + 1

    sorted_sectors = sorted(sector_count.items(), key=lambda x: x[1], reverse=True)
    main_set = set(s[0] for s in sorted_sectors[:5])
    return [s[0] for s in sorted_sectors if s[0] not in main_set][:5]


def _recommend_strategy(phase: str) -> str:
    """根据情绪周期推荐交易策略。"""
    mapping = {
        "冰点": "低吸 — 重点低位首板、强势股的二次低吸机会",
        "启动": "半路 — 关注卡位股和首板确认的辨识度标的",
        "发酵": "追涨 — 跟随主线龙头，回避杂毛",
        "高潮": "接力高标 — 仅做最高标的接力，严控仓位",
        "高位混沌": "轻仓观望 — 等待方向明确",
        "分歧": "低吸龙头 — 龙头分歧转一致才加仓",
        "退潮": "空仓休息 — 等待冰点信号",
    }
    return mapping.get(phase, "观望 — 等待信号明确")


def _suggest_position(phase: str) -> str:
    """根据情绪周期建议仓位。"""
    mapping = {
        "冰点": "1-2成试探仓",
        "启动": "3成",
        "发酵": "5-7成",
        "高潮": "5成（随时准备减仓）",
        "高位混沌": "3成以下",
        "分歧": "2-3成",
        "退潮": "空仓",
    }
    return mapping.get(phase, "3成")


async def _generate_review_summary(
    cycle: dict,
    limit_up_data: dict,
    market_overview: dict,
    main_sectors: list[str],
    broken_boards: list,
) -> tuple[str, str]:
    """LLM 生成复盘总结和次日计划。"""
    parts = [
        f"情绪周期: {cycle.get('phase', '未知')} (置信度{cycle.get('confidence', 0)}%)",
        f"市场高度: {cycle.get('height', 0)}板",
        f"涨停数: {cycle.get('total_limit_up', 0)}, 首板: {cycle.get('first_board_count', 0)}, 炸板: {cycle.get('broken_count', 0)}",
        f"主线板块: {', '.join(main_sectors[:3]) if main_sectors else '不明确'}",
        f"炸板: {len(broken_boards)}只",
    ]
    if cycle.get("ai_reason"):
        parts.append(f"AI判断: {cycle['ai_reason']}")

    leader = limit_up_data.get("market_leader")
    if leader:
        parts.append(f"龙头: {leader.get('name', '')}({leader.get('board_count', 0)}板)")

    prompt = f"""请根据以下数据生成简洁的每日复盘总结和次日操作计划。

{chr(10).join(parts)}

请输出 JSON（不要输出其他内容）:
{{"summary": "<200字复盘总结>", "plan": "<100字次日操作计划>"}}"""

    settings = get_settings()
    raw = await chat(model=settings.utility_llm_model or "zhipu/glm-4-flash", prompt=prompt, temperature=0.3, timeout=60)
    if raw:
        import re
        match = re.search(r"\{[\s\S]*?\}", raw)
        if match:
            data = json.loads(match.group())
            return data.get("summary", ""), data.get("plan", "")
    return "", ""
