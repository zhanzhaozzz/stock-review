"""V1 PostMarketReview Pydantic schemas。"""
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel

BriefGrade = Literal["成功", "部分成功", "失败"]


class PostMarketReviewCreate(BaseModel):
    date: date
    brief_grade: Optional[BriefGrade] = None
    grade_reason: Optional[str] = None
    actual_market_trend: Optional[str] = None
    carry_over_themes: Optional[list] = None
    next_day_seeds: Optional[list] = None
    eliminated_directions: Optional[list] = None


class PostMarketReviewUpdate(BaseModel):
    brief_grade: Optional[BriefGrade] = None
    grade_reason: Optional[str] = None
    actual_market_trend: Optional[str] = None
    carry_over_themes: Optional[list] = None
    next_day_seeds: Optional[list] = None
    eliminated_directions: Optional[list] = None


class PostMarketReviewRead(BaseModel):
    date: date
    brief_grade: Optional[str] = None
    grade_reason: Optional[str] = None
    actual_market_trend: Optional[str] = None
    carry_over_themes: Optional[list] = None
    next_day_seeds: Optional[list] = None
    eliminated_directions: Optional[list] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
