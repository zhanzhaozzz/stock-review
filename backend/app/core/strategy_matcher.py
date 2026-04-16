"""战法匹配引擎 — 根据当前情绪周期自动推荐适用战法。

工作流:
  1. 读取 strategies 表中的活跃战法
  2. 匹配当前情绪周期与战法的 applicable_cycles
  3. 输出: 适用战法列表 + 推荐仓位 + 注意事项
"""
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import normalize_market_phase, normalize_market_phase_list
from app.models.strategy import Strategy

logger = logging.getLogger(__name__)

POSITION_BY_CYCLE = {
    "冰点": "1-2成试探仓",
    "启动": "3成",
    "发酵": "5-7成",
    "高潮": "5成（随时准备减仓）",
    "高位混沌": "3成以下",
    "退潮": "空仓",
}

CAUTION_BY_CYCLE = {
    "冰点": "市场极度低迷，仅做试错，严格止损",
    "启动": "辨识度优先，回避杂毛股",
    "发酵": "跟随主线龙头，不追高位接力",
    "高潮": "只做最高标接力，亏钱效应来临立即撤退",
    "高位混沌": "方向不明，轻仓试错，不恋战",
    "退潮": "空仓休息是最好的策略",
}


async def match_strategies(
    cycle_phase: str,
    db: AsyncSession,
) -> dict:
    """根据情绪周期匹配适用战法。"""
    cycle_phase = normalize_market_phase(cycle_phase)

    stmt = select(Strategy).where(Strategy.is_active == True)
    result = await db.execute(stmt)
    all_strategies = result.scalars().all()

    matched = []
    for s in all_strategies:
        raw_cycles = s.applicable_cycles if isinstance(s.applicable_cycles, list) else []
        cycles = normalize_market_phase_list(raw_cycles)
        if cycle_phase in cycles:
            matched.append({
                "id": s.id,
                "name": s.name,
                "conditions": s.conditions or "",
                "entry_rules": s.entry_rules or "",
                "exit_rules": s.exit_rules or "",
                "position_rules": s.position_rules or "",
                "buy_point_rules": s.buy_point_rules or "",
                "match_reason": f"适用于{cycle_phase}阶段",
            })

    return {
        "cycle_phase": cycle_phase,
        "matched_strategies": matched,
        "suggested_position": POSITION_BY_CYCLE.get(cycle_phase, "3成"),
        "caution": CAUTION_BY_CYCLE.get(cycle_phase, "保持警惕"),
        "total_matched": len(matched),
    }


async def get_recommend_for_review(
    cycle_phase: str,
    db: AsyncSession,
) -> tuple[str, str]:
    """为复盘引擎提供推荐战法名称和仓位。"""
    result = await match_strategies(cycle_phase, db)
    names = [s["name"] for s in result["matched_strategies"]]
    strategy_text = ", ".join(names) if names else CAUTION_BY_CYCLE.get(cycle_phase, "观望")
    position_text = result["suggested_position"]
    return strategy_text, position_text
