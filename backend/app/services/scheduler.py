"""定时任务调度 — 使用 APScheduler 在收盘后自动刷新数据。

任务列表:
  1. 同步市场数据 (15:30)
  2. 同步新闻数据 (每小时 9:00-20:00)
  3. 同步自选股行情 (15:35)
  4. 执行自选股评级 (15:40)
  5. 执行每日复盘 (15:50)
"""
import logging
from datetime import date

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler = None


def _shift_time(hour: int, minute: int, offset_min: int) -> tuple[int, int]:
    """按分钟偏移并归一化到 24 小时制。"""
    total = (hour * 60 + minute + offset_min) % (24 * 60)
    return total // 60, total % 60


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
    return _scheduler


def setup_scheduler():
    """注册所有定时任务。"""
    scheduler = get_scheduler()
    settings = get_settings()

    hour = settings.refresh_hour
    minute = settings.refresh_minute
    watch_hour, watch_minute = _shift_time(hour, minute, 5)
    rating_hour, rating_minute = _shift_time(hour, minute, 10)
    review_hour, review_minute = _shift_time(hour, minute, 20)

    scheduler.add_job(
        _sync_market_data,
        CronTrigger(hour=hour, minute=minute, day_of_week="mon-fri"),
        id="sync_market",
        name="同步市场数据",
        replace_existing=True,
    )

    scheduler.add_job(
        _sync_news_data,
        CronTrigger(hour="9-20", minute=0, day_of_week="mon-fri"),
        id="sync_news",
        name="同步新闻数据",
        replace_existing=True,
    )

    scheduler.add_job(
        _sync_watchlist_quotes,
        CronTrigger(hour=watch_hour, minute=watch_minute, day_of_week="mon-fri"),
        id="sync_watchlist",
        name="同步自选股行情",
        replace_existing=True,
    )

    kline_hour, kline_minute = _shift_time(hour, minute, 7)
    fund_hour, fund_minute = _shift_time(hour, minute, 8)

    scheduler.add_job(
        _sync_watchlist_klines,
        CronTrigger(hour=kline_hour, minute=kline_minute, day_of_week="mon-fri"),
        id="sync_watchlist_klines",
        name="预加载自选股K线",
        replace_existing=True,
    )

    scheduler.add_job(
        _sync_watchlist_fundamentals,
        CronTrigger(hour=fund_hour, minute=fund_minute, day_of_week="mon-fri"),
        id="sync_watchlist_fundamentals",
        name="同步自选股基本面",
        replace_existing=True,
    )

    scheduler.add_job(
        _run_watchlist_rating,
        CronTrigger(hour=rating_hour, minute=rating_minute, day_of_week="mon-fri"),
        id="run_rating",
        name="自选股评级",
        replace_existing=True,
    )

    scheduler.add_job(
        _run_daily_review,
        CronTrigger(hour=review_hour, minute=review_minute, day_of_week="mon-fri"),
        id="run_review",
        name="每日复盘",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        "Scheduler started: market@%02d:%02d, news@hourly, watchlist@%02d:%02d, "
        "klines@%02d:%02d, fund@%02d:%02d, rating@%02d:%02d, review@%02d:%02d",
        hour, minute, watch_hour, watch_minute, kline_hour, kline_minute,
        fund_hour, fund_minute, rating_hour, rating_minute, review_hour, review_minute,
    )


async def _sync_market_data():
    """同步市场总览到 SQLite。"""
    logger.info("[Scheduler] Syncing market data...")
    try:
        from app.api.v1.sync import _sync_market
        await _sync_market()
        logger.info("[Scheduler] Market data synced")
    except Exception as e:
        logger.error("[Scheduler] Market sync failed: %s", e)


async def _sync_news_data():
    """同步新闻到 SQLite。"""
    logger.info("[Scheduler] Syncing news data...")
    try:
        from app.api.v1.sync import _sync_news
        await _sync_news()
        logger.info("[Scheduler] News data synced")
    except Exception as e:
        logger.error("[Scheduler] News sync failed: %s", e)


async def _sync_watchlist_quotes():
    """同步自选股行情到 SQLite。"""
    logger.info("[Scheduler] Syncing watchlist quotes...")
    try:
        from app.api.v1.sync import _sync_watchlist_quotes as sync_wl
        await sync_wl()
        logger.info("[Scheduler] Watchlist quotes synced")
    except Exception as e:
        logger.error("[Scheduler] Watchlist sync failed: %s", e)


async def _sync_watchlist_klines():
    """预加载自选股 K 线历史到 SQLite。"""
    logger.info("[Scheduler] Preloading watchlist klines...")
    try:
        from app.api.v1.sync import _preload_watchlist_klines
        await _preload_watchlist_klines()
        logger.info("[Scheduler] Watchlist klines preloaded")
    except Exception as e:
        logger.error("[Scheduler] Watchlist klines preload failed: %s", e)


async def _sync_watchlist_fundamentals():
    """同步自选股基本面数据到 SQLite。"""
    logger.info("[Scheduler] Syncing watchlist fundamentals...")
    try:
        from app.api.v1.sync import _sync_fundamentals
        await _sync_fundamentals()
        logger.info("[Scheduler] Watchlist fundamentals synced")
    except Exception as e:
        logger.error("[Scheduler] Watchlist fundamentals sync failed: %s", e)


