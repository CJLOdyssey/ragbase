"""FastAPI application entry point — app factory, middleware, routers, error handling."""

import importlib
import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.responses import Response

# Make `backend` importable when running as `python backend/src/core/app.py`.
sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Startup guard (must be first — catches pre-init crashes) ──────────────
from observability.startup_guard import mark_starting

mark_starting()

from routers import (
    admin_users,
    assets,
    attachments,
    auth,
    events,
    feedback,
    feedback_review,
    keys,
    knowledge_bases,
    models,
    monitoring,
    prompts,
    providers,
    query,
    rag_test,
    retrieval_logs,
    run_continue,
    runs,
    sessions,
    versions,
)

from core.app_lifespan import shutdown, startup
from core.env import env_float
from core.infra.logging_config import get_logger

logger = get_logger(__name__)

APP_VERSION = "0.1.0"


# Sentry APM — must be initialized before the FastAPI app is built.
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
        traces_sample_rate=env_float("SENTRY_TRACES_SAMPLE_RATE", 0.1),
        profiles_sample_rate=env_float("SENTRY_PROFILES_SAMPLE_RATE", 0.1),
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


_is_production = os.environ.get("RAGBASE_ENV", "development") == "production"

app = FastAPI(
    title="RagBase API",
    description="企业级 RAG 知识库问答平台 API — 文档上传、索引、检索、生成",
    version=APP_VERSION,
    # OWASP A02: production 关闭公开 API 文档（Schema 是攻击面地图）。
    docs_url=None if _is_production else "/docs",
    redoc_url=None if _is_production else "/redoc",
    openapi_url=None if _is_production else "/openapi.json",
    lifespan=lifespan,
)


# ── OpenAPI security schemes ────────────────────────────────────────────────
# RagBase uses a global AuthMiddleware (Starlette) rather than per-route
# FastAPI Depends.  The middleware handles real authentication; this
# custom_openapi() function ensures the generated OpenAPI spec declares
# the Bearer scheme so that Swagger UI shows an "Authorize" button and
# client generators include JWT auth headers.
def custom_openapi() -> dict[str, Any]:
    """Build OpenAPI schema with security declarations.

    Called lazily by FastAPI on first /openapi.json request.  Caches the
    result on ``app.openapi_schema`` so subsequent calls are O(1).
    """
    if app.openapi_schema:
        return app.openapi_schema

    from fastapi.openapi.utils import get_openapi

    openapi_schema = get_openapi(
        title=app.title,
        description=app.description,
        version=app.version,
        routes=app.routes,
    )

    # Declare the Bearer JWT scheme (matches auth.py's JWT logic).
    openapi_schema.setdefault("components", {}).setdefault(
        "securitySchemes", {}
    )["Bearer"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "使用 /api/auth/login 获取的 JWT token",
    }

    # Apply Bearer globally — every route requires auth by default.
    # Individual routes can override with `security: []` if they are public.
    openapi_schema["security"] = [{"Bearer": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi  # type: ignore[method-assign]  # FastAPI hook override


from observability import router as debug_router

app.include_router(debug_router)


# Middleware — Starlette wraps in reverse add order, so the LAST add_middleware
# call is the OUTERMOST middleware. Execution order (request in):
# request-size → security-headers → CSP → CORS → request-log → auth → rate-limit.
from core.infra.rate_limit import RateLimitMiddleware

app.add_middleware(
    RateLimitMiddleware,
    rate=int(os.environ.get("RATE_LIMIT", "60")),
    window_seconds=int(os.environ.get("RATE_LIMIT_WINDOW", "60")),
)

from auth import AuthMiddleware

app.add_middleware(AuthMiddleware)

from core.infra.request_logger import RequestLogMiddleware

app.add_middleware(RequestLogMiddleware)

_cors_origins_raw = os.environ.get("CORS_ORIGINS", "")
if _cors_origins_raw:
    _cors_origins = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()]
elif _is_production:
    # OWASP A02: production 必须显式配置允许来源——不允许静默回退到开发默认值。
    _prod_origin = os.environ.get("CORS_ORIGIN")
    if not _prod_origin:
        raise RuntimeError(
            "RAGBASE_ENV=production requires CORS_ORIGINS (comma-separated) "
            "or CORS_ORIGIN to be set — refusing to start with permissive "
            "development defaults (OWASP A02)."
        )
    _cors_origins = [_prod_origin]
else:
    # Development defaults only when CORS_ORIGINS is not explicitly set.
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

from core.infra.csp_middleware import CSPMiddleware

app.add_middleware(CSPMiddleware)

from core.infra.security_headers_middleware import SecurityHeadersMiddleware

app.add_middleware(SecurityHeadersMiddleware)

from core.infra.request_size_middleware import RequestSizeLimitMiddleware

app.add_middleware(RequestSizeLimitMiddleware)


# ── Routers ─────────────────────────────────────────────────────────────────
routers = [auth, events, runs, run_continue, sessions, attachments, models, keys,
           prompts, providers, versions, assets, feedback, monitoring, feedback_review,
           query, retrieval_logs,
           admin_users, knowledge_bases, rag_test]
for r in routers:
    app.include_router(r.router)


# ── Exception handler ──────────────────────────────────────────────────────
@app.exception_handler(Exception)
def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle uncaught exceptions — log and return 500 JSON response."""
    logger.error(
        "Unhandled exception on %s %s: %s", request.method, request.url.path, exc, exc_info=True
    )
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
async def metrics(request: Request) -> Response:
    """Prometheus metrics endpoint.

    OWASP A02: when METRICS_TOKEN is set, the endpoint requires
    ``Authorization: Bearer <token>`` so internal operational data is not
    publicly readable; unset keeps the endpoint open (dev / scraped by an
    internal Prometheus with network-level access control).
    """
    metrics_token = os.environ.get("METRICS_TOKEN", "")
    if metrics_token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header != f"Bearer {metrics_token}":
            return JSONResponse(
                status_code=401,
                content={"detail": {"error": {"code": "AUTH_001", "message": "未授权"}}},
            )
    from core.infra.metrics import metrics_endpoint
    return metrics_endpoint()


@app.get("/api/health")
async def health() -> JSONResponse:
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
def version() -> dict[str, str]:
    """Application version endpoint."""
    return {"version": APP_VERSION}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8080"))
    logger.info("Starting uvicorn on 0.0.0.0:%d", port)
    uvicorn.run("backend.core.app:app", host="0.0.0.0", port=port, reload=True)
