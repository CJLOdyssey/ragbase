"""Locust load test for RagBase — multi-scenario with user types.

Usage:
    pip install locust

    # Web UI on http://localhost:8089:
    locust -f tests/loadtests/locustfile.py

    # Headless: 100 users, 10 spawn/s, 5 min:
    locust -f tests/loadtests/locustfile.py \
        --headless --users 100 --spawn-rate 10 --run-time 5m \
        --host http://localhost:8081

    # Or use the convenience script:
    bash tests/loadtests/run_load_test.sh
"""

from __future__ import annotations

import json
import os
import random
from collections import defaultdict
from typing import Any

from locust import FastHttpUser, between, events, task
from locust.runners import MasterRunner, WorkerRunner

AUTH_EMAIL = os.environ.get("LOADTEST_EMAIL", "admin@example.com")
AUTH_PASSWORD = os.environ.get("LOADTEST_PASSWORD", "admin123")

# ── Shared utility ────────────────────────────────────────────────────────────


def _uid() -> str:
    return hex(random.randint(1, 99999))[2:]


def _login(client: Any) -> str | None:
    resp = client.post("/api/auth/login", json={
        "email": AUTH_EMAIL,
        "password": AUTH_PASSWORD,
    })
    if resp.status_code == 200:
        token = resp.json().get("access_token")
        if token:
            client.headers.update({"Authorization": f"Bearer {token}"})
            return token
    return None


# ── Response-time tracking for percentiles ────────────────────────────────────

_response_times: dict[str, list[float]] = defaultdict(list)


@events.request.add_listener
def _record_response_time(
    request_type: str,
    name: str,
    response_time: float,
    response_length: int,
    exception: Any,
    context: dict[str, Any],
    **kwargs: Any,
) -> None:
    _response_times[name].append(response_time)


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = min(int(pct / 100.0 * len(sorted_vals)), len(sorted_vals) - 1)
    return round(sorted_vals[idx], 2)


