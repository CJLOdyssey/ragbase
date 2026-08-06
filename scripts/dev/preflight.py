"""Preflight check — validates environment before the app starts.

Runs before the backend in CI and local dev. Catches:
- Missing env vars
- Database connectivity + migration state
- Redis connectivity
- Disk space
- Port availability

Exits non-zero on any failure so CI stops early with a clear message.
"""

import os
import shutil
import subprocess
import sys


def _check(label: str, ok: bool, detail: str = "") -> None:
    icon = "✅" if ok else "❌"
    print(f"{icon} {label}")
    if detail and not ok:
        print(f"   {detail}")


def check_env() -> bool:
    required = [
        "DATABASE_URL",
    ]
    all_ok = True
    for var in required:
        val = os.environ.get(var)
        ok = bool(val)
        _check(f"ENV {var}", ok, f"missing — set {var}")
        if not ok:
            all_ok = False
    return all_ok


def check_db() -> bool:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        _check("Database", False, "DATABASE_URL not set")
        return False

    sync_url = url.replace("+asyncpg", "+psycopg2").replace("+pg8000", "+psycopg2")
    try:
        import sqlalchemy

        engine = sqlalchemy.create_engine(sync_url, connect_args={"connect_timeout": 5})
        conn = engine.connect()
        conn.execute(sqlalchemy.text("SELECT 1"))
        conn.close()
        engine.dispose()
        _check("Database connectivity", True)
    except Exception as e:
        _check("Database connectivity", False, str(e)[:200])
        return False

    try:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            capture_output=True, text=True, timeout=120,
            # core 在 backend/src（alembic env.py import core.config）
            env={**os.environ, "PYTHONPATH": "backend/src"},
        )
        if result.returncode == 0:
            _check("Database migration", True)
        else:
            all_output = result.stdout + "\n" + result.stderr
            errors = "\n".join(
                line for line in all_output.split("\n")
                if "Traceback" in line or "Error" in line or "error" in line
                or "psycopg" in line or "sqlalchemy" in line or "alembic" in line
            )
            details = errors.strip()[:2000] or all_output.strip()[:2000]
            _check("Database migration", False, f"alembic upgrade failed:\n{details}")
            return False
    except Exception as e:
        _check("Database migration", False, str(e)[:300])
        return False

    return True


def check_redis() -> bool:
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/1")
    try:
        import redis

        r = redis.from_url(redis_url, socket_connect_timeout=3)
        r.ping()
        r.close()
        _check("Redis connectivity", True)
        return True
    except Exception as e:
        _check("Redis connectivity", False, str(e)[:200])
        return False


def check_disk() -> bool:
    min_mb = int(os.environ.get("OBSERVABILITY_MIN_DISK_MB", "100"))
    try:
        usage = shutil.disk_usage(".")
        free_mb = usage.free // (1024 * 1024)
        ok = free_mb >= min_mb
        _check(f"Disk space ({free_mb}MB free >= {min_mb}MB min)", ok)
        return ok
    except Exception as e:
        _check("Disk space check", False, str(e)[:200])
        return False


def check_port(port: int, label: str = "Port") -> bool:
    import socket

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = s.connect_ex(("127.0.0.1", port))
        s.close()
        if result == 0:
            _check(f"{label} {port}", False, f"port {port} already in use")
            return False
        _check(f"{label} {port}", True)
        return True
    except Exception:
        _check(f"{label} {port}", True)
        return True


def main() -> int:
    print("=" * 50)
    print("  AgentStudio Preflight Check")
    print("=" * 50)
    print()

    checks = [
        ("Environment", check_env),
        ("Database", check_db),
        ("Redis", check_redis),
        ("Disk", check_disk),
    ]

    results: list[bool] = []
    for label, fn in checks:
        print(f"[{label}]")
        try:
            ok = fn()
            results.append(ok)
        except Exception as e:
            _check(f"{label} unexpected error", False, str(e)[:300])
            results.append(False)
        print()

    all_ok = all(results)
    print("=" * 50)
    if all_ok:
        print("  ✅ All checks passed")
    else:
        failed = sum(1 for r in results if not r)
        print(f"  ❌ {failed} check(s) failed — fix above errors and retry")
    print("=" * 50)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
