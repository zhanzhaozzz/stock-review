"""每日复盘引擎 — 基于客观数据 + LLM 生成结构化复盘草稿。"""
import json
import logging
from datetime import date

from app.config import get_settings
from app.core.market_review import get_daily_context
from app.core.sentiment_engine import judge_cycle_with_ai
from app.llm.client import chat
from app.llm.prompts.review import REVIEW_SYSTEM_PROMPT, build_review_prompt

logger = logging.getLogger(__name__)

SENTIMENT_ENUM = {"启动期", "发酵期", "高潮期", "高位混沌期", "退潮期", "低位混沌期"}
QUADRANT_ENUM = {"情指共振", "情好指差", "情差指好", "情指双杀"}


async def generate_daily_review(
    limit_up_data: dict,
    market_overview: dict = None,
    prev_phases: list[str] = None,
) -> dict:
    """生成当天的结构化复盘草稿（对齐 DailyReview 新字段）。"""
    trade_date = limit_up_data.get("date") if isinstance(limit_up_data, dict) else "today"
    daily_context = await get_daily_context(
        target_date=trade_date,
        limit_up_data_override=limit_up_data if isinstance(limit_up_data, dict) else None,
        market_overview_override=market_overview if isinstance(market_overview, dict) else None,
    )

    limit_context = daily_context.get("limit_up_data", {})
    market_ctx = daily_context.get("market_overview", {})
    cycle_result = await judge_cycle_with_ai(limit_context, market_ctx, prev_phases)

    llm_output = await _generate_structured_review(daily_context, cycle_result, prev_phases or [])

    sentiment_cycle_main = _normalize_sentiment(
        llm_output.get("sentiment_cycle_main", ""),
        cycle_result.get("phase", ""),
    )
    conclusion_quadrant = _normalize_quadrant(
        llm_output.get("conclusion_quadrant", ""),
        sentiment_cycle_main,
    )
    main_sectors = llm_output.get("main_sectors", "") or daily_context.get("main_sectors", "")
    sub_sectors = llm_output.get("sub_sectors", "") or daily_context.get("sub_sectors", "")
    market_style = llm_output.get("market_style", "")
    broken_high_stock = llm_output.get("broken_high_stock", "")
    next_day_prediction = llm_output.get("next_day_prediction", "")
    next_day_mode = llm_output.get("next_day_mode", "")
    core_middle_stock = llm_output.get("core_middle_stock", "") or daily_context.get("core_middle_stock", "")

    broken_boards = limit_context.get("broken_boards", []) if isinstance(limit_context, dict) else []
    total_limit_up = sum(item.get("count", 0) for item in limit_context.get("ladder", [])) if isinstance(limit_context, dict) else 0
    first_board_count = int(limit_context.get("first_board_count", 0) or 0) if isinstance(limit_context, dict) else 0
    broken_board_count = len(broken_boards)

    review_summary = f"{sentiment_cycle_main}，{conclusion_quadrant}。{market_style}".strip("，。")
    next_day_plan = "\n".join(x for x in [next_day_prediction, next_day_mode] if x).strip()

    return {
        "date": str(date.today()),
        "status": "draft",
        "market_height": int(daily_context.get("market_height", 0) or 0),
        "dragon_stock": daily_context.get("dragon_stock", ""),
        "core_middle_stock": core_middle_stock,
        "market_ladder": daily_context.get("market_ladder", ""),
        "total_volume": daily_context.get("total_volume", ""),
        "sentiment_cycle_main": sentiment_cycle_main,
        "main_sectors": main_sectors,
        "sub_sectors": sub_sectors,
        "market_style": market_style,
        "broken_high_stock": broken_high_stock,
        "conclusion_quadrant": conclusion_quadrant,
        "next_day_prediction": next_day_prediction,
        "next_day_mode": next_day_mode,
        "market_sentiment": sentiment_cycle_main,
        "total_limit_up": total_limit_up,
        "first_board_count": first_board_count,
        "broken_board_count": broken_board_count,
        "main_sector": main_sectors,
        "sub_sector": sub_sectors,
        "broken_boards": json.dumps(broken_boards[:10], ensure_ascii=False) if broken_boards else "",
        "review_summary": review_summary,
        "next_day_plan": next_day_plan,
        "applicable_strategy": _strategy_by_quadrant(conclusion_quadrant),
        "suggested_position": _position_by_quadrant(conclusion_quadrant),
        "cycle_result": cycle_result,
    }


async def _generate_structured_review(daily_context: dict, cycle_result: dict, prev_phases: list[str]) -> dict:
    prompt_context = {
        **daily_context,
        "cycle_hint": cycle_result,
        "prev_phases": prev_phases,
    }
    prompt = build_review_prompt(prompt_context)
    settings = get_settings()
    raw = await chat(
        model=settings.utility_llm_model or "zhipu/glm-4-flash",
        prompt=prompt,
        system=REVIEW_SYSTEM_PROMPT,
        temperature=0.2,
        timeout=60,
    )
    if not raw:
        return {}
    try:
        import re
        matched = re.search(r"\{[\s\S]*\}", raw)
        if not matched:
            return {}
        data = json.loads(matched.group())
        if isinstance(data, dict):
            return data
    except Exception as e:
        logger.warning("Parse review json failed: %s", e)
    return {}


def _normalize_sentiment(raw_sentiment: str, cycle_phase: str) -> str:
    if raw_sentiment in SENTIMENT_ENUM:
        return raw_sentiment
    phase_map = {
        "冰点": "低位混沌期",
        "启动": "启动期",
        "发酵": "发酵期",
        "高潮": "高潮期",
        "高位混沌": "高位混沌期",
        "分歧": "高位混沌期",
        "退潮": "退潮期",
    }
    return phase_map.get(cycle_phase, "低位混沌期")


def _normalize_quadrant(raw_quadrant: str, sentiment_cycle_main: str) -> str:
    if raw_quadrant in QUADRANT_ENUM:
        return raw_quadrant
    if sentiment_cycle_main in {"启动期", "发酵期", "高潮期"}:
        return "情指共振"
    if sentiment_cycle_main == "高位混沌期":
        return "情好指差"
    if sentiment_cycle_main == "退潮期":
        return "情指双杀"
    return "情差指好"


def _strategy_by_quadrant(conclusion_quadrant: str) -> str:
    mapping = {
        "情指共振": "擒龙主升",
        "情差指好": "切换试错",
        "情好指差": "补涨缠龙",
        "情指双杀": "空仓等待",
    }
    return mapping.get(conclusion_quadrant, "试错轻仓")


def _position_by_quadrant(conclusion_quadrant: str) -> str:
    mapping = {
        "情指共振": "5-7成",
        "情差指好": "2-3成",
        "情好指差": "3-4成",
        "情指双杀": "0-1成",
    }
    return mapping.get(conclusion_quadrant, "2成")
