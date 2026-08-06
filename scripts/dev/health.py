#!/usr/bin/env python3
"""Server health monitor — exit non-zero if unhealthy.

Usage:
    python scripts/dev/health.py [--port 8081] [--check-orphans]
"""
import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request


def check_health(base_url: str) -> dict:
    url = f"{base_url}/api/health"
    resp = urllib.request.urlopen(url, timeout=10)
    return json.loads(resp.read())


def check_orphans() -> list[str]:
    """Find orphaned Python processes (PPID=1)."""
    try:
        result = subprocess.run(
            ["ps", "--ppid", "1", "-o", "pid,comm,etime,args"],
            capture_output=True, text=True, timeout=5,
        )
        lines = result.stdout.strip().split("\n")[1:]
        orphans = []
        for line in lines:
            if not line.strip():
                continue
            parts = line.split(None, 3)
            if len(parts) >= 2 and "python" in parts[1].lower():
                orphans.append(line.strip())
        return orphans
    except (subprocess.SubprocessError, FileNotFoundError):
        return []


def check_cpu_load() -> dict:
    """Check system load vs CPU count."""
    try:
        nproc = os.cpu_count() or 1
        load1, load5, load15 = os.getloadavg()
        return {
            "load_1min": round(load1, 2),
            "load_5min": round(load5, 2),
            "load_15min": round(load15, 2),
            "cpu_count": nproc,
            "overloaded": load1 > nproc * 0.8,
        }
    except OSError:
        return {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Server health monitor")
    parser.add_argument("--port", type=int, default=8080, help="Backend port")
    parser.add_argument("--check-orphans", action="store_true", help="Check for orphaned processes")
    args = parser.parse_args()

    base_url = f"http://localhost:{args.port}"
    exit_code = 0

    # 1. Health endpoint
    try:
        data = check_health(base_url)
        status = data.get("status", "unknown")
        print(f"[HEALTH] Status: {status}")
        if status != "healthy":
            print(f"[HEALTH] Degraded: {json.dumps(data.get('checks', {}))}")
            exit_code = 1
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        print(f"[HEALTH] FAILED — cannot reach {base_url}/api/health: {e}")
        exit_code = 1

    # 2. Orphaned processes
    if args.check_orphans:
        orphans = check_orphans()
        if orphans:
            print(f"[HEALTH] WARNING: {len(orphans)} orphaned Python processes:")
            for o in orphans:
                print(f"  {o}")
            exit_code = exit_code or 1
        else:
            print("[HEALTH] No orphaned Python processes")

    # 3. CPU load
    cpu_info = check_cpu_load()
    if cpu_info:
        load_str = f"{cpu_info['load_1min']} / {cpu_info['cpu_count']} cores"
        if cpu_info.get("overloaded"):
            print(f"[HEALTH] WARNING: CPU overloaded — load {load_str}")
            exit_code = exit_code or 1
        else:
            print(f"[HEALTH] CPU load OK — {load_str}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
