"""Benchmark: HTTP endpoint latency and throughput."""

from __future__ import annotations

import asyncio
import statistics
import time

import httpx
import pytest

pytestmark = pytest.mark.benchmark

BASE = "http://localhost:8080"


class TestHTTPBenchmark:
    """Basic HTTP performance benchmarks for key endpoints."""

    # Number of concurrent requests
    CONCURRENCY = 20
    # Total requests to fire
    TOTAL_REQUESTS = 200

    @pytest.mark.parametrize("endpoint", [
        "/api/health",
        "/api/agents",
        "/api/prompts",
    ])
    def test_endpoint_latency(self, endpoint: str):
        """Measure p50/p95/p99 latency for a GET endpoint."""
        url = f"{BASE}{endpoint}"

        async def _fire(sem: asyncio.Semaphore) -> float:
            async with sem:
                t0 = time.monotonic()
                async with httpx.AsyncClient(timeout=10) as client:
                    r = await client.get(url)
                elapsed = time.monotonic() - t0
                assert r.status_code < 500, f"{endpoint} returned {r.status_code}"
                return elapsed

        async def _run():
            sem = asyncio.Semaphore(self.CONCURRENCY)
            tasks = [_fire(sem) for _ in range(self.TOTAL_REQUESTS)]
            results = await asyncio.gather(*tasks)
            return sorted(results)

        latencies = asyncio.run(_run())
        p50 = statistics.median(latencies)
        p95 = latencies[int(len(latencies) * 0.95)]
        p99 = latencies[int(len(latencies) * 0.99)]
        avg = statistics.mean(latencies)
        throughput = len(latencies) / sum(latencies)

        print(f"\n  {endpoint}:")
        print(f"    Requests: {len(latencies)} @ {self.CONCURRENCY} concurrent")
        print(f"    p50={p50*1000:.1f}ms p95={p95*1000:.1f}ms p99={p99*1000:.1f}ms")
        print(f"    avg={avg*1000:.1f}ms throughput={throughput:.0f} req/s")

        # Sanity thresholds (loose — adjust based on CI environment)
        assert p99 < 5.0, f"p99 latency {p99*1000:.0f}ms exceeds 5s threshold"
