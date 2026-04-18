# LEGACY — AI 分析历史保留为辅助工具，不再作为 V1 主流程入口。

from datetime import datetime, date

from sqlalchemy import String, Float, Integer, Text, Date, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AnalysisHistory(Base):
    __tablename__ = "analysis_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), index=True)
    name: Mapped[str] = mapped_column(String(50))
    market: Mapped[str] = mapped_column(String(5))
    date: Mapped[date] = mapped_column(Date, index=True)

    raw_result: Mapped[str | None] = mapped_column(Text)
    score: Mapped[float | None] = mapped_column(Float)
    advice: Mapped[str | None] = mapped_column(String(20))
    news_context: Mapped[str | None] = mapped_column(Text)
    target_price: Mapped[float | None] = mapped_column(Float)
    stop_loss: Mapped[float | None] = mapped_column(Float)
    key_levels: Mapped[dict | None] = mapped_column(JSON)

    # 战法与仓位建议 (融合情绪周期体系)
    sentiment_context: Mapped[dict | None] = mapped_column(JSON)
    position_advice: Mapped[dict | None] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
