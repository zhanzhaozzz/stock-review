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


@asynccontextmanager
async def lifespan(app: FastAPI):
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


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": settings.app_name}


import pathlib

static_dir = pathlib.Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.api_port, reload=True)
