import logging
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine = create_async_engine(
    settings.database_url,
    echo=settings.app_env == "development",
    connect_args={"check_same_thread": False},
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _migrate_operation_records(conn):
    """兼容旧版 operation_records 列结构，迁移为新版字段。"""
    if not settings.database_url.startswith("sqlite"):
        return

    table_info = await conn.exec_driver_sql("PRAGMA table_info(operation_records)")
    cols = [row[1] for row in table_info.fetchall()]
    if not cols:
        return

    new_cols = {"entry_price", "exit_price", "pnl_pct", "note"}
    if new_cols.issubset(cols):
        return

    old_cols = {"position_size", "entry_reason", "result_date", "result_pnl", "result_note"}
    if not old_cols.issubset(cols):
        logger.warning("operation_records schema mismatch; skip auto-migration: %s", cols)
        return

    logger.info("Migrating operation_records table to new schema...")
    await conn.exec_driver_sql("""
        CREATE TABLE operation_records_new (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            strategy_used VARCHAR(50),
            target_stock VARCHAR(100),
            action VARCHAR(20),
            entry_price FLOAT,
            exit_price FLOAT,
            pnl_pct FLOAT,
            note TEXT,
            is_correct BOOLEAN,
            created_at DATETIME NOT NULL
        )
    """)
    await conn.exec_driver_sql("""
        INSERT INTO operation_records_new (
            id, date, strategy_used, target_stock, action,
            entry_price, exit_price, pnl_pct, note, is_correct, created_at
        )
        SELECT
            id, date, strategy_used, target_stock, action,
            NULL AS entry_price,
            NULL AS exit_price,
            result_pnl AS pnl_pct,
            result_note AS note,
            is_correct,
            created_at
        FROM operation_records
    """)
    await conn.exec_driver_sql("DROP TABLE operation_records")
    await conn.exec_driver_sql("ALTER TABLE operation_records_new RENAME TO operation_records")
    await conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_operation_records_date ON operation_records (date)"
    )
    logger.info("operation_records migration completed")


async def _migrate_daily_reviews(conn):
    """兼容旧版 daily_reviews，补充 Phase1 MVP 新字段。"""
    if not settings.database_url.startswith("sqlite"):
        return

    table_info = await conn.exec_driver_sql("PRAGMA table_info(daily_reviews)")
    cols = [row[1] for row in table_info.fetchall()]
    if not cols:
        return

    alter_statements = []
    if "status" not in cols:
        alter_statements.append("ALTER TABLE daily_reviews ADD COLUMN status VARCHAR(20) DEFAULT 'draft'")
    if "sentiment_cycle_main" not in cols:
        alter_statements.append("ALTER TABLE daily_reviews ADD COLUMN sentiment_cycle_main VARCHAR(20)")
    if "dragon_stock" not in cols:
        alter_statements.append("ALTER TABLE daily_reviews ADD COLUMN dragon_stock VARCHAR(100)")
    if "core_middle_stock" not in cols:
        alter_statements.append("ALTER TABLE daily_reviews ADD COLUMN core_middle_stock VARCHAR(100)")
    if "market_ladder" not in cols:
        alter_statements.append("ALTER TABLE daily_reviews ADD COLUMN market_ladder TEXT")
    if "total_volume" not in cols:
        alter_statements.append("ALTER TABLE daily_reviews ADD COLUMN total_volume VARCHAR(100)")
    if "main_sectors" not in cols:
        alter_statements.append("ALTER TABLE daily_reviews ADD COLUMN main_sectors VARCHAR(200)")
    if "sub_sectors" not in cols:
        alter_statements.append("ALTER TABLE daily_reviews ADD COLUMN sub_sectors VARCHAR(200)")
    if "market_style" not in cols:
        alter_statements.append("ALTER TABLE daily_reviews ADD COLUMN market_style VARCHAR(200)")
    if "broken_high_stock" not in cols:
        alter_statements.append("ALTER TABLE daily_reviews ADD COLUMN broken_high_stock VARCHAR(200)")
    if "conclusion_quadrant" not in cols:
        alter_statements.append("ALTER TABLE daily_reviews ADD COLUMN conclusion_quadrant VARCHAR(20)")
    if "next_day_prediction" not in cols:
        alter_statements.append("ALTER TABLE daily_reviews ADD COLUMN next_day_prediction TEXT")
    if "next_day_mode" not in cols:
        alter_statements.append("ALTER TABLE daily_reviews ADD COLUMN next_day_mode TEXT")

    if "sentiment_cycle_sub" not in cols:
        alter_statements.append("ALTER TABLE daily_reviews ADD COLUMN sentiment_cycle_sub VARCHAR(50)")
    if "index_sentiment_sh" not in cols:
        alter_statements.append("ALTER TABLE daily_reviews ADD COLUMN index_sentiment_sh VARCHAR(100)")
    if "index_sentiment_csm" not in cols:
        alter_statements.append("ALTER TABLE daily_reviews ADD COLUMN index_sentiment_csm VARCHAR(100)")

    if not alter_statements:
        return

    logger.info("Migrating daily_reviews table with %d new columns", len(alter_statements))
    for sql in alter_statements:
        await conn.exec_driver_sql(sql)
    logger.info("daily_reviews migration completed")


async def init_db():
    """Create all tables."""
    from app.models import stock, rating, analysis, watchlist, news, review, strategy, sentiment, user, llm_usage, market, fundamental, quote  # noqa: F401

    async with engine.begin() as conn:
        await _migrate_operation_records(conn)
        await _migrate_daily_reviews(conn)
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully")


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
