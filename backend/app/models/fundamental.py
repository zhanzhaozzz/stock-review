from datetime import datetime, date

from sqlalchemy import String, Float, Integer, Date, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class StockFundamental(Base):
    """个股基本面快照 — 每日一条，独立于评级周期。"""
    __tablename__ = "stock_fundamentals"
    __table_args__ = (UniqueConstraint("code", "date", name="uq_fundamental_code_date"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)

    # 核心估值
    pe_ttm: Mapped[float | None] = mapped_column(Float)
    pb_mrq: Mapped[float | None] = mapped_column(Float)
    roe: Mapped[float | None] = mapped_column(Float)
    eps: Mapped[float | None] = mapped_column(Float)
    market_cap: Mapped[float | None] = mapped_column(Float)
    circulating_cap: Mapped[float | None] = mapped_column(Float)
    debt_ratio: Mapped[float | None] = mapped_column(Float)

    # 资金流向（元）
    main_net_inflow: Mapped[float | None] = mapped_column(Float)
    retail_net_inflow: Mapped[float | None] = mapped_column(Float)
    large_net_inflow: Mapped[float | None] = mapped_column(Float)

    # 市场微观
    vol_ratio: Mapped[float | None] = mapped_column(Float)
    turnover_ratio: Mapped[float | None] = mapped_column(Float)
    committee: Mapped[float | None] = mapped_column(Float)
    swing: Mapped[float | None] = mapped_column(Float)
    rise_day_count: Mapped[int | None] = mapped_column(Integer)

    # 多周期涨跌幅 %
    chg_5d: Mapped[float | None] = mapped_column(Float)
    chg_10d: Mapped[float | None] = mapped_column(Float)
    chg_20d: Mapped[float | None] = mapped_column(Float)
    chg_60d: Mapped[float | None] = mapped_column(Float)
    chg_year: Mapped[float | None] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
