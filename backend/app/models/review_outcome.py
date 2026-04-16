"""V1 核心对象：盘后全局复盘。"""
from datetime import datetime, date

from sqlalchemy import String, Date, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PostMarketReview(Base):
    """盘后全局复盘，对当天判断做对账，输出明日承接。"""
    __tablename__ = "post_market_reviews"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    brief_grade: Mapped[str | None] = mapped_column(String(32))
    grade_reason: Mapped[str | None] = mapped_column(Text)
    actual_market_trend: Mapped[str | None] = mapped_column(Text)
    carry_over_themes: Mapped[dict | None] = mapped_column(JSON)
    next_day_seeds: Mapped[dict | None] = mapped_column(JSON)
    eliminated_directions: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
