"""Prometheus RED metrics for HTTP endpoint observability and application-level
monitoring (LLM calls, tool invocations, graph execution)."""

from prometheus_client import Counter, Gauge, Histogram, generate_latest
from starlette.responses import Response

# ── HTTP-level RED metrics ──────────────────────────────────────────────────

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    labelnames=["method", "endpoint", "status"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    labelnames=["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)

http_errors_total = Counter(
    "http_errors_total",
    "Total HTTP errors",
    labelnames=["method", "endpoint"],
)

# ── Application-level metrics ──────────────────────────────────────────────

llm_requests_total = Counter(
    "llm_requests_total",
    "Total LLM API calls",
    labelnames=["model", "status"],
)

llm_request_duration_seconds = Histogram(
    "llm_request_duration_seconds",
    "LLM API call duration in seconds",
    labelnames=["model"],
    buckets=(0.1, 0.5, 1, 2, 5, 10, 20, 40, 60, 120),
)

llm_tokens_total = Counter(
    "llm_tokens_total",
    "Total tokens consumed by LLM calls",
    labelnames=["model", "type"],
)

tool_invocations_total = Counter(
    "tool_invocations_total",
    "Total tool invocations",
    labelnames=["tool_name", "status"],
)

tool_invocation_duration_seconds = Histogram(
    "tool_invocation_duration_seconds",
    "Tool invocation duration in seconds",
    labelnames=["tool_name"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10, 30),
)

graph_runs_total = Counter(
    "graph_runs_total",
    "Total LangGraph runs",
    labelnames=["graph_type", "status"],
)

graph_run_duration_seconds = Histogram(
    "graph_run_duration_seconds",
    "Graph run duration in seconds",
    labelnames=["graph_type"],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600),
)

graph_rounds_per_run = Histogram(
    "graph_rounds_per_run",
    "Agent loop rounds per graph run",
    labelnames=["graph_type"],
    buckets=(1, 2, 3, 5, 8, 12, 20, 35, 50),
)

stream_messages_dropped_total = Counter(
    "stream_messages_dropped_total",
    "Total stream messages dropped due to buffer overflow",
)

active_runs = Gauge(
    "active_runs",
    "Number of currently executing runs",
    labelnames=["graph_type"],
)

db_pool_active = Gauge(
    "db_pool_active",
    "Active database connections in pool",
)

db_pool_overflow = Gauge(
    "db_pool_overflow",
    "Overflow database connections in pool",
)


def metrics_endpoint() -> Response:
    """Return Prometheus metrics in text format."""
    return Response(content=generate_latest(), media_type="text/plain; charset=utf-8")