@events.quitting.add_listener
def _write_results(environment: Any, **kwargs: Any) -> None:
    report: dict[str, Any] = {
        "summary": {
            "total_requests": environment.stats.total.num_requests,
            "total_failures": environment.stats.total.num_failures,
            "avg_response_time": round(environment.stats.total.avg_response_time, 2),
        },
        "percentiles_by_endpoint": {},
        "global_percentiles": {},
    }

    all_times: list[float] = []
    for endpoint, times in sorted(_response_times.items()):
        all_times.extend(times)
        report["percentiles_by_endpoint"][endpoint] = {
            "requests": len(times),
            "p50": _percentile(times, 50),
            "p95": _percentile(times, 95),
            "p99": _percentile(times, 99),
        }

    report["global_percentiles"] = {
        "requests": len(all_times),
        "p50": _percentile(all_times, 50),
        "p95": _percentile(all_times, 95),
        "p99": _percentile(all_times, 99),
    }

    results_path = os.environ.get("LOCUST_RESULTS_FILE", "locust_results.json")
    with open(results_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n[Locust] Results written to {results_path}")
    print(f"[Locust] Global P50={report['global_percentiles']['p50']}ms "
          f"P95={report['global_percentiles']['p95']}ms "
          f"P99={report['global_percentiles']['p99']}ms")


@events.init.add_listener
def _on_locust_init(environment: Any, **kwargs: Any) -> None:
    if isinstance(environment.runner, MasterRunner):
        print("[Locust] Master runner initialized")
    elif isinstance(environment.runner, WorkerRunner):
        print("[Locust] Worker runner initialized")


# ═══════════════════════════════════════════════════════════════════════════════
# User Types
# ═══════════════════════════════════════════════════════════════════════════════


class ReadOnlyUser(FastHttpUser):
    """浏览端点：sessions/prompts/models/providers/keys/versions/health。

    Weight: 5 (most common user).
    """

    weight = 5
    wait_time = between(0.5, 3.0)

    def on_start(self) -> None:
        _login(self.client)

    @task(5)
    def health(self) -> None:
        self.client.get("/api/health", name="health")

    @task(4)
    def list_sessions(self) -> None:
        self.client.get("/api/sessions", name="list_sessions")

    @task(3)
    def list_prompts(self) -> None:
        self.client.get("/api/prompts", name="list_prompts")

    @task(3)
    def list_models(self) -> None:
        self.client.get("/api/models", name="list_models")

    @task(2)
    def list_keys(self) -> None:
        self.client.get("/api/keys", name="list_keys")

    @task(2)
    def list_providers(self) -> None:
        self.client.get("/api/providers", name="list_providers")

    @task(1)
    def list_versions(self) -> None:
        self.client.get("/api/versions", name="list_versions")

    @task(1)
    def list_assets(self) -> None:
        self.client.get("/api/assets", name="list_assets")

    @task(1)
    def retrieval_logs(self) -> None:
        self.client.get("/api/retrieval-logs", name="retrieval_logs")

    @task(1)
    def query_strategies(self) -> None:
        self.client.get("/api/query/strategies", name="query_strategies")


class PowerUser(FastHttpUser):
    """创建会话并发起问答；创建/删除提示词。

    Weight: 2 (less common, heavier operations).
    """

    weight = 2
    wait_time = between(1.0, 5.0)

    def on_start(self) -> None:
        _login(self.client)

    @task(3)
    def session_then_chat(self) -> None:
        tag = _uid()
        resp = self.client.post("/api/sessions", json={
            "title": f"loadtest-session-{tag}",
        }, name="create_session")
        if resp.status_code == 201:
            session = resp.json()
            sid = session.get("id")
            if sid:
                self.client.post("/api/runs", json={
                    "session_id": sid,
                    "requirement": "你好，请介绍一下知识库功能",
                }, name="start_chat_run")

    @task(2)
    def create_then_delete_prompt(self) -> None:
        tag = _uid()
        payload = {
            "name": f"loadtest-prompt-{tag}",
            "content": "You are a helpful assistant.",
            "category": "general",
        }
        resp = self.client.post("/api/prompts", json=payload, name="create_prompt")
        if resp.status_code in (200, 201):
            prompt = resp.json()
            pid = prompt.get("id")
            if pid:
                self.client.delete(f"/api/prompts/{pid}", name="delete_prompt")

    @task(1)
    def create_then_delete_session(self) -> None:
        tag = _uid()
        resp = self.client.post("/api/sessions", json={
            "title": f"loadtest-cleanup-{tag}",
        }, name="create_cleanup_session")
        if resp.status_code == 201:
            sid = resp.json().get("id")
            if sid:
                self.client.delete(f"/api/sessions/{sid}", name="delete_session")

    @task(1)
    def create_key_then_delete(self) -> None:
        tag = _uid()
        payload = {
            "name": f"loadtest-key-{tag}",
            "provider": "siliconflow",
            "api_key": "sk-loadtest-placeholder",
            "capabilities": ["llm"],
        }
        resp = self.client.post("/api/keys", json=payload, name="create_key")
        if resp.status_code in (200, 201):
            key = resp.json()
            kid = key.get("id")
            if kid:
                self.client.delete(f"/api/keys/{kid}", name="delete_key")


class AdminUser(FastHttpUser):
    """监控/管理端：monitoring、feedback、admin、debug。

    Weight: 1 (least common, admin-only).
    """

    weight = 1
    wait_time = between(2.0, 8.0)

    def on_start(self) -> None:
        _login(self.client)

    @task(3)
    def monitoring_summary(self) -> None:
        self.client.get("/api/monitoring/summary", name="monitoring_summary")

    @task(2)
    def monitoring_timeseries(self) -> None:
        self.client.get("/api/monitoring/timeseries", name="monitoring_timeseries")

    @task(2)
    def debug_health(self) -> None:
        self.client.get("/api/debug/health", name="debug_health")

    @task(1)
    def admin_users(self) -> None:
        self.client.get("/api/admin/users", name="admin_users")

    @task(1)
    def metrics(self) -> None:
        self.client.get("/api/metrics", name="admin_metrics")

    @task(1)
    def health_check(self) -> None:
        self.client.get("/api/health", name="admin_health")
