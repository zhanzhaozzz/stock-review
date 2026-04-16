"""V1 MarketStateDaily 服务层。"""
import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_state import MarketStateDaily
from app.schemas.market_state import MarketStateDailyCreate, MarketStateDailyUpdate

logger = logging.getLogger(__name__)


async def get_by_date(db: AsyncSession, target_date: date) -> MarketStateDaily | None:
    result = await db.execute(
        select(MarketStateDaily).where(MarketStateDaily.date == target_date)
    )
    return result.scalar_one_or_none()


async def create_or_update(
    db: AsyncSession, data: MarketStateDailyCreate
) -> MarketStateDaily:
    existing = await get_by_date(db, data.date)
    if existing:
        for field, value in data.model_dump(exclude_unset=True, exclude={"date"}).items():
            setattr(existing, field, value)
        await db.commit()
        await db.refresh(existing)
        return existing

    record = MarketStateDaily(**data.model_dump(exclude_unset=True))
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def generate_from_snapshot(db: AsyncSession, target_date: date) -> MarketStateDaily:
    """从涨停梯队 / 市场总览等原始数据组装 MarketStateDaily。

    幂等：同日已存在则覆盖更新。
    """
    logger.info("[MarketState] 开始生成 date=%s", target_date)

    from app.core.limit_up_tracker import get_limit_up_data
    from app.core.market_review import get_market_overview, get_total_volume_with_delta
    from app.core.sentiment_engine import judge_cycle_by_rules

    limit_up = await get_limit_up_data(str(target_date))
    logger.info("[MarketState] 涨停数据获取完成: height=%s", limit_up.get("market_height"))

    market_overview = await get_market_overview()
    logger.info("[MarketState] 市场总览获取完成")

    volume_info = await get_total_volume_with_delta(str(target_date))

    ladder = limit_up.get("ladder", [])
    total_limit_up = sum(item.get("count", 0) for item in ladder)
    first_board_count = int(limit_up.get("first_board_count", 0) or 0)
    broken_boards = limit_up.get("broken_boards", [])
    broken_count = len(broken_boards)
    boom_rate = round(broken_count / total_limit_up * 100, 2) if total_limit_up > 0 else 0.0

    breadth = market_overview.get("breadth", {}) if isinstance(market_overview, dict) else {}

    rule_result = judge_cycle_by_rules(limit_up)
    market_phase = rule_result.get("phase", "冰点")

    style_tag = _infer_style_tag(market_phase, total_limit_up, limit_up.get("market_height", 0))

    sector_dist = limit_up.get("sector_distribution", {})
    focus_sectors = list(sector_dist.keys())[:8]

    total_amount_yi = volume_info.get("total_amount_yi", 0)
    total_volume_int = int(total_amount_yi * 100_000_000) if total_amount_yi else 0
    delta_amount_yi = volume_info.get("delta_amount_yi", 0)
    volume_delta_int = int(delta_amount_yi * 100_000_000) if delta_amount_yi else 0

    temperature = _calc_temperature(
        total_limit_up, broken_count, limit_up.get("market_height", 0),
        breadth.get("up", 0), breadth.get("down", 0),
    )

    conclusion = _build_conclusion(
        market_phase, style_tag, temperature,
        total_limit_up, broken_count, limit_up.get("market_height", 0),
    )

    data = MarketStateDailyCreate(
        date=target_date,
        temperature_score=temperature,
        market_phase=market_phase,
        style_tag=style_tag,
        limit_up_count=total_limit_up,
        limit_down_count=int(limit_up.get("limit_down_count", 0) or breadth.get("limit_down", 0) or 0),
        boom_rate=boom_rate,
        highest_ladder=int(limit_up.get("market_height", 0) or 0),
        promotion_rate=float(limit_up.get("promotion_rate", 0.0) or 0.0),
        total_volume=total_volume_int,
        volume_delta=volume_delta_int,
        focus_sectors=focus_sectors,
        conclusion=conclusion,
    )

    result = await create_or_update(db, data)
    logger.info("[MarketState] 生成完成 date=%s phase=%s temp=%s", target_date, market_phase, temperature)
    return result


def _calc_temperature(
    limit_up: int, broken: int, height: int,
    up_count: int, down_count: int,
) -> int:
    """根据客观数据计算市场温度 0-100。"""
    score = 50

    if limit_up >= 80:
        score += 20
    elif limit_up >= 50:
        score += 10
    elif limit_up <= 20:
        score -= 15

    if height >= 6:
        score += 10
    elif height >= 4:
        score += 5
    elif height <= 2:
        score -= 5

    if limit_up > 0:
        boom_pct = broken / limit_up * 100
        if boom_pct >= 30:
            score -= 10
        elif boom_pct <= 10:
            score += 5

    total = up_count + down_count
    if total > 0:
        up_pct = up_count / total * 100
        if up_pct >= 65:
            score += 10
        elif up_pct <= 35:
            score -= 10

    return max(0, min(100, score))


def _infer_style_tag(phase: str, limit_up: int, height: int) -> str:
    if phase in ("高潮", "发酵") and height >= 4:
        return "接力优先"
    if phase == "启动":
        return "趋势优先"
    if phase == "高位混沌":
        return "轮动试错"
    return "防守观察"


def _build_conclusion(
    phase: str, style: str, temp: int,
    limit_up: int, broken: int, height: int,
) -> str:
    return (
        f"市场阶段={phase}，风格={style}，温度={temp}。"
        f"涨停{limit_up}家，炸板{broken}家，最高{height}板。"
    )
