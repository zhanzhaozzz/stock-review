"""V1 PostMarketReview 服务层。"""
import json
import logging
import re
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review_outcome import PostMarketReview
from app.schemas.review_outcome import PostMarketReviewCreate, PostMarketReviewUpdate

logger = logging.getLogger(__name__)


async def get_by_date(db: AsyncSession, target_date: date) -> PostMarketReview | None:
    result = await db.execute(
        select(PostMarketReview).where(PostMarketReview.date == target_date)
    )
    return result.scalar_one_or_none()


async def create_or_update(
    db: AsyncSession, data: PostMarketReviewCreate
) -> PostMarketReview:
    existing = await get_by_date(db, data.date)
    if existing:
        for field, value in data.model_dump(exclude_unset=True, exclude={"date"}).items():
            setattr(existing, field, value)
        await db.commit()
        await db.refresh(existing)
        return existing

    record = PostMarketReview(**data.model_dump(exclude_unset=True))
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def run_review(db: AsyncSession, target_date: date) -> PostMarketReview:
    """消费当天 BattleBrief + MarketStateDaily + CandidatePoolEntry 生成盘后复盘。

    幂等：同日已存在则覆盖更新。
    依赖约束：必须先有 CandidatePoolEntry.review_outcome 回填结果。
    """
    logger.info("[PostMarketReview] 开始生成 date=%s", target_date)

    from app.core import market_state_service, battle_brief_service, candidate_pool_service
    from app.config import get_settings
    from app.llm.client import chat
    from app.llm.prompts.post_market_review import (
        POST_MARKET_REVIEW_SYSTEM_PROMPT,
        build_post_market_review_prompt,
    )

    market_state = await market_state_service.get_by_date(db, target_date)
    battle_brief = await battle_brief_service.get_by_date(db, target_date)
    candidates = await candidate_pool_service.list_by_date(db, target_date)

    ms_context = {}
    if market_state:
        ms_context = {
            "market_phase": market_state.market_phase,
            "temperature_score": market_state.temperature_score,
            "style_tag": market_state.style_tag,
            "limit_up_count": market_state.limit_up_count,
            "boom_rate": market_state.boom_rate,
            "highest_ladder": market_state.highest_ladder,
            "conclusion": market_state.conclusion,
        }
        logger.info("[PostMarketReview] MarketStateDaily 已加载")
    else:
        logger.warning("[PostMarketReview] 当日无 MarketStateDaily")

    bb_context = {}
    if battle_brief:
        bb_context = {
            "status_tone": battle_brief.status_tone,
            "suggested_position": battle_brief.suggested_position,
            "overall_conclusion": battle_brief.overall_conclusion,
            "bullish_sectors": battle_brief.bullish_sectors,
            "bearish_sectors": battle_brief.bearish_sectors,
        }
        logger.info("[PostMarketReview] BattleBrief 已加载")
    else:
        logger.warning("[PostMarketReview] 当日无 BattleBrief")

    candidate_summary = []
    outcome_stats = {"逻辑兑现": 0, "时机未到": 0, "逻辑证伪": 0, "纪律拦截正确": 0, "待复盘": 0}
    for c in candidates:
        outcome = c.review_outcome or "待复盘"
        outcome_stats[outcome] = outcome_stats.get(outcome, 0) + 1
        candidate_summary.append({
            "code": c.code,
            "name": c.name,
            "source_type": c.source_type,
            "gate_status": c.gate_status,
            "review_outcome": outcome,
            "review_note": c.review_note,
        })
    logger.info("[PostMarketReview] 候选池条目: %d, 验证分布: %s", len(candidates), outcome_stats)

    context = {
        "target_date": str(target_date),
        "market_state": ms_context,
        "battle_brief": bb_context,
        "candidates": candidate_summary[:20],
        "outcome_stats": outcome_stats,
    }

    settings = get_settings()
    model = settings.analysis_llm_model or settings.utility_llm_model or "zhipu/glm-4-flash"

    raw = await chat(
        model=model,
        prompt=build_post_market_review_prompt(context),
        system=POST_MARKET_REVIEW_SYSTEM_PROMPT,
        temperature=0.3,
        timeout=60,
    )

    llm_output = _parse_llm_json(raw)

    _GRADE_VALID = {"成功", "部分成功", "失败"}
    brief_grade = llm_output.get("brief_grade", "")
    if brief_grade not in _GRADE_VALID:
        brief_grade = _fallback_grade(outcome_stats)

    data = PostMarketReviewCreate(
        date=target_date,
        brief_grade=brief_grade,
        grade_reason=llm_output.get("grade_reason", ""),
        actual_market_trend=llm_output.get("actual_market_trend", ""),
        carry_over_themes=llm_output.get("carry_over_themes", []),
        next_day_seeds=llm_output.get("next_day_seeds", []),
        eliminated_directions=llm_output.get("eliminated_directions", []),
    )

    result = await create_or_update(db, data)
    logger.info("[PostMarketReview] 生成完成 date=%s grade=%s", target_date, brief_grade)
    return result


def _parse_llm_json(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        matched = re.search(r"\{[\s\S]*\}", raw)
        if matched:
            data = json.loads(matched.group())
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def _fallback_grade(outcome_stats: dict) -> str:
    total = sum(outcome_stats.values())
    if total == 0:
        return "部分成功"
    good = outcome_stats.get("逻辑兑现", 0) + outcome_stats.get("纪律拦截正确", 0)
    if good / total >= 0.6:
        return "成功"
    if good / total >= 0.3:
        return "部分成功"
    return "失败"
