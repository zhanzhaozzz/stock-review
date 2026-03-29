"""AI 分析流水线 — 行情数据 → 技术面分析 → 获取新闻 → 基本面快照 → LLM 生成报告。

数据流:
  1. 获取日线行情 + 实时行情
  2. 技术面规则引擎 (stock_analyzer) 生成结构化信号
  3. 获取基本面数据
  4. 获取近期相关新闻 (从 news_cache 表查)
  5. 获取最新评级 (如果有)
  6. 组装上下文 → LLM 生成分析报告
  7. 解析 JSON → 持久化到 analysis_history 表
"""
import json
import logging
import re
from datetime import date
from typing import Optional

from app.config import get_settings
from app.core.stock_analyzer import analyze_technical, TechnicalResult
from app.data_provider.manager import get_data_manager
from app.llm.client import chat
from app.llm.prompts.analysis import ANALYSIS_SYSTEM_PROMPT, build_analysis_prompt

logger = logging.getLogger(__name__)


async def analyze_stock(
    code: str,
    name: str = "",
    market: str = "A",
    days: int = 120,
) -> Optional[dict]:
    """对单只股票执行完整 AI 分析，返回分析报告 dict。"""
    mgr = get_data_manager()

    df = await mgr.get_daily(code, days)
    if df is None or len(df) < 20:
        logger.warning("Insufficient data for analysis: %s", code)
        return None

    if not name:
        try:
            quote = await mgr.get_realtime_quote(code)
            if quote and quote.get("name"):
                name = quote["name"]
        except Exception:
            name = code

    technical = analyze_technical(df)
    technical_context = technical.to_context()

    price_summary = _build_price_summary(df)

    fund_data = await mgr.get_fundamental(code)
    fund_summary = _build_fund_summary(fund_data) if fund_data else ""

    news_context = await _get_news_context(code, name)

    rating_summary = await _get_rating_summary(code)

    settings = get_settings()
    model = settings.analysis_llm_model or "deepseek/deepseek-chat"

    prompt = build_analysis_prompt(
        name=name,
        code=code,
        market=market,
        price_summary=price_summary,
        technical_context=technical_context,
        fundamental_summary=fund_summary,
        news_context=news_context,
        rating_summary=rating_summary,
    )

    raw = await chat(model=model, prompt=prompt, system=ANALYSIS_SYSTEM_PROMPT, timeout=180)
    if not raw:
        logger.warning("LLM returned empty for analysis of %s", code)
        return _fallback_report(code, name, market, technical, fund_data)

    parsed = _parse_analysis_response(raw)
    if not parsed:
        logger.warning("Failed to parse LLM analysis for %s", code)
        return _fallback_report(code, name, market, technical, fund_data)

    parsed["code"] = code
    parsed["name"] = name
    parsed["market"] = market
    parsed["raw_result"] = raw
    parsed["technical"] = technical.to_context()

    if fund_data:
        parsed["pe"] = fund_data.get("pe")
        parsed["pb"] = fund_data.get("pb")
        parsed["roe"] = fund_data.get("roe")

    return parsed


def _build_price_summary(df) -> str:
    """构建价格摘要。"""
    import pandas as pd
    close = pd.Series(df["close"].values, dtype=float)
    price = close.iloc[-1]
    hi, lo = close.max(), close.min()
    lines = [f"- 最新价: {price:.2f}"]
    for offset, label in [(6, "5日"), (11, "10日"), (21, "20日"), (61, "60日")]:
        if len(close) > offset:
            ret = (price / close.iloc[-offset] - 1) * 100
            lines.append(f"- {label}涨跌幅: {ret:+.2f}%")
    dd = (hi - price) / (hi + 1e-10) * 100
    rb = (price - lo) / (lo + 1e-10) * 100
    lines.append(f"- 区间高点: {hi:.2f} (回撤 {dd:.1f}%)")
    lines.append(f"- 区间低点: {lo:.2f} (反弹 {rb:.1f}%)")
    return "\n".join(lines)


