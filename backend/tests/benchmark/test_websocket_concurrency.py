"""Benchmark: WebSocket concurrent connections and message throughput."""

from __future__ import annotations

import asyncio
import json
import time

import pytest
import websockets

from tests.conftest import Api

def _clear_limits():
    import subprocess
    for container in ["virtual-team-redis", "agent-studio-redis"]:
        try:
            out = subprocess.run(
                ["docker", "exec", container, "redis-cli", "-n", "1", "KEYS", "ratelimit:*"],
                capture_output=True, text=True, timeout=5,
            )
            if out.stdout.strip():
                keys = out.stdout.strip().split("\n")
                subprocess.run(
                    ["docker", "exec", container, "redis-cli", "-n", "1", "DEL"] + keys,
                    capture_output=True, timeout=5,
                )
        except Exception:
            pass

pytestmark = pytest.mark.benchmark

WS_BASE = "ws://localhost:8080"


class TestWebSocketConcurrency:
    """Verify WebSocket handles multiple concurrent connections."""

    CONCURRENT_CLIENTS = 10

    def test_concurrent_ws_connections(self, api: Api):
        """Open N concurrent WS connections and verify they all receive status."""
        _clear_limits()
        # Create N runs
        run_ids = []
        for i in range(self.CONCURRENT_CLIENTS):
            r = api.post("/api/sessions", json={"title": f"ws-bench-{i}"})
            assert r.status_code == 201, r.text
            sid = r.json()["id"]
            r = api.post("/api/runs", json={"requirement": f"test {i}", "session_id": sid})
            if r.status_code != 200:
                continue  # skip if run creation fails (no LLM key)
            run_ids.append(r.json()["run_id"])

        if len(run_ids) < 2:
            pytest.skip("Need at least 2 runs for concurrency test")

        async def _connect_and_verify(run_id: str) -> float:
            """Connect to WS, measure time to receive first message."""
            uri = f"{WS_BASE}/ws/runs/{run_id}"
            t0 = time.monotonic()
            async with websockets.connect(uri) as ws:
                msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                elapsed = time.monotonic() - t0
                data = json.loads(msg)
                assert data["type"] == "status"
                assert data["status"] == "connected"
            return elapsed

        async def _run_all():
            tasks = [_connect_and_verify(rid) for rid in run_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            times = [r for r in results if isinstance(r, float)]
            errors = [r for r in results if isinstance(r, Exception)]
            return times, errors

        times, errors = asyncio.run(_run_all())

        assert len(errors) == 0, f"{len(errors)} connections failed: {errors[:3]}"
        assert len(times) == len(run_ids), f"Expected {len(run_ids)} connections, got {len(times)}"

        p50 = sorted(times)[len(times) // 2]
        p99 = sorted(times)[int(len(times) * 0.99)]
        print(f"\nWS Concurrency ({len(times)} clients): p50={p50*1000:.1f}ms p99={p99*1000:.1f}ms")

    def test_ws_message_throughput(self, api: Api):
        """Single WS connection - measure sustained message receive rate."""
        _clear_limits()
        r = api.post("/api/sessions", json={"title": "ws-throughput"})
        assert r.status_code == 201, r.text
        sid = r.json()["id"]
        r = api.post("/api/runs", json={"requirement": "throughput test", "session_id": sid})
        if r.status_code != 200:
            pytest.skip("Run creation failed (no LLM key)")
        run_id = r.json()["run_id"]

        async def _measure():
            uri = f"{WS_BASE}/ws/runs/{run_id}"
            msg_count = 0
            t0 = time.monotonic()
            async with websockets.connect(uri) as ws:
                try:
                    while True:
                        await asyncio.wait_for(ws.recv(), timeout=3.0)
                        msg_count += 1
                except (asyncio.TimeoutError, websockets.ConnectionClosed):
                    pass
            elapsed = time.monotonic() - t0
            return msg_count, elapsed

        msg_count, elapsed = asyncio.run(_measure())
        rate = msg_count / elapsed if elapsed > 0 else 0
        print(f"\nWS Throughput: {msg_count} messages in {elapsed:.1f}s ({rate:.1f} msg/s)")
