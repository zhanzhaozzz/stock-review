"""V1 核心对象：候选池条目。"""
from datetime import datetime, date

from sqlalchemy import String, Integer, Date, DateTime, Text, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CandidatePoolEntry(Base):
    """当天作战名单，承载选股理由、门控状态和盘后验证结果。"""
    __tablename__ = "candidate_pool_entries"
    __table_args__ = (
        UniqueConstraint("date", "code", name="uq_candidate_pool_date_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    code: Mapped[str] = mapped_column(String(20), index=True)
    name: Mapped[str] = mapped_column(String(64))
    source_type: Mapped[str] = mapped_column(String(32))
    source_reason: Mapped[str | None] = mapped_column(Text)
    theme: Mapped[str | None] = mapped_column(String(128))
    thesis: Mapped[str | None] = mapped_column(Text)
    gate_status: Mapped[str | None] = mapped_column(String(32))
    gate_reason: Mapped[str | None] = mapped_column(Text)
    action_hint: Mapped[str | None] = mapped_column(String(32))
    risk_flags: Mapped[dict | None] = mapped_column(JSON)
    review_outcome: Mapped[str] = mapped_column(String(32), default="待复盘")
    review_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
