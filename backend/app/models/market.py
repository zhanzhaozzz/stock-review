# LEGACY — V1 已由 MarketStateDaily 替代（结构化客观定调）。
# 保留为原始快照缓存层，不再作为页面主结论层。
# market_state_service.generate_from_snapshot 间接消费其数据源。

"""市场快照 — 大盘指数、涨跌面、板块排行持久化存储。"""
from datetime import datetime, date

from sqlalchemy import String, Integer, Float, Date, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MarketSnapshot(Base):
    """每日市场快照 — 替代 Redis 短缓存，支持历史查询。"""
    __tablename__ = "market_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    snapshot_type: Mapped[str] = mapped_column(String(30), index=True)
    data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
