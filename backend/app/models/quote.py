from datetime import datetime, date

from sqlalchemy import String, Text, Date, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TradingQuote(Base):
    """交易语录 — 记录每日交易心得与规则积累。"""
    __tablename__ = "trading_quotes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
