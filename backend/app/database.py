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


async def init_db():
    """Create all tables."""
    from app.models import stock, rating, analysis, watchlist, news, review, strategy, sentiment, user, llm_usage, market  # noqa: F401

    async with engine.begin() as conn:
        await _migrate_operation_records(conn)
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully")


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
