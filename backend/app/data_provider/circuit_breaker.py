"""熔断器 — 参考 daily_stock_analysis 实现的 CircuitBreaker (CLOSED/OPEN/HALF_OPEN)。

用于保护外部数据源调用：连续失败达阈值后进入熔断状态（跳过调用），
冷却期结束后进入半开状态（允许少量探测请求），成功则恢复。
"""
import logging
import time
import threading
from typing import Optional

logger = logging.getLogger(__name__)

CLOSED = "closed"
OPEN = "open"
HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 3,
        cooldown_seconds: float = 300.0,
        half_open_max_calls: int = 1,
    ):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.half_open_max_calls = half_open_max_calls
        self._states: dict[str, dict] = {}
        self._lock = threading.Lock()

    def _get_state(self, source: str) -> dict:
        if source not in self._states:
            self._states[source] = {
                "state": CLOSED,
                "failures": 0,
                "last_failure_time": 0.0,
                "half_open_calls": 0,
            }
        return self._states[source]

    def allow_request(self, source: str) -> bool:
        with self._lock:
            s = self._get_state(source)
            if s["state"] == CLOSED:
                return True
            if s["state"] == OPEN:
                elapsed = time.time() - s["last_failure_time"]
                if elapsed >= self.cooldown_seconds:
                    s["state"] = HALF_OPEN
                    s["half_open_calls"] = 0
                    logger.info("[熔断器] %s 冷却结束，进入半开状态", source)
                    return True
                return False
            if s["state"] == HALF_OPEN:
                if s["half_open_calls"] < self.half_open_max_calls:
                    s["half_open_calls"] += 1
                    return True
                return False
            return True

    def record_success(self, source: str) -> None:
        with self._lock:
            s = self._get_state(source)
            if s["state"] == HALF_OPEN:
                logger.info("[熔断器] %s 半开探测成功，恢复正常", source)
            s["state"] = CLOSED
            s["failures"] = 0
            s["half_open_calls"] = 0

    def record_failure(self, source: str, error: Optional[str] = None) -> None:
        with self._lock:
            s = self._get_state(source)
            s["failures"] += 1
            s["last_failure_time"] = time.time()

            if s["state"] == HALF_OPEN:
                s["state"] = OPEN
                s["half_open_calls"] = 0
                logger.warning("[熔断器] %s 半开探测失败，继续熔断 %.0fs", source, self.cooldown_seconds)
            elif s["failures"] >= self.failure_threshold:
                s["state"] = OPEN
                logger.warning("[熔断器] %s 连续失败 %d 次，进入熔断 (冷却 %.0fs)",
                               source, s["failures"], self.cooldown_seconds)
                if error:
                    logger.warning("[熔断器] 最后错误: %s", error)

    def get_status(self) -> dict[str, str]:
        with self._lock:
            return {source: info["state"] for source, info in self._states.items()}

    def reset(self, source: Optional[str] = None) -> None:
        with self._lock:
            if source:
                self._states.pop(source, None)
            else:
                self._states.clear()


realtime_breaker = CircuitBreaker(failure_threshold=3, cooldown_seconds=300.0)
market_data_breaker = CircuitBreaker(failure_threshold=3, cooldown_seconds=300.0)
