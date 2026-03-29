"""AI 分析相关的 Pydantic 模型。"""
from pydantic import BaseModel
from typing import Optional


class AnalyzeRequest(BaseModel):
    codes: list[str]


class PositionAdvice(BaseModel):
    suggested_size: str = ""
    entry_type: str = ""
    stop_condition: str = ""


class SentimentContext(BaseModel):
    current_cycle: str = ""
    applicable_strategy: str = ""
    strategy_reason: str = ""


class AnalysisItem(BaseModel):
    code: str
    name: str = ""
    market: str = "A"
    date: str = ""
    summary: str = ""
    signal: str = "观望"
    score: float = 0
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    technical_view: str = ""
    fundamental_view: str = ""
    news_impact: str = ""
    key_points: list[str] = []
    risk_warnings: list[str] = []
    sentiment_context: Optional[SentimentContext] = None
    position_advice: Optional[PositionAdvice] = None


class AnalyzeResponse(BaseModel):
    total: int
    success: int
    failed: int
    results: list[AnalysisItem]


class AnalysisHistoryItem(BaseModel):
    id: int
    code: str
    name: str
    market: str
    date: str
    score: Optional[float] = None
    advice: Optional[str] = None
    summary: str = ""
    signal: str = ""
    created_at: str = ""
