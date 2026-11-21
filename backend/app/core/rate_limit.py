import asyncio
import hashlib
import logging
import time

from fastapi import Request
from fastapi.responses import JSONResponse
from redis import Redis
from redis.exceptions import RedisError
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.config import get_settings

logger = logging.getLogger(__name__)
_INCREMENT_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return count
"""


def _bucket(path: str) -> tuple[str, int, int] | None:
    if path.startswith("/api/v1/auth/login"):
        return "auth-login", 10, 60
    if path.startswith("/api/v1/auth/register"):
        return "auth-register", 5, 60
    if path == "/api/v1/resumes/upload":
        return "resume-upload", 5, 60
    if path.startswith("/api/v1/interviews/"):
        return "interviews", 20, 60
    if path.startswith("/api/v1/matching/"):
        return "matching", 30, 60
    return None


class RedisRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        settings = get_settings()
        bucket = _bucket(request.url.path)
        if settings.redis_url is None or bucket is None:
            return await call_next(request)

        name, limit, window_seconds = bucket
        client_ip = request.headers.get("x-real-ip") or (
            request.client.host if request.client else "unknown"
        )
        identity = hashlib.sha256(f"{client_ip}:{name}".encode()).hexdigest()
        redis_client = Redis.from_url(
            settings.redis_url,
            socket_timeout=1,
            socket_connect_timeout=1,
        )
        key = f"careerlens:rate-limit:{name}:{identity}"
        try:
            count = await asyncio.to_thread(
                redis_client.eval,
                _INCREMENT_SCRIPT,
                1,
                key,
                window_seconds,
            )
        except RedisError as exc:
            logger.error(
                "Rate limiting backend unavailable",
                extra={"bucket": name, "error_type": type(exc).__name__},
            )
            return JSONResponse(
                status_code=503,
                content={"detail": "Request protection is temporarily unavailable."},
            )
        finally:
            await asyncio.to_thread(redis_client.close)

        if int(count) > limit:
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": str(window_seconds)},
                content={"detail": "Too many requests. Please try again later."},
            )
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - int(count)))
        return response