async def _run_watchlist_rating():
    """对自选股执行评级。"""
    logger.info("[Scheduler] Running watchlist ratings...")
    try:
        from sqlalchemy import select
        from app.database import async_session
        from app.models.watchlist import Watchlist as WatchlistItem
        from app.core.rating_engine import rate_stock
        from app.models.rating import Rating

        async with async_session() as db:
            stmt = select(WatchlistItem)
            result = await db.execute(stmt)
            items = result.scalars().all()

            if not items:
                logger.info("[Scheduler] Watchlist empty, skip rating")
                return

            today = date.today()
            for item in items:
                try:
                    r = await rate_stock(item.code, name=item.name, market=item.market)
                    if r:
                        rating_obj = Rating(
                            code=item.code,
                            name=r.get("name", item.name),
                            market=r.get("market", item.market),
                            date=today,
                            model_type="quant_ai",
                            trend_score=r.get("trend_score"),
                            momentum_score=r.get("momentum_score"),
                            volatility_score=r.get("volatility_score"),
                            volume_score=r.get("volume_score"),
                            value_score=r.get("value_score"),
                            sentiment_score=r.get("sentiment_score"),
                            fundamental_score=r.get("fundamental_score"),
                            ai_score=r.get("ai_score"),
                            total_score=r.get("total_score"),
                            rating=r.get("rating", ""),
                            reason={"text": r.get("reason", "")},
                        )
                        db.add(rating_obj)
                except Exception as e:
                    logger.error("[Scheduler] Rating failed for %s: %s", item.code, e)

            await db.commit()
            logger.info("[Scheduler] Ratings done for %d stocks", len(items))
    except Exception as e:
        logger.error("[Scheduler] Rating task failed: %s", e)


async def _run_daily_review():
    """执行每日复盘。"""
    logger.info("[Scheduler] Running daily review...")
    try:
        from sqlalchemy import select, desc
        from app.database import async_session
        from app.models.review import DailyReview
        from app.models.sentiment import SentimentCycleLog
        from app.core.limit_up_tracker import get_limit_up_data
        from app.core.review_engine import generate_daily_review
        from app.cache import cache_get

        today = date.today()
        async with async_session() as db:
            existing = await db.execute(
                select(DailyReview).where(DailyReview.date == today)
            )
            if existing.scalar_one_or_none():
                logger.info("[Scheduler] Review already exists for today")
                return

            limit_up_data = await get_limit_up_data()

            market_overview = None
            try:
                cached = await cache_get("sr:market:overview")
                if cached and isinstance(cached, dict):
                    market_overview = cached
            except Exception:
                pass

            prev_stmt = select(SentimentCycleLog).order_by(desc(SentimentCycleLog.date)).limit(7)
            prev_result = await db.execute(prev_stmt)
            prev_rows = prev_result.scalars().all()
            prev_phases = [r.cycle_phase for r in reversed(prev_rows) if r.cycle_phase]

            result = await generate_daily_review(limit_up_data, market_overview, prev_phases)

            leader = limit_up_data.get("market_leader") or {}
            leader_name = ""
            if isinstance(leader, dict):
                leader_name = str(leader.get("name", "") or "")

            cycle = result.get("cycle_result", {})
            ai_reason = cycle.get("ai_reason", "") if isinstance(cycle, dict) else ""

            review_obj = DailyReview(
                date=today,
                status=result.get("status", "draft"),
                market_sentiment=result.get("market_sentiment", ""),
                sentiment_cycle_main=result.get("sentiment_cycle_main", ""),
                market_height=result.get("market_height", 0),
                market_leader=leader_name,
                dragon_stock=result.get("dragon_stock", leader_name),
                core_middle_stock=result.get("core_middle_stock", ""),
                market_ladder=result.get("market_ladder", ""),
                total_volume=result.get("total_volume", ""),
                total_limit_up=result.get("total_limit_up", 0),
                first_board_count=result.get("first_board_count", 0),
                broken_board_count=result.get("broken_board_count", 0),
                sentiment_detail=ai_reason,
                main_sector=result.get("main_sector", ""),
                sub_sector=result.get("sub_sector", ""),
                main_sectors=result.get("main_sectors", ""),
                sub_sectors=result.get("sub_sectors", ""),
                market_style=result.get("market_style", ""),
                broken_boards=result.get("broken_boards", ""),
                broken_high_stock=result.get("broken_high_stock", ""),
                conclusion_quadrant=result.get("conclusion_quadrant", ""),
                review_summary=result.get("review_summary", ""),
                next_day_plan=result.get("next_day_plan", ""),
                next_day_prediction=result.get("next_day_prediction", ""),
                next_day_mode=result.get("next_day_mode", ""),
                applicable_strategy=result.get("applicable_strategy", ""),
                suggested_position=result.get("suggested_position", ""),
                ai_review_draft=result.get("review_summary", ""),
                ai_next_day_suggestion=result.get("next_day_plan", ""),
                is_confirmed=(result.get("status", "draft") == "published"),
            )
            db.add(review_obj)
            log = SentimentCycleLog(
                date=today,
                cycle_phase=cycle.get("phase", ""),
                market_height=cycle.get("height", 0),
                main_sector=result.get("main_sector", ""),
                transition_note=cycle.get("ai_reason", ""),
            )
            db.add(log)
            await db.commit()

            logger.info("[Scheduler] Daily review completed: %s", cycle.get("phase", ""))
    except Exception as e:
        logger.error("[Scheduler] Review task failed: %s", e)
