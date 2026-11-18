import hashlib
import ipaddress
import logging
import threading
import time

from fastapi import Request

from config.settings import env, settings
from core.errors import ApiError

logger = logging.getLogger(__name__)


class RateLimiter:
    """Fixed-window rate limiting for authentication endpoints.

    With RATE_LIMIT_STORE=redis the counters live in Redis (shared by every process and
    server); otherwise, or when Redis cannot be reached, in this process.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._windows: dict[str, tuple[int, float]] = {}
        self._redis = None

    def hit(self, key: str) -> None:
        count, retry = self._count(key)
        if count > settings.auth_rate_limit:
            retry = max(1, retry)
            raise ApiError(
                429,
                "too_many_requests",
                f"Too many attempts. Try again in {retry} seconds.",
                headers={"Retry-After": str(retry)},
            )

    def _count(self, key: str) -> tuple[int, int]:
        if env("RATE_LIMIT_STORE", "local") == "redis":
            try:
                return self._count_in_redis(key)
            except Exception as error:  # noqa: BLE001 - any Redis failure falls back to local counting
                logger.error("Rate limiting falls back to local storage: %s", error)
        return self._count_locally(key)

    def _count_in_redis(self, key: str) -> tuple[int, int]:
        if self._redis is None:
            import redis

            self._redis = redis.Redis.from_url(env("REDIS_URL", "redis://127.0.0.1:6379/0"), socket_timeout=2, socket_connect_timeout=2)
        name = "semarc:rate-limit:" + hashlib.sha1(key.encode()).hexdigest()
        pipeline = self._redis.pipeline()
        pipeline.set(name, 0, ex=settings.auth_rate_window, nx=True)
        pipeline.incr(name)
        pipeline.ttl(name)
        _, count, ttl = pipeline.execute()
        return int(count), int(ttl)

    def _count_locally(self, key: str) -> tuple[int, int]:
        now = time.monotonic()
        with self._lock:
            count, reset = self._windows.get(key, (0, now + settings.auth_rate_window))
            if reset <= now:
                count, reset = 0, now + settings.auth_rate_window
            count += 1
            self._windows[key] = (count, reset)
        return count, int(reset - now)


limiter = RateLimiter()


def _address(value: str):
    try:
        address = ipaddress.ip_address(value.strip())
    except ValueError:
        return None
    return address.ipv4_mapped or address if isinstance(address, ipaddress.IPv6Address) else address


def _trusted(address, networks: list) -> bool:
    return address is not None and any(address.version == network.version and address in network for network in networks)


def client_ip(request: Request) -> str:
    """X-Forwarded-For is believed only when the direct peer is listed in TRUSTED_PROXIES;
    then the client is the rightmost forwarded address that is not itself a trusted proxy."""
    peer = request.client.host if request.client else "unknown"
    networks = []
    for item in env("TRUSTED_PROXIES", "").split(","):
        if item.strip():
            try:
                networks.append(ipaddress.ip_network(item.strip(), strict=False))
            except ValueError:
                logger.warning("Ignoring invalid TRUSTED_PROXIES entry: %s", item)
    forwarded = request.headers.get("x-forwarded-for")
    peer_address = _address(peer)
    if not forwarded or not networks or not _trusted(peer_address, networks):
        return str(peer_address or peer)
    hops = [hop.strip() for hop in forwarded.split(",") if hop.strip()]
    for index in range(len(hops) - 1, -1, -1):
        hop = _address(hops[index])
        if index == 0 or not _trusted(hop, networks):
            return str(hop or hops[index])
    return str(peer_address)


def auth_rate_limit(request: Request) -> None:
    """Dependency for authentication endpoints, keyed by path and client address."""
    limiter.hit(f"{request.url.path}|{client_ip(request)}")
