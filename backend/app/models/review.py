from datetime import datetime, date

from sqlalchemy import String, Integer, Float, Boolean, Text, Date, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DailyReview(Base):
    """每日复盘记录 — 对应 Excel 复盘表的结构化存储。"""
    __tablename__ = "daily_reviews"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, unique=True, index=True)

    # --- 市场情绪 ---
    market_sentiment: Mapped[str | None] = mapped_column(String(20))
    market_height: Mapped[int | None] = mapped_column(Integer)
    market_leader: Mapped[str | None] = mapped_column(String(100))
    total_limit_up: Mapped[int | None] = mapped_column(Integer)
    first_board_count: Mapped[int | None] = mapped_column(Integer)
    broken_board_count: Mapped[int | None] = mapped_column(Integer)
    sentiment_detail: Mapped[str | None] = mapped_column(Text)

    # --- 板块 ---
    main_sector: Mapped[str | None] = mapped_column(String(200))
    sub_sector: Mapped[str | None] = mapped_column(String(200))

    # --- 断板高标 ---
    broken_boards: Mapped[str | None] = mapped_column(Text)

    # --- 复盘内容 ---
    review_summary: Mapped[str | None] = mapped_column(Text)
    next_day_plan: Mapped[str | None] = mapped_column(Text)
    applicable_strategy: Mapped[str | None] = mapped_column(String(100))
    suggested_position: Mapped[str | None] = mapped_column(String(50))

    # --- AI 辅助 ---
    ai_review_draft: Mapped[str | None] = mapped_column(Text)
    ai_next_day_suggestion: Mapped[str | None] = mapped_column(Text)

    # --- 盘面过程 ---
    market_action: Mapped[str | None] = mapped_column(String(10))
    market_result: Mapped[str | None] = mapped_column(String(10))

    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class LimitUpBoard(Base):
    """涨停板/连板梯队 — 每日自动生成，替代 Excel 截图。"""
    __tablename__ = "limit_up_boards"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    board_count: Mapped[int] = mapped_column(Integer)
    code: Mapped[str] = mapped_column(String(20), index=True)
    name: Mapped[str] = mapped_column(String(50))
    sector: Mapped[str | None] = mapped_column(String(50))
    change_pct: Mapped[float | None] = mapped_column(Float)
    turnover: Mapped[float | None] = mapped_column(Float)
    is_first_board: Mapped[bool] = mapped_column(Boolean, default=False)
    is_broken: Mapped[bool] = mapped_column(Boolean, default=False)
