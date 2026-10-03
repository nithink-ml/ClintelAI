"""Production API rate limiting and abuse prevention with Redis and in-memory fallback."""

import logging
import time
from collections import defaultdict
from typing import Any

from fastapi import HTTPException, Request, Response, status

from app.core.config import settings

logger = logging.getLogger("clintelai")

# In-memory storage fallback for local dev or when Redis is unreachable
# Structure: { key: [(timestamp_epoch, count)] }
_IN_MEMORY_RATE_LIMITS: dict[str, list[float]] = defaultdict(list)
_REDIS_CLIENT: Any = None
_REDIS_AVAILABLE: bool | None = None


async def get_redis_client():
    """Returns an active Redis async connection or None if unavailable."""
    global _REDIS_CLIENT, _REDIS_AVAILABLE
    if _REDIS_AVAILABLE is False and not settings.REDIS_FALLBACK_IN_MEMORY:
        return None

    if _REDIS_CLIENT is None:
        try:
            import redis.asyncio as aioredis

            client = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_timeout=1.0,
                socket_connect_timeout=1.0,
            )
            await client.ping()
            _REDIS_CLIENT = client
            _REDIS_AVAILABLE = True
            logger.info(f"Connected to Redis rate limiter at {settings.REDIS_URL}")
        except Exception as exc:
            _REDIS_AVAILABLE = False
            _REDIS_CLIENT = None
            logger.warning(
                f"Redis unavailable for rate limiting ({exc!s}). Using in-memory fallback: {settings.REDIS_FALLBACK_IN_MEMORY}"
            )
            return None
    return _REDIS_CLIENT


class RateLimiter:
    """FastAPI dependency for sliding-window rate limiting per IP or authenticated user."""

    def __init__(
        self,
        requests: int = 60,
        window_seconds: int = 60,
        prefix: str = "default",
    ):
        self.requests = requests
        self.window_seconds = window_seconds
        self.prefix = prefix

    def _get_client_identifier(self, request: Request) -> str:
        """Extracts client identity from authorization token or forwarded IP."""
        # 1. Check for authenticated user token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            if token:
                try:
                    from app.core.security import decode_token

                    payload = decode_token(token)
                    user_sub = payload.get("sub")
                    if user_sub:
                        return f"user:{user_sub}"
                except Exception as exc:
                    logger.debug("Token extraction skipped in rate limiter: %s", exc)

        # 2. Check X-Forwarded-For header for reverse proxies (Nginx / Cloudflare)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
            if client_ip:
                return f"ip:{client_ip}"

        # 3. Direct client host
        if request.client and request.client.host:
            return f"ip:{request.client.host}"

        return "unknown_client"

    async def __call__(self, request: Request, response: Response) -> None:
        if not settings.RATE_LIMIT_ENABLED:
            return

        client_id = self._get_client_identifier(request)
        rate_key = f"ratelimit:{self.prefix}:{client_id}"
        current_time = time.time()

        redis = await get_redis_client()

        if redis is not None and _REDIS_AVAILABLE:
            try:
                # Redis sliding-window counter via pipeline
                pipe = redis.pipeline()
                pipe.incr(rate_key)
                pipe.ttl(rate_key)
                results = await pipe.execute()
                count = results[0]
                ttl = results[1]

                # Set expiry on first request in window
                if ttl == -1 or count == 1:
                    await redis.expire(rate_key, self.window_seconds)
                    ttl = self.window_seconds

                remaining = max(0, self.requests - count)
                reset_sec = max(1, ttl)

                response.headers["X-RateLimit-Limit"] = str(self.requests)
                response.headers["X-RateLimit-Remaining"] = str(remaining)
                response.headers["X-RateLimit-Reset"] = str(reset_sec)

                if count > self.requests:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=(
                            f"Too many requests to {self.prefix} API. "
                            f"Rate limit exceeded: {self.requests} requests per {self.window_seconds}s. "
                            f"Please retry after {reset_sec} seconds."
                        ),
                        headers={"Retry-After": str(reset_sec)},
                    )
                return
            except HTTPException:
                raise
            except Exception as exc:
                logger.warning(
                    f"Redis rate limit check failed ({exc!s}). Falling back to in-memory."
                )

        # In-Memory Sliding Window Fallback
        timestamps = _IN_MEMORY_RATE_LIMITS[rate_key]
        window_start = current_time - self.window_seconds

        # Prune old timestamps
        _IN_MEMORY_RATE_LIMITS[rate_key] = [t for t in timestamps if t > window_start]
        count = len(_IN_MEMORY_RATE_LIMITS[rate_key]) + 1
        remaining = max(0, self.requests - count)

        reset_sec = self.window_seconds
        if _IN_MEMORY_RATE_LIMITS[rate_key]:
            oldest_in_window = _IN_MEMORY_RATE_LIMITS[rate_key][0]
            reset_sec = max(1, int(self.window_seconds - (current_time - oldest_in_window)))

        response.headers["X-RateLimit-Limit"] = str(self.requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_sec)

        if count > self.requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Too many requests to {self.prefix} API. "
                    f"Rate limit exceeded: {self.requests} requests per {self.window_seconds}s. "
                    f"Please retry after {reset_sec} seconds."
                ),
                headers={"Retry-After": str(reset_sec)},
            )

        _IN_MEMORY_RATE_LIMITS[rate_key].append(current_time)
