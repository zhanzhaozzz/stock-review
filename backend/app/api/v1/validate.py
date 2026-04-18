"""Phase 4 数据完整性验证 API — 检查 V1 四对象当日产物。"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core import (
    market_state_service,
    battle_brief_service,
    candidate_pool_service,
    post_market_review_service,
)

router = APIRouter()


@router.get("/v1-status")
async def validate_v1_status(
    target_date: Optional[str] = Query(None, alias="date", description="YYYY-MM-DD，默认今天"),
    db: AsyncSession = Depends(get_db),
):
    """检查 V1 四对象在指定日期的数据完整性，输出验证报告。"""
    d = date.fromisoformat(target_date) if target_date else date.today()

    market_state = await market_state_service.get_by_date(db, d)
    battle_brief = await battle_brief_service.get_by_date(db, d)
    candidates = await candidate_pool_service.list_by_date(db, d)
    post_review = await post_market_review_service.get_by_date(db, d)

    candidate_count = len(candidates)
    gate_stats: dict[str, int] = {}
    outcome_stats: dict[str, int] = {}
    for c in candidates:
        gs = c.gate_status or "未知"
        gate_stats[gs] = gate_stats.get(gs, 0) + 1
        oc = c.review_outcome or "待复盘"
        outcome_stats[oc] = outcome_stats.get(oc, 0) + 1

    checks = {
        "market_state_daily": {
            "exists": market_state is not None,
            "date": str(market_state.date) if market_state else None,
            "market_phase": market_state.market_phase if market_state else None,
            "temperature_score": market_state.temperature_score if market_state else None,
            "style_tag": market_state.style_tag if market_state else None,
        },
        "battle_brief": {
            "exists": battle_brief is not None,
            "date": str(battle_brief.date) if battle_brief else None,
            "status_tone": battle_brief.status_tone if battle_brief else None,
            "suggested_position": battle_brief.suggested_position if battle_brief else None,
            "has_conclusion": bool(battle_brief.overall_conclusion) if battle_brief else False,
        },
        "candidate_pool": {
            "exists": candidate_count > 0,
            "count": candidate_count,
            "gate_stats": gate_stats,
            "outcome_stats": outcome_stats,
            "unique_codes": len({c.code for c in candidates}),
            "duplicates": candidate_count - len({c.code for c in candidates}),
        },
        "post_market_review": {
            "exists": post_review is not None,
            "date": str(post_review.date) if post_review else None,
            "brief_grade": post_review.brief_grade if post_review else None,
            "has_next_day_seeds": bool(post_review.next_day_seeds) if post_review else False,
            "has_carry_over_themes": bool(post_review.carry_over_themes) if post_review else False,
        },
    }

    all_exist = all(v["exists"] for v in checks.values())
    no_duplicates = checks["candidate_pool"]["duplicates"] == 0

    return {
        "date": d.isoformat(),
        "overall": "PASS" if (all_exist and no_duplicates) else "FAIL",
        "summary": {
            "all_objects_exist": all_exist,
            "no_duplicate_candidates": no_duplicates,
            "candidate_count": candidate_count,
        },
        "checks": checks,
    }
