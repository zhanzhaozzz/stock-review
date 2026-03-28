from fastapi import APIRouter

from app.api.v1 import market, ratings, watchlist, news, sync

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(market.router, prefix="/market", tags=["market"])
api_router.include_router(ratings.router, prefix="/ratings", tags=["ratings"])
api_router.include_router(watchlist.router, prefix="/watchlist", tags=["watchlist"])
api_router.include_router(news.router, prefix="/news", tags=["news"])
api_router.include_router(sync.router, prefix="/sync", tags=["sync"])
