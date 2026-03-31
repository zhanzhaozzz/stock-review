"""复盘相关 Pydantic 模型。"""
from pydantic import BaseModel
from typing import Optional


class ReviewRunRequest(BaseModel):
    """触发复盘的请求。"""
    pass


class DailyReviewItem(BaseModel):
    id: int
    date: str
    market_sentiment: str = ""
    market_height: int = 0
    market_leader: str = ""
    total_limit_up: int = 0
    first_board_count: int = 0
    broken_board_count: int = 0
    sentiment_detail: str = ""
    main_sector: str = ""
    sub_sector: str = ""
    review_summary: str = ""
    next_day_plan: str = ""
    applicable_strategy: str = ""
    suggested_position: str = ""
    ai_review_draft: str = ""
    ai_next_day_suggestion: str = ""
    market_action: str = ""
    market_result: str = ""
    is_confirmed: bool = False
    created_at: str = ""


class ReviewUpdateRequest(BaseModel):
    """用户编辑/确认复盘的请求。"""
    market_sentiment: Optional[str] = None
    sentiment_detail: Optional[str] = None
    review_summary: Optional[str] = None
    next_day_plan: Optional[str] = None
    applicable_strategy: Optional[str] = None
    suggested_position: Optional[str] = None
    market_action: Optional[str] = None
    market_result: Optional[str] = None
    is_confirmed: Optional[bool] = None


class LimitUpItem(BaseModel):
    id: int
    date: str
    board_count: int
    code: str
    name: str
    sector: str = ""
    change_pct: Optional[float] = None
    turnover: Optional[float] = None
    is_first_board: bool = False
    is_broken: bool = False


class SentimentLogItem(BaseModel):
    id: int
    date: str
    cycle_phase: str
    market_height: int = 0
    main_sector: str = ""
    transition_note: str = ""
