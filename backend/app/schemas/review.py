"""复盘相关 Pydantic 模型。"""
from pydantic import BaseModel
from typing import Literal, Optional

ReviewStatus = Literal["draft", "published"]
SentimentCycleMain = Literal["冰点", "启动", "发酵", "高潮", "高位混沌", "退潮"]
ConclusionQuadrant = Literal["情指共振", "情好指差", "情差指好", "情指双杀"]


class ReviewRunRequest(BaseModel):
    """触发复盘的请求。"""
    pass


class DailyReviewItem(BaseModel):
    id: int
    date: str
    status: ReviewStatus = "draft"
    market_sentiment: str = ""
    sentiment_cycle_main: str = ""
    market_height: int = 0
    market_leader: str = ""
    dragon_stock: str = ""
    core_middle_stock: str = ""
    market_ladder: str = ""
    total_volume: str = ""
    total_limit_up: int = 0
    first_board_count: int = 0
    broken_board_count: int = 0
    sentiment_detail: str = ""
    main_sector: str = ""
    sub_sector: str = ""
    main_sectors: str = ""
    sub_sectors: str = ""
    market_style: str = ""
    broken_boards: str = ""
    broken_high_stock: str = ""
    sentiment_cycle_sub: str = ""
    index_sentiment_sh: str = ""
    index_sentiment_csm: str = ""
    conclusion_quadrant: str = ""
    review_summary: str = ""
    next_day_plan: str = ""
    next_day_prediction: str = ""
    next_day_mode: str = ""
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
    status: Optional[ReviewStatus] = None
    market_sentiment: Optional[str] = None
    sentiment_cycle_main: Optional[SentimentCycleMain] = None
    market_height: Optional[int] = None
    market_leader: Optional[str] = None
    total_limit_up: Optional[int] = None
    first_board_count: Optional[int] = None
    broken_board_count: Optional[int] = None
    broken_boards: Optional[str] = None
    dragon_stock: Optional[str] = None
    core_middle_stock: Optional[str] = None
    market_ladder: Optional[str] = None
    total_volume: Optional[str] = None
    sentiment_detail: Optional[str] = None
    main_sectors: Optional[str] = None
    sub_sectors: Optional[str] = None
    market_style: Optional[str] = None
    broken_high_stock: Optional[str] = None
    sentiment_cycle_sub: Optional[str] = None
    index_sentiment_sh: Optional[str] = None
    index_sentiment_csm: Optional[str] = None
    conclusion_quadrant: Optional[ConclusionQuadrant] = None
    review_summary: Optional[str] = None
    next_day_plan: Optional[str] = None
    next_day_prediction: Optional[str] = None
    next_day_mode: Optional[str] = None
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
