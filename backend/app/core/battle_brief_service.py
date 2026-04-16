"""V1 BattleBrief 服务层。"""
import json
import logging
import re
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.battle_brief import BattleBrief
from app.schemas.battle_brief import BattleBriefCreate, BattleBriefUpdate

logger = logging.getLogger(__name__)


async def get_by_date(db: AsyncSession, target_date: date) -> BattleBrief | None:
    result = await db.execute(
        select(BattleBrief).where(BattleBrief.date == target_date)
    )
    return result.scalar_one_or_none()


async def create_or_update(
    db: AsyncSession, data: BattleBriefCreate
) -> BattleBrief:
    existing = await get_by_date(db, data.date)
    if existing:
        for field, value in data.model_dump(exclude_unset=True, exclude={"date"}).items():
            setattr(existing, field, value)
        await db.commit()
        await db.refresh(existing)
        return existing

    record = BattleBrief(**data.model_dump(exclude_unset=True))
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def generate(db: AsyncSession, target_date: date) -> BattleBrief:
    """基于最近一期 MarketStateDaily + 隔夜新闻 生成 BattleBrief。

    幂等：同日已存在则覆盖更新。
    """
    logger.info("[BattleBrief] 开始生成 date=%s", target_date)

    from app.core import market_state_service
    from app.news.aggregator import get_aggregator
    from app.config import get_settings
    from app.llm.client import chat
    from app.llm.prompts.battle_brief import BATTLE_BRIEF_SYSTEM_PROMPT, build_battle_brief_prompt

    market_state = await market_state_service.get_by_date(db, target_date)
    if not market_state:
        from datetime import timedelta
        yesterday = target_date - timedelta(days=1)
        while yesterday.weekday() >= 5:
            yesterday -= timedelta(days=1)
        market_state = await market_state_service.get_by_date(db, yesterday)

    ms_context = {}
    if market_state:
        ms_context = {
            "date": str(market_state.date),
            "temperature_score": market_state.temperature_score,
            "market_phase": market_state.market_phase,
            "style_tag": market_state.style_tag,
            "limit_up_count": market_state.limit_up_count,
            "limit_down_count": market_state.limit_down_count,
            "boom_rate": market_state.boom_rate,
            "highest_ladder": market_state.highest_ladder,
            "promotion_rate": market_state.promotion_rate,
            "focus_sectors": market_state.focus_sectors,
            "conclusion": market_state.conclusion,
        }
        logger.info("[BattleBrief] 市场状态已加载 phase=%s", market_state.market_phase)
    else:
        logger.warning("[BattleBrief] 无可用 MarketStateDaily，将基于空上下文生成")

    news_items = []
    try:
        agg = get_aggregator()
        raw_news = await agg.fetch_latest(limit=30)
        for item in raw_news[:15]:
            news_items.append({
                "title": item.title,
                "source": item.source,
                "summary": (item.summary or "")[:100],
            })
        logger.info("[BattleBrief] 新闻获取完成 count=%d", len(news_items))
    except Exception as e:
        logger.warning("[BattleBrief] 新闻获取失败: %s", e)

    context = {
        "target_date": str(target_date),
        "latest_market_state": ms_context,
        "overnight_news": news_items,
    }

    settings = get_settings()
    model = settings.analysis_llm_model or settings.utility_llm_model or "zhipu/glm-4-flash"

    raw = await chat(
        model=model,
        prompt=build_battle_brief_prompt(context),
        system=BATTLE_BRIEF_SYSTEM_PROMPT,
        temperature=0.3,
        timeout=60,
    )

    llm_output = _parse_llm_json(raw)

    _TONE_VALID = {"可做", "轻仓试错", "防守观察", "不做"}
    status_tone = llm_output.get("status_tone", "")
    if status_tone not in _TONE_VALID:
        status_tone = _fallback_tone(ms_context.get("market_phase", ""))

    data = BattleBriefCreate(
        date=target_date,
        status_tone=status_tone,
        suggested_position=llm_output.get("suggested_position", "2成"),
        overall_conclusion=llm_output.get("overall_conclusion", ""),
        macro_context=llm_output.get("macro_context", []),
        main_narrative=llm_output.get("main_narrative", []),
        bullish_sectors=llm_output.get("bullish_sectors", []),
        bearish_sectors=llm_output.get("bearish_sectors", []),
        risk_tips=llm_output.get("risk_tips", []),
        allowed_actions=llm_output.get("allowed_actions", []),
        forbidden_actions=llm_output.get("forbidden_actions", []),
    )

    result = await create_or_update(db, data)
    logger.info("[BattleBrief] 生成完成 date=%s tone=%s", target_date, status_tone)
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


def _fallback_tone(phase: str) -> str:
    mapping = {
        "高潮": "可做",
        "发酵": "可做",
        "启动": "轻仓试错",
        "高位混沌": "防守观察",
        "退潮": "不做",
        "冰点": "防守观察",
    }
    return mapping.get(phase, "防守观察")
