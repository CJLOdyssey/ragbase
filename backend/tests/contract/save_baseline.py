#!/usr/bin/env python3
"""Save the current OpenAPI schema as a baseline for contract diffing.

Usage:
    python tests/contract/save_baseline.py

Fetches http://localhost:8080/openapi.json and saves it to
tests/contract/openapi_baseline.json. If a previous baseline exists,
prints a summary of added, removed, and changed endpoints.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

HOST = "http://localhost:8080"
BASELINE_PATH = Path(__file__).resolve().parent / "openapi_baseline.json"


def _endpoints_from_paths(paths: dict[str, object]) -> set[str]:
    result: set[str] = set()
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method in methods:
            if method in ("get", "post", "put", "delete", "patch", "options", "head", "trace"):
                result.add(f"{method.upper()} {path}")
    return result


def _fetch_openapi() -> dict[str, object]:
    try:
        resp = httpx.get(f"{HOST}/openapi.json", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as exc:
        print(f"ERROR: Failed to fetch {HOST}/openapi.json: {exc}", file=sys.stderr)
        sys.exit(1)


def _load_previous() -> dict[str, object] | None:
    if not BASELINE_PATH.exists():
        return None
    try:
        return json.loads(BASELINE_PATH.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        print(f"WARNING: Could not read previous baseline: {exc}", file=sys.stderr)
        return None


def main() -> None:
    current = _fetch_openapi()
    previous = _load_previous()

    # Extract endpoint sets
    current_paths: dict[str, object] = current.get("paths", {})
    current_endpoints = _endpoints_from_paths(current_paths)

    prev_paths: dict[str, object] = {}
    prev_endpoints: set[str] = set()
    if previous is not None:
        prev_paths = previous.get("paths", {})
        prev_endpoints = _endpoints_from_paths(prev_paths)

    # Write baseline
    BASELINE_PATH.write_text(json.dumps(current, indent=2, ensure_ascii=False) + "\n")
    print(f"Baseline saved → {BASELINE_PATH}")
    print(f"  Endpoints: {len(current_endpoints)}")

    # Diff if previous exists
    if previous is not None:
        added = current_endpoints - prev_endpoints
        removed = prev_endpoints - current_endpoints
        changed = set()
        for path in set(current_paths.keys()) & set(prev_paths.keys()):
            if current_paths[path] != prev_paths[path]:
                changed.add(path)

        if added:
            print(f"\n  Added   (+{len(added)}):")
            for ep in sorted(added):
                print(f"    + {ep}")

        if removed:
            print(f"\n  Removed (-{len(removed)}):")
            for ep in sorted(removed):
                print(f"    - {ep}")

        if changed:
            print(f"\n  Changed (~{len(changed)}):")
            for path in sorted(changed):
                print(f"    ~ {path}")

        if not added and not removed and not changed:
            print("  No changes detected — contract is stable ✓")

    # Print version info
    info = current.get("info", {})
    if info:
        print(f"\n  Title: {info.get('title', 'N/A')}")
        print(f"  Version: {info.get('version', 'N/A')}")


if __name__ == "__main__":
    main()
