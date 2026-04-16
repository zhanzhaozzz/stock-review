"""V1 核心对象：盘前作战简报。"""
from datetime import datetime, date

from sqlalchemy import String, Date, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BattleBrief(Base):
    """盘前生成的全局作战简报，当天最高指导文件。"""
    __tablename__ = "battle_briefs"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    status_tone: Mapped[str | None] = mapped_column(String(32))
    suggested_position: Mapped[str | None] = mapped_column(String(32))
    overall_conclusion: Mapped[str | None] = mapped_column(Text)
    macro_context: Mapped[dict | None] = mapped_column(JSON)
    main_narrative: Mapped[dict | None] = mapped_column(JSON)
    bullish_sectors: Mapped[dict | None] = mapped_column(JSON)
    bearish_sectors: Mapped[dict | None] = mapped_column(JSON)
    risk_tips: Mapped[dict | None] = mapped_column(JSON)
    allowed_actions: Mapped[dict | None] = mapped_column(JSON)
    forbidden_actions: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
