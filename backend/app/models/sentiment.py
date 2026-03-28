from datetime import datetime, date

from sqlalchemy import String, Integer, Float, Boolean, Text, Date, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SentimentCycleLog(Base):
    """情绪周期变化日志 — 用于趋势分析。"""
    __tablename__ = "sentiment_cycle_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, unique=True, index=True)
    cycle_phase: Mapped[str] = mapped_column(String(20))
    market_height: Mapped[int | None] = mapped_column(Integer)
    main_sector: Mapped[str | None] = mapped_column(String(50))
    transition_note: Mapped[str | None] = mapped_column(Text)


class OperationRecord(Base):
    """操作记录 — 用于验证"我的操作模式是否正确"。"""
    __tablename__ = "operation_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    strategy_used: Mapped[str | None] = mapped_column(String(50))
    target_stock: Mapped[str | None] = mapped_column(String(100))
    action: Mapped[str | None] = mapped_column(String(20))
    position_size: Mapped[str | None] = mapped_column(String(20))
    entry_reason: Mapped[str | None] = mapped_column(Text)
    result_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    result_pnl: Mapped[float | None] = mapped_column(Float)
    result_note: Mapped[str | None] = mapped_column(Text)
    is_correct: Mapped[bool | None] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
