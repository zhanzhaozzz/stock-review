# LEGACY — 量化评级保留为辅助工具，不再作为 V1 主流程入口。
# /ratings 页面仍可通过 URL 直接访问但不在主导航。

from datetime import datetime, date

from sqlalchemy import String, Float, Integer, Text, Date, DateTime, UniqueConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Rating(Base):
    __tablename__ = "ratings"
    __table_args__ = (UniqueConstraint("code", "date", "model_type", name="uq_rating_code_date_model"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), index=True)
    name: Mapped[str] = mapped_column(String(50))
    market: Mapped[str] = mapped_column(String(5))
    date: Mapped[date] = mapped_column(Date, index=True)
    model_type: Mapped[str] = mapped_column(String(20), default="quant_ai")

    # 六维技术因子评分 (0-100)
    trend_score: Mapped[float | None] = mapped_column(Float)
    momentum_score: Mapped[float | None] = mapped_column(Float)
    volatility_score: Mapped[float | None] = mapped_column(Float)
    volume_score: Mapped[float | None] = mapped_column(Float)
    value_score: Mapped[float | None] = mapped_column(Float)
    sentiment_score: Mapped[float | None] = mapped_column(Float)

    # 综合评分
    fundamental_score: Mapped[float | None] = mapped_column(Float)
    ai_score: Mapped[float | None] = mapped_column(Float)
    total_score: Mapped[float | None] = mapped_column(Float)
    rating: Mapped[str | None] = mapped_column(String(20))

    reason: Mapped[dict | None] = mapped_column(JSON)

    # 基本面快照
    pe: Mapped[float | None] = mapped_column(Float)
    pb: Mapped[float | None] = mapped_column(Float)
    roe: Mapped[float | None] = mapped_column(Float)
    market_cap: Mapped[float | None] = mapped_column(Float)
    net_flow: Mapped[float | None] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
