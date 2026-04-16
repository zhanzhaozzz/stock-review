"""V1 核心对象：每日市场状态。"""
from datetime import datetime, date

from sqlalchemy import String, Integer, Float, Date, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MarketStateDaily(Base):
    """每日收盘后的客观市场状态，给出客观机器定调。"""
    __tablename__ = "market_state_daily"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    temperature_score: Mapped[int | None] = mapped_column(Integer)
    market_phase: Mapped[str | None] = mapped_column(String(32))
    style_tag: Mapped[str | None] = mapped_column(String(32))
    limit_up_count: Mapped[int | None] = mapped_column(Integer)
    limit_down_count: Mapped[int | None] = mapped_column(Integer)
    boom_rate: Mapped[float | None] = mapped_column(Float)
    highest_ladder: Mapped[int | None] = mapped_column(Integer)
    promotion_rate: Mapped[float | None] = mapped_column(Float)
    total_volume: Mapped[int | None] = mapped_column(Integer)
    volume_delta: Mapped[int | None] = mapped_column(Integer)
    focus_sectors: Mapped[dict | None] = mapped_column(JSON)
    conclusion: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
