
import logging
import time
import uuid

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import RequestResponseEndpoint
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.database import get_engine
from app.core.rate_limit import RedisRateLimitMiddleware
from app.schemas.health import HealthResponse

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        description="AI-powered recruitment and career recommendation platform.",
        version=settings.app_version,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Accept", "Authorization", "Content-Type", "X-Request-ID"],
    )
    application.add_middleware(RedisRateLimitMiddleware)
    application.include_router(api_router, prefix=settings.api_v1_prefix)

    @application.middleware("http")
    async def log_request(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "HTTP request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response

    @application.get("/", tags=["health"])
    def home() -> dict[str, str]:
        return {"message": "Welcome to CareerLens AI", "status": "Running"}

    @application.get("/health", response_model=HealthResponse, tags=["health"])
    def health() -> HealthResponse:
        return HealthResponse(status="healthy")

    @application.get("/ready", response_model=HealthResponse, tags=["health"])
    def readiness() -> HealthResponse:
        try:
            with get_engine().connect() as connection:
                connection.execute(text("SELECT 1"))
            if settings.redis_url:
                redis_client = Redis.from_url(settings.redis_url, socket_timeout=1)
                try:
                    redis_client.ping()
                finally:
                    redis_client.close()
        except (SQLAlchemyError, RedisError) as exc:
            logger.warning(
                "Application readiness check failed",
                extra={"error_type": type(exc).__name__},
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="A required application dependency is unavailable.",
            ) from None
        return HealthResponse(status="healthy")

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = [
            {
                "loc": error.get("loc", ()),
                "msg": error.get("msg", "Invalid value."),
                "type": error.get("type", "value_error"),
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={"detail": errors, "request_id": request.state.request_id},
        )

    @application.exception_handler(StarletteHTTPException)
    async def handle_http_error(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        headers = exc.headers or {}
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "request_id": request.state.request_id},
            headers=headers,
        )

    @application.exception_handler(Exception)
    async def handle_unexpected_error(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error(
            "Unhandled request error",
            extra={
                "request_id": getattr(request.state, "request_id", None),
                "path": request.url.path,
                "error_type": type(exc).__name__,
            },
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "An unexpected server error occurred.",
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    return application


app = create_app()
