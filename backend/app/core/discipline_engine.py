"""V1 纪律门控引擎 — 给候选池做显式规则门控。

本阶段先写死简单规则，不做自动学习。
"""
import logging

from app.models.market_state import MarketStateDaily
from app.schemas.candidate_pool import CandidatePoolEntryCreate

logger = logging.getLogger(__name__)


def evaluate(
    candidate: CandidatePoolEntryCreate,
    market_state: MarketStateDaily | None,
) -> dict:
    """返回 gate_status / gate_reason / action_hint。

    规则（Phase 1 硬编码）：
    - 市场温度 >= 80 且来源非梯队 → 拦截
    - 市场温度 >= 60 → 观察
    - 其余 → 通过
    """
    gate_status = "通过"
    gate_reason = "默认通过"
    action_hint = "重点跟踪"

    if market_state and market_state.temperature_score is not None:
        temp = market_state.temperature_score
        if temp >= 80 and candidate.source_type != "梯队":
            gate_status = "拦截"
            gate_reason = f"市场温度 {temp} 过高，非梯队来源风险大"
            action_hint = "放弃"
        elif temp >= 60:
            gate_status = "观察"
            gate_reason = f"市场温度 {temp} 偏高，需谨慎"
            action_hint = "观察等待"

    if market_state and market_state.market_phase == "退潮":
        gate_status = "拦截"
        gate_reason = "市场处于退潮阶段，整体不宜进场"
        action_hint = "放弃"

    return {
        "gate_status": gate_status,
        "gate_reason": gate_reason,
        "action_hint": action_hint,
    }