def _build_fund_summary(fund: dict) -> str:
    """构建基本面摘要。"""
    parts = []
    if fund.get("pe") is not None:
        parts.append(f"PE: {fund['pe']:.2f}")
    if fund.get("pb") is not None:
        parts.append(f"PB: {fund['pb']:.2f}")
    if fund.get("roe") is not None:
        parts.append(f"ROE: {fund['roe']:.2f}%")
    if fund.get("market_cap") is not None:
        mc = fund["market_cap"] / 100_000_000
        parts.append(f"市值: {mc:.0f}亿")
    if fund.get("industry"):
        parts.append(f"行业: {fund['industry']}")
    if fund.get("net_flow") is not None:
        nf = fund["net_flow"] / 10000
        parts.append(f"主力净流入: {nf:.0f}万")
    return " | ".join(parts) if parts else ""


async def _get_news_context(code: str, name: str, limit: int = 8) -> str:
    """从 news_cache 表获取相关新闻作为上下文。"""
    try:
        from sqlalchemy import select, desc, or_
        from app.database import async_session
        from app.models.news import NewsCache

        clean_code = code.split(".")[0]
        async with async_session() as session:
            stmt = (
                select(NewsCache)
                .where(
                    or_(
                        NewsCache.title.contains(name),
                        NewsCache.title.contains(clean_code),
                    )
                )
                .order_by(desc(NewsCache.publish_time))
                .limit(limit)
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()

        if not rows:
            return ""

        lines = []
        for r in rows:
            time_str = r.publish_time.strftime("%m-%d %H:%M") if r.publish_time else ""
            lines.append(f"- [{time_str}] {r.title} ({r.source})")
        return "\n".join(lines)
    except Exception as e:
        logger.debug("News context fetch failed: %s", e)
        return ""


async def _get_rating_summary(code: str) -> str:
    """获取最新评级作为参考。"""
    try:
        from sqlalchemy import select, desc
        from app.database import async_session
        from app.models.rating import Rating

        async with async_session() as session:
            stmt = (
                select(Rating)
                .where(Rating.code == code)
                .order_by(desc(Rating.date))
                .limit(1)
            )
            result = await session.execute(stmt)
            r = result.scalar_one_or_none()

        if not r:
            return ""

        parts = [
            f"评级: {r.rating} (总分{r.total_score:.0f})",
            f"趋势{r.trend_score:.0f} 动量{r.momentum_score:.0f} 波动{r.volatility_score:.0f}",
            f"成交量{r.volume_score:.0f} 价值{r.value_score:.0f} 情绪{r.sentiment_score:.0f}",
        ]
        if r.ai_score:
            parts.append(f"AI评分{r.ai_score:.0f}")
        if isinstance(r.reason, dict) and r.reason.get("text"):
            parts.append(f"AI分析: {r.reason['text'][:100]}")
        return " | ".join(parts)
    except Exception as e:
        logger.debug("Rating summary fetch failed: %s", e)
        return ""


def _parse_analysis_response(raw: str) -> Optional[dict]:
    """解析 LLM 返回的 JSON 报告。"""
    text = raw.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        text = match.group(1).strip()

    for attempt in [text, raw.strip()]:
        try:
            data = json.loads(attempt)
            if isinstance(data, dict) and ("summary" in data or "signal" in data):
                return data
        except json.JSONDecodeError:
            continue

    json_match = re.search(r"\{[\s\S]*\}", raw)
    if json_match:
        try:
            data = json.loads(json_match.group())
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    return None


def _fallback_report(code: str, name: str, market: str, tech: TechnicalResult, fund: Optional[dict]) -> dict:
    """LLM 失败时的降级报告。"""
    signal = "观望"
    if tech.trend_strength >= 65:
        signal = "持有" if tech.trend_strength < 80 else "买入"
    elif tech.trend_strength <= 35:
        signal = "观望" if tech.trend_strength > 20 else "卖出"

    return {
        "code": code,
        "name": name,
        "market": market,
        "summary": tech.summary,
        "signal": signal,
        "score": tech.trend_strength,
        "target_price": None,
        "stop_loss": None,
        "technical_view": tech.to_context(),
        "fundamental_view": _build_fund_summary(fund) if fund else "基本面数据暂缺",
        "news_impact": "暂无新闻上下文",
        "key_points": tech.signals[:3] if tech.signals else ["暂无关键信号"],
        "risk_warnings": tech.warnings[:3] if tech.warnings else ["暂无风险提示"],
        "sentiment_context": {},
        "position_advice": {},
        "raw_result": "",
        "technical": tech.to_context(),
    }
