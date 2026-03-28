import os
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
if not ENV_PATH.exists():
    ENV_PATH = BASE_DIR.parent / ".env"


class Settings(BaseSettings):
    app_name: str = "StockReview"
    app_env: str = "development"
    api_port: int = 8000

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/stock_review.db"

    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None

    # Tushare
    tushare_token: str = ""

    # Data provider priority
    data_provider_priority: str = "akshare,tushare,efinance"

    # LLM
    deepseek_api_key: str = ""
    deepseek_api_base: str = "https://api.deepseek.com"
    zhipu_api_key: str = ""
    moonshot_api_key: str = ""
    dashscope_api_key: str = ""

    rating_llm_models: str = "deepseek/deepseek-chat,zhipu/glm-4-flash,moonshot/moonshot-v1-8k"
    rating_llm_weights: str = "0.4,0.3,0.3"
    analysis_llm_model: str = "deepseek/deepseek-chat"
    utility_llm_model: str = "zhipu/glm-4-flash"

    # JWT
    jwt_secret_key: str = "change-me-to-a-random-string"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    admin_username: str = "admin"
    admin_password: str = "admin123"

    # Scheduler
    refresh_hour: int = 15
    refresh_minute: int = 30

    # Cache TTL
    cache_ttl_trading: int = 60
    cache_ttl_non_trading: int = 300

    model_config = {"env_file": str(ENV_PATH), "env_file_encoding": "utf-8", "extra": "ignore"}

    @property
    def provider_priority_list(self) -> list[str]:
        return [p.strip() for p in self.data_provider_priority.split(",")]

    @property
    def rating_model_list(self) -> list[str]:
        return [m.strip() for m in self.rating_llm_models.split(",")]

    @property
    def rating_weight_list(self) -> list[float]:
        return [float(w.strip()) for w in self.rating_llm_weights.split(",")]

    @property
    def data_dir(self) -> Path:
        d = BASE_DIR / "data"
        d.mkdir(parents=True, exist_ok=True)
        return d


@lru_cache
def get_settings() -> Settings:
    return Settings()
