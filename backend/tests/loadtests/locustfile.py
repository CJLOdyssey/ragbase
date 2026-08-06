"""Locust load test for Virtual Team backend — multi-scenario with user types.

Usage:
    pip install locust

    # Web UI on http://localhost:8089:
    locust -f tests/loadtests/locustfile.py

    # Headless: 100 users, 10 spawn/s, 5 min:
    locust -f tests/loadtests/locustfile.py \
        --headless --users 100 --spawn-rate 10 --run-time 5m \
        --host http://localhost:8080

    # Or use the convenience script:
    bash tests/loadtests/run_load_test.sh
"""

from __future__ import annotations

import json
import os
import random
import time
from collections import defaultdict
from typing import Any

from locust import FastHttpUser, between, events, task
from locust.runners import MasterRunner, WorkerRunner

AUTH_USERNAME = os.environ.get("LOADTEST_USERNAME", "admin")
AUTH_PASSWORD = os.environ.get("LOADTEST_PASSWORD", "admin123")

# ── Shared utility ────────────────────────────────────────────────────────────


def _uid() -> str:
    return hex(random.randint(1, 99999))[2:]


def _login(client: Any) -> str | None:
    resp = client.post("/api/auth/login", json={
        "username": AUTH_USERNAME,
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
    """Browses endpoints — agents, tools, skills, sessions, prompts, teams, MCPs, keys, providers, commands, workflows, versions.

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
    def list_agents(self) -> None:
        self.client.get("/api/agents", name="list_agents")

    @task(3)
    def list_tools(self) -> None:
        self.client.get("/api/tools", name="list_tools")

    @task(3)
    def list_skills(self) -> None:
        self.client.get("/api/skills", name="list_skills")

    @task(2)
    def list_sessions(self) -> None:
        self.client.get("/api/sessions", name="list_sessions")

    @task(2)
    def list_prompts(self) -> None:
        self.client.get("/api/prompts", name="list_prompts")

    @task(2)
    def list_teams(self) -> None:
        self.client.get("/api/teams", name="list_teams")

    @task(2)
    def list_mcps(self) -> None:
        self.client.get("/api/mcps", name="list_mcps")

    @task(2)
    def list_keys(self) -> None:
        self.client.get("/api/keys", name="list_keys")

    @task(1)
    def list_providers(self) -> None:
        self.client.get("/api/providers", name="list_providers")

    @task(1)
    def list_commands(self) -> None:
        self.client.get("/api/commands", name="list_commands")

    @task(1)
    def list_workflows(self) -> None:
        self.client.get("/api/workflows", name="list_workflows")

    @task(1)
    def list_versions(self) -> None:
        self.client.get("/api/versions", name="list_versions")

    @task(1)
    def list_models(self) -> None:
        self.client.get("/api/models", name="list_models")

    @task(1)
    def get_tools_plugins(self) -> None:
        self.client.get("/api/tools/plugins", name="get_tools_plugins")


class PowerUser(FastHttpUser):
    """Creates a resource then deletes it; creates a session then sends a chat.

    Weight: 2 (less common, heavier operations).
    """

    weight = 2
    wait_time = between(1.0, 5.0)

    def on_start(self) -> None:
        _login(self.client)

    @task(3)
    def create_then_delete_agent(self) -> None:
        tag = _uid()
        payload = {
            "name": f"loadtest-agent-{tag}",
            "role_identifier": f"role_{tag}",
            "system_prompt": "You are a helpful assistant.",
            "model": "deepseek-v4-flash",
            "temperature": 0.7,
            "is_active": True,
            "icon": "🤖",
        }
        resp = self.client.post("/api/agents", json=payload, name="create_agent")
        if resp.status_code in (200, 201):
            agent = resp.json()
            agent_id = agent.get("id")
            if agent_id:
                self.client.delete(f"/api/agents/{agent_id}", name="delete_agent")

    @task(2)
    def create_then_delete_tool(self) -> None:
        tag = _uid()
        payload = {
            "name": f"loadtest-tool-{tag}",
            "category": "api",
            "description": "Load test tool.",
        }
        resp = self.client.post("/api/tools", json=payload, name="create_tool")
        if resp.status_code in (200, 201):
            tool = resp.json()
            tid = tool.get("id")
            if tid:
                self.client.delete(f"/api/tools/{tid}", name="delete_tool")

    @task(2)
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
                    "agent_id": None,
                    "user_message": "Hello, how are you?",
                }, name="start_chat_run")

    @task(1)
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
    def create_then_delete_skill(self) -> None:
        tag = _uid()
        payload = {
            "name": f"loadtest-skill-{tag}",
            "category": "general",
            "description": "Load test skill.",
        }
        resp = self.client.post("/api/skills", json=payload, name="create_skill")
        if resp.status_code in (200, 201):
            skill = resp.json()
            sid = skill.get("id")
            if sid:
                self.client.delete(f"/api/skills/{sid}", name="delete_skill")

    @task(1)
    def create_then_delete_mcp(self) -> None:
        tag = _uid()
        payload = {
            "name": f"loadtest-mcp-{tag}",
            "type": "stdio",
            "command": "python",
            "args": ["-m", "mcp"],
            "env": {},
        }
        resp = self.client.post("/api/mcps", json=payload, name="create_mcp")
        if resp.status_code in (200, 201):
            mcp = resp.json()
            mid = mcp.get("id")
            if mid:
                self.client.delete(f"/api/mcps/{mid}", name="delete_mcp")

    @task(1)
    def create_then_delete_team(self) -> None:
        tag = _uid()
        payload = {
            "name": f"loadtest-team-{tag}",
            "description": "Load test team.",
        }
        resp = self.client.post("/api/teams", json=payload, name="create_team")
        if resp.status_code == 201:
            team = resp.json()
            tid = team.get("id")
            if tid:
                self.client.delete(f"/api/teams/{tid}", name="delete_team")

    @task(1)
    def create_then_delete_workflow(self) -> None:
        tag = _uid()
        payload = {
            "name": f"loadtest-workflow-{tag}",
            "description": "Load test workflow.",
        }
        resp = self.client.post("/api/workflows", json=payload, name="create_workflow")
        if resp.status_code in (200, 201):
            wf = resp.json()
            wid = wf.get("id")
            if wid:
                self.client.delete(f"/api/workflows/{wid}", name="delete_workflow")


class AdminUser(FastHttpUser):
    """Checks admin stats, logs, activity; lists all sessions.

    Weight: 1 (least common, admin-only).
    """

    weight = 1
    wait_time = between(2.0, 8.0)

    def on_start(self) -> None:
        _login(self.client)

    @task(3)
    def admin_stats(self) -> None:
        self.client.get("/api/admin/stats", name="admin_stats")

    @task(2)
    def admin_logs(self) -> None:
        self.client.get("/api/admin/logs", name="admin_logs")

    @task(1)
    def admin_activity(self) -> None:
        self.client.get("/api/admin/activity", name="admin_activity")

    @task(1)
    def list_all_sessions(self) -> None:
        self.client.get("/api/sessions", name="admin_list_sessions")

    @task(1)
    def list_agents_for_audit(self) -> None:
        self.client.get("/api/agents", name="admin_list_agents")

    @task(1)
    def health_check(self) -> None:
        self.client.get("/api/health", name="admin_health")

    @task(1)
    def metrics(self) -> None:
        self.client.get("/api/metrics", name="admin_metrics")
