import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import init_db, async_session
from app.cache import get_redis, close_redis
from app.api.v1.router import api_router
from app.services.seed import run_seed
from app.services.scheduler import setup_scheduler, get_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_preload_task = None


async def _startup_preload():
    """服务启动后自动预加载市场数据（非阻塞，不影响服务可用性）。"""
    await asyncio.sleep(3)
    try:
        from app.api.v1.sync import _sync_market
        result = await _sync_market()
        logger.info("Startup market preload done: %s", result)
    except Exception as e:
        logger.warning("Startup market preload failed: %s", e)
    try:
        from app.api.v1.sync import _preload_watchlist_klines
        result = await _preload_watchlist_klines()
        logger.info("Startup watchlist klines preload done: %s", result)
    except Exception as e:
        logger.warning("Startup watchlist klines preload failed: %s", e)
    try:
        from app.api.v1.sync import _sync_fundamentals
        result = await _sync_fundamentals()
        logger.info("Startup fundamentals preload done: %s", result)
    except Exception as e:
        logger.warning("Startup fundamentals preload failed: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _preload_task
    logger.info("Starting Stock Review...")
    await init_db()
    async with async_session() as session:
        await run_seed(session)
    r = await get_redis()
    try:
        await r.ping()
        logger.info("Redis connected")
    except Exception as e:
        logger.warning("Redis not available, cache will be skipped: %s", e)
    try:
        setup_scheduler()
        logger.info("Scheduler started")
    except Exception as e:
        logger.warning("Scheduler failed to start: %s", e)
    _preload_task = asyncio.create_task(_startup_preload())
    yield
    try:
        scheduler = get_scheduler()
        if scheduler.running:
            scheduler.shutdown(wait=False)
    except Exception:
        pass
    await close_redis()
    logger.info("Stock Review stopped")


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


import pathlib
from starlette.responses import FileResponse


static_dir = pathlib.Path(__file__).parent / "static"
if static_dir.exists():
    # 将 /assets 子目录挂载为静态文件服务（JS/CSS/图片等构建产物）
    assets_dir = static_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # SPA fallback：先尝试在 static_dir 根目录找对应文件（favicon.svg 等），
    # 找不到则返回 index.html 以支持前端 client-side 路由
    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        candidate = static_dir / full_path
        if candidate.is_file():
            return FileResponse(str(candidate))
        index = static_dir / "index.html"
        if index.exists():
            return FileResponse(str(index))
        return {"detail": "Not Found"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.api_port, reload=True)
