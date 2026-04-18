from fastapi import APIRouter

from app.api.v1 import market, ratings, watchlist, news, sync
from app.api.v1 import analysis, review, strategy, operations, quote
from app.api.v1 import combat_desk, candidate_pool, post_market_review
from app.api.v1 import generate, validate
from app.config import get_settings

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(market.router, prefix="/market", tags=["market"])
api_router.include_router(ratings.router, prefix="/ratings", tags=["ratings"])
api_router.include_router(watchlist.router, prefix="/watchlist", tags=["watchlist"])
api_router.include_router(news.router, prefix="/news", tags=["news"])
api_router.include_router(sync.router, prefix="/sync", tags=["sync"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
api_router.include_router(review.router, prefix="/review", tags=["review"])
api_router.include_router(strategy.router, prefix="/strategies", tags=["strategies"])
api_router.include_router(operations.router, prefix="/operations", tags=["operations"])
api_router.include_router(quote.router, prefix="/quotes", tags=["quotes"])
api_router.include_router(combat_desk.router, prefix="/combat-desk", tags=["combat-desk"])
api_router.include_router(candidate_pool.router, prefix="/candidates", tags=["candidates"])
api_router.include_router(post_market_review.router, prefix="/post-market-review", tags=["post-market-review"])
api_router.include_router(generate.router, prefix="/generate", tags=["generate"])
api_router.include_router(validate.router, prefix="/validate", tags=["validate"])


@api_router.get("/health", tags=["system"])
async def health():
    settings = get_settings()
    return {"status": "ok", "app": settings.app_name}
