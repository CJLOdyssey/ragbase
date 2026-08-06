"""Observability trace and error analysis utilities."""

from typing import Any

from observability.store import get_store

_KNOWN_ERRORS: dict[str, str] = {
    "UndefinedTable": "数据库表未创建，请运行 `alembic upgrade head`",
    "ProgrammingError": "SQL 执行错误，通常是表结构不匹配或权限问题",
    "InterfaceError": "数据库连接断开",
    " OperationalError": "数据库操作失败，检查连接和表状态",
    "TimeoutError": "操作超时，检查依赖服务（Redis/DB）状态",
    "ConnectionRefusedError": "连接被拒绝，目标服务未启动",
    "KeyError": "键不存在，通常是数据格式不匹配",
    "TypeError": "类型错误，通常是函数参数或格式不匹配",
    "AuthenticationError": "认证失败，检查 API Key 或令牌",
}


def analyze_error(error_type: str) -> str | None:
    """Return a suggestion string for known error types, or None."""
    for key, suggestion in _KNOWN_ERRORS.items():
        if key in error_type:
            return suggestion
    return None


def analyze_trace(trace_id: str) -> dict[str, Any]:
    """Analyze a trace by its ID, returning errors, slow spans, and suggestions."""
    store = get_store()
    events = store.by_trace(trace_id)
    if not events:
        return {"trace_id": trace_id, "events": [], "suggestion": None}

    error_events = [e for e in events if e["error_type"]]
    slow_events = [e for e in events if e["duration_ms"] and e["duration_ms"] > 1000]

    suggestions = set()
    for e in error_events:
        suggestion = analyze_error(e["error_type"])
        if suggestion:
            suggestions.add(suggestion)

    return {
        "trace_id": trace_id,
        "total_events": len(events),
        "errors": len(error_events),
        "slow_spans": len(slow_events),
        "error_events": [
            {
                "level": e["level"],
                "message": e["message"],
                "error_type": e["error_type"],
                "error_stack": e["error_stack"][:500] if e["error_stack"] else None,
                "duration_ms": e["duration_ms"],
                "logger": e["logger"],
            }
            for e in error_events[:10]
        ],
        "slow_events": [
            {
                "message": e["message"],
                "duration_ms": e["duration_ms"],
                "logger": e["logger"],
            }
            for e in slow_events[:10]
        ],
        "suggestion": list(suggestions)[0] if suggestions else None,
    }


def recent_errors_report(seconds: int = 300) -> list[dict[str, Any]]:
    """Generate an error report for recent traces within the time window."""
    store = get_store()
    traces = store.error_trace_ids(seconds=seconds)
    results = []
    for t in traces[:20]:
        report = analyze_trace(t["trace_id"])
        if report["errors"] > 0:
            results.append(report)
    return results
