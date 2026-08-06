"""FastAPI application entry point: app factory, middleware, router registration, and error handling."""

import importlib
import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Startup guard (must be first — catches pre-init crashes) ──────────────
from observability.startup_guard import mark_starting

mark_starting()

from routers import (
    assets,
    attachments,
    auth,
    generation,
    keys,
    models,
    prompts,
    providers,
    run_continue,
    runs,
    sessions,
    versions,
)

from core.app_lifespan import shutdown, startup
from core.infra.logging_config import get_logger

logger = get_logger(__name__)

def _safe_float(key: str, default: float) -> float:
    try:
        return float(os.environ[key])
    except (KeyError, ValueError, TypeError):
        return default


# ── Sentry APM (must be initialized before FastAPI app) ─────────────────────
_sentry_dsn = os.environ.get("SENTRY_DSN", "")
if _sentry_dsn:
    sentry_sdk: Any = importlib.import_module("sentry_sdk")
    FastApiIntegration: Any = importlib.import_module("sentry_sdk.integrations.fastapi").FastApiIntegration
    StarletteIntegration: Any = importlib.import_module("sentry_sdk.integrations.starlette").StarletteIntegration

    sentry_sdk.init(
        dsn=_sentry_dsn,
        environment=os.environ.get("SENTRY_ENVIRONMENT", "development"),
        integrations=[
            StarletteIntegration(),
            FastApiIntegration(),
        ],
        traces_sample_rate=_safe_float("SENTRY_TRACES_SAMPLE_RATE", 0.1),
        profiles_sample_rate=_safe_float("SENTRY_PROFILES_SAMPLE_RATE", 0.1),
        send_default_pii=False,
    )
    logger.info("Sentry initialized (environment=%s)", os.environ.get("SENTRY_ENVIRONMENT", "development"))
else:
    logger.info("Sentry DSN not configured — error tracking disabled")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager — runs startup and shutdown hooks."""
    await startup(app)
    yield
    await shutdown(app)


app = FastAPI(
    title="ContentStudio API",
    description="内容创作助手 API — 文案生成、图文合成、素材库管理",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# ── Debug routes ───────────────────────────────────────────────────────────
from observability import router as debug_router

app.include_router(debug_router)


# ── Middleware (order matters — outermost first) ────────────────────────────
from core.infra.rate_limit import RateLimitMiddleware

_rate_limit_user_raw = os.environ.get("RATE_LIMIT_USER")
app.add_middleware(
    RateLimitMiddleware,
    rate=int(os.environ.get("RATE_LIMIT", "60")),
    window_seconds=int(os.environ.get("RATE_LIMIT_WINDOW", "60")),
    user_rate=int(_rate_limit_user_raw) if _rate_limit_user_raw else None,
)

from auth import AuthMiddleware

app.add_middleware(AuthMiddleware)

from core.infra.request_logger import RequestLogMiddleware

app.add_middleware(RequestLogMiddleware)

_cors_origins_raw = os.environ.get("CORS_ORIGINS", "")
if _cors_origins_raw:
    _cors_origins = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()]
else:
    # Development defaults only when CORS_ORIGINS is not explicitly set
    _cors_origins = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:8080",
        "http://localhost:8081",
        "http://localhost:8082",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:8081",
        "http://127.0.0.1:8082",
    ]
    _prod_origin = os.environ.get("CORS_ORIGIN")
    if _prod_origin:
        _cors_origins.append(_prod_origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-User-ID", "X-Requested-With", "Accept"],
)

# ── CSP (Content-Security-Policy) ─────────────────────────────────────────
from core.infra.csp_middleware import CSPMiddleware

app.add_middleware(CSPMiddleware)

# ── Security headers (X-Content-Type-Options, X-Frame-Options, HSTS) ─────
from core.infra.security_headers_middleware import SecurityHeadersMiddleware

app.add_middleware(SecurityHeadersMiddleware)

# ── Request body size limit ──────────────────────────────────────────────
from core.infra.request_size_middleware import RequestSizeLimitMiddleware

app.add_middleware(RequestSizeLimitMiddleware)


# ── Routers ─────────────────────────────────────────────────────────────────
routers = [auth, runs, run_continue, sessions, attachments, models, keys,
           prompts, providers, versions, generation, assets]
for r in routers:
    app.include_router(r.router)


# ── Exception handler ──────────────────────────────────────────────────────
@app.exception_handler(Exception)
def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle uncaught exceptions — log and return 500 JSON response."""
    logger.error(
        "Unhandled exception on %s %s: %s", request.method, request.url.path, exc, exc_info=True
    )
    if isinstance(exc, HTTPException):
        raise exc
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误，请查看日志了解详情"},
    )


# ── Health / Metrics / Version ─────────────────────────────────────────────


def _get_process_cpu_seconds() -> float | None:
    """Return total CPU seconds consumed by this process (from /proc/pid/stat).

    Linux exposes utime+stime (fields 13-14) and cutime+cstime (fields 15-16)
    in clock ticks, where CLK_TCK is almost always 100.
    """
    try:
        with open(f"/proc/{os.getpid()}/stat") as f:
            parts = f.read().split()
        total_ticks = int(parts[13]) + int(parts[14]) + int(parts[15]) + int(parts[16])
        return round(total_ticks / 100, 1)  # CLK_TCK=100 on Linux
    except Exception:
        return None


@app.get("/api/metrics")
def metrics() -> Any:
    """Prometheus metrics endpoint."""
    from core.infra.metrics import metrics_endpoint
    return metrics_endpoint()


@app.get("/api/health")
async def health() -> Any:
    """Deep health check — verifies DB, Redis, and self CPU health."""
    from repository.health import check_database, check_redis

    db_status = await check_database()
    redis_status = await check_redis()
    cpu_seconds = _get_process_cpu_seconds()

    checks: dict[str, str] = {"database": db_status, "redis": redis_status}
    if cpu_seconds is not None:
        checks["cpu_seconds"] = str(cpu_seconds)

    healthy = db_status == "ok" and redis_status == "ok"
    status_code = 200 if healthy else 503
    return JSONResponse(
        content={"status": "healthy" if healthy else "degraded", "checks": checks},
        status_code=status_code,
    )


@app.get("/api/version")
def version() -> Any:
    """Application version endpoint."""
    return {"version": "0.1.0"}


# ── Main ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8080"))
    logger.info("Starting uvicorn on 0.0.0.0:%d", port)
    uvicorn.run("backend.core.app:app", host="0.0.0.0", port=port, reload=True)
