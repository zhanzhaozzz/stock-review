"""Base class for all data fetchers."""
import logging
from abc import ABC, abstractmethod
from datetime import date

import pandas as pd

from app.data_provider.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


class BaseFetcher(ABC):
    """Abstract base for market data fetchers with unified interface."""

    name: str = "base"
    consecutive_failures: int = 0
    MAX_FAILURES: int = 3

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

    @abstractmethod
    async def get_daily(self, code: str, days: int = 120) -> pd.DataFrame | None:
        """Fetch daily OHLCV data.

        Returns DataFrame with columns: date, open, high, low, close, volume, turnover, change_pct
        or None on failure.
        """

    @abstractmethod
    async def get_realtime_quote(self, code: str) -> dict | None:
        """Fetch realtime quote. Returns dict with: price, change, change_pct, volume, etc."""

    async def get_index_daily(self, code: str, days: int = 60) -> pd.DataFrame | None:
        """Fetch index daily data. Default implementation returns None (not supported)."""
        return None

    async def get_stock_list(self, market: str = "A") -> pd.DataFrame | None:
        """Fetch stock list for a market. Default returns None."""
        return None

    def record_success(self):
        self.consecutive_failures = 0

    def record_failure(self):
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.MAX_FAILURES:
            logger.warning("%s has %d consecutive failures, will be deprioritized",
                           self.name, self.consecutive_failures)

    @property
    def is_degraded(self) -> bool:
        return self.consecutive_failures >= self.MAX_FAILURES
