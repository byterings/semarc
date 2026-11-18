import threading
import time

from fastapi import Request

from config.settings import settings
from core.errors import ApiError


class RateLimiter:
    """Fixed-window, in-process rate limiting for authentication endpoints."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._windows: dict[str, tuple[int, float]] = {}

    def hit(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            count, reset = self._windows.get(key, (0, now + settings.auth_rate_window))
            if reset <= now:
                count, reset = 0, now + settings.auth_rate_window
            count += 1
            self._windows[key] = (count, reset)

        if count > settings.auth_rate_limit:
            retry = max(1, int(reset - now))
            raise ApiError(
                429,
                "too_many_requests",
                f"Too many attempts. Try again in {retry} seconds.",
                headers={"Retry-After": str(retry)},
            )


limiter = RateLimiter()


def auth_rate_limit(request: Request) -> None:
    """Dependency for POST /register and POST /login, keyed by path and client address."""
    client = request.client.host if request.client else "unknown"
    limiter.hit(f"{request.url.path}|{client}")
