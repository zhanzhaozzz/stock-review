"""AI 分析 API — 个股深度分析报告。

数据流:
  1. POST /analyze     — 触发分析 → LLM 生成报告 → 写入 analysis_history 表
  2. GET  /history      — 从 SQLite 查询历史分析记录
  3. GET  /{record_id}  — 查看某次分析的完整报告
"""
import asyncio
import logging
from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.analysis_pipeline import analyze_stock
from app.models.analysis import AnalysisHistory
from app.schemas.analysis import (
    AnalyzeRequest,
    AnalyzeResponse,
    AnalysisItem,
    AnalysisHistoryItem,
    SentimentContext,
    PositionAdvice,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _detect_market(code: str) -> str:
    if code.upper().endswith(".HK") or code.lower().startswith("hk"):
        return "HK"
    return "A"


async def _resolve_name(code: str) -> tuple[str, str]:
    market = _detect_market(code)
    name = code
    try:
        from app.data_provider.manager import get_data_manager
        mgr = get_data_manager()
        quote = await mgr.get_realtime_quote(code)
        if quote and quote.get("name"):
            name = quote["name"]
    except Exception:
        pass
    return name, market


def _to_analysis_item(r: dict, analysis_date: str) -> AnalysisItem:
    """将分析结果 dict 转为 Pydantic 模型。"""
    sc = r.get("sentiment_context")
    pa = r.get("position_advice")
    return AnalysisItem(
        code=r.get("code", ""),
        name=r.get("name", ""),
        market=r.get("market", "A"),
        date=analysis_date,
        summary=r.get("summary", ""),
        signal=r.get("signal", "观望"),
        score=r.get("score", 0),
        target_price=r.get("target_price"),
        stop_loss=r.get("stop_loss"),
        technical_view=r.get("technical_view", ""),
        fundamental_view=r.get("fundamental_view", ""),
        news_impact=r.get("news_impact", ""),
        key_points=r.get("key_points", []),
        risk_warnings=r.get("risk_warnings", []),
        sentiment_context=SentimentContext(**sc) if isinstance(sc, dict) else None,
        position_advice=PositionAdvice(**pa) if isinstance(pa, dict) else None,
    )


@router.post("/analyze", response_model=AnalyzeResponse)
async def run_analysis(req: AnalyzeRequest, db: AsyncSession = Depends(get_db)):
    """对指定股票列表执行 AI 深度分析。"""
    results: list[AnalysisItem] = []
    failed = 0
    today = date.today()
    today_str = str(today)

    sem = asyncio.Semaphore(3)

    async def _analyze_one(code: str):
        nonlocal failed
        async with sem:
            try:
                name, market = await _resolve_name(code)
                r = await analyze_stock(code, name=name, market=market)
                if r is None:
                    failed += 1
                    return

                raw_result = r.get("raw_result", "")
                parsed = {k: v for k, v in r.items() if k not in ("raw_result", "technical", "pe", "pb", "roe")}

                history_obj = AnalysisHistory(
                    code=code,
                    name=r.get("name", code),
                    market=r.get("market", "A"),
                    date=today,
                    raw_result=raw_result,
                    score=r.get("score"),
                    advice=r.get("signal"),
                    news_context=r.get("news_impact", ""),
                    target_price=r.get("target_price"),
                    stop_loss=r.get("stop_loss"),
                    key_levels={"key_points": r.get("key_points", [])},
                    sentiment_context=r.get("sentiment_context"),
                    position_advice=r.get("position_advice"),
                )
                db.add(history_obj)

                results.append(_to_analysis_item(r, today_str))
            except Exception as e:
                logger.error("Analysis failed for %s: %s", code, e)
                failed += 1

    tasks = [_analyze_one(c) for c in req.codes]
    await asyncio.gather(*tasks)

    try:
        await db.commit()
    except Exception as e:
        logger.error("Analysis DB commit failed: %s", e)
        await db.rollback()

    return AnalyzeResponse(
        total=len(req.codes),
        success=len(results),
        failed=failed,
        results=results,
    )


@router.get("/history", response_model=list[AnalysisHistoryItem])
async def analysis_history(
    code: str = Query(None),
    limit: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """分析历史记录。"""
    stmt = select(AnalysisHistory).order_by(desc(AnalysisHistory.created_at))
    if code:
        stmt = stmt.where(AnalysisHistory.code == code)
    stmt = stmt.limit(limit)

    result = await db.execute(stmt)
    rows = result.scalars().all()

    return [
        AnalysisHistoryItem(
            id=r.id,
            code=r.code,
            name=r.name,
            market=r.market,
            date=str(r.date),
            score=r.score,
            advice=r.advice,
            summary=r.raw_result[:200] if r.raw_result else "",
            signal=r.advice or "",
            created_at=r.created_at.isoformat() if r.created_at else "",
        )
        for r in rows
    ]


@router.get("/{record_id}")
async def get_analysis(record_id: int, db: AsyncSession = Depends(get_db)):
    """获取某次分析的完整报告。"""
    stmt = select(AnalysisHistory).where(AnalysisHistory.id == record_id)
    result = await db.execute(stmt)
    r = result.scalar_one_or_none()
    if not r:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Analysis not found")

    return {
        "id": r.id,
        "code": r.code,
        "name": r.name,
        "market": r.market,
        "date": str(r.date),
        "score": r.score,
        "advice": r.advice,
        "raw_result": r.raw_result,
        "news_context": r.news_context,
        "target_price": r.target_price,
        "stop_loss": r.stop_loss,
        "key_levels": r.key_levels,
        "sentiment_context": r.sentiment_context,
        "position_advice": r.position_advice,
        "created_at": r.created_at.isoformat() if r.created_at else "",
    }
