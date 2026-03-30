"""评级相关的 Pydantic 模型。"""
from pydantic import BaseModel, Field


class RatingRunRequest(BaseModel):
    codes: list[str] = Field(..., description="股票代码列表", min_length=1, max_length=50)


class RatingScores(BaseModel):
    trend_score: float = 0
    momentum_score: float = 0
    volatility_score: float = 0
    volume_score: float = 0
    value_score: float = 0
    sentiment_score: float = 0
    fundamental_score: float | None = None
    ai_score: float = 0
    total_score: float = 0


class RatingItem(RatingScores):
    code: str
    name: str
    market: str = "A"
    rating: str = ""
    reason: str = ""
    pe: float | None = None
    pb: float | None = None
    roe: float | None = None
    market_cap: float | None = None
    net_flow: float | None = None
    date: str = ""


class RatingRunResponse(BaseModel):
    total: int = 0
    success: int = 0
    failed: int = 0
    results: list[RatingItem] = []


class RatingHistoryItem(BaseModel):
    date: str
    total_score: float
    rating: str
    trend_score: float = 0
    momentum_score: float = 0
    volatility_score: float = 0
    volume_score: float = 0
    value_score: float = 0
    sentiment_score: float = 0
    ai_score: float = 0
