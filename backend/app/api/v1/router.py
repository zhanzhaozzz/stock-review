from fastapi import APIRouter

from app.api.v1 import market

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(market.router, prefix="/market", tags=["market"])
