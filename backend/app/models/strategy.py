from datetime import datetime

from sqlalchemy import String, Integer, Boolean, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Strategy(Base):
    """战法库 — 可编辑的交易策略参考。"""
    __tablename__ = "strategies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    applicable_cycles: Mapped[list | None] = mapped_column(JSON)
    conditions: Mapped[str | None] = mapped_column(Text)
    entry_rules: Mapped[str | None] = mapped_column(Text)
    exit_rules: Mapped[str | None] = mapped_column(Text)
    position_rules: Mapped[str | None] = mapped_column(Text)
    buy_point_rules: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
