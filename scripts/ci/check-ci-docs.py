#!/usr/bin/env python3
"""CI docs consistency checks — .env.example coverage + module counts."""
import re
import pathlib
import sys

root = pathlib.Path(__file__).resolve().parent.parent.parent
errors = 0


def _extract_int(pattern: str, text: str, label: str) -> int:
    m = re.search(pattern, text)
    if m is None:
        print(f"❌ Could not find pattern '{pattern}' for {label}")
        sys.exit(1)
    return int(m.group(1))

# ── 1. .env.example coverage ──────────────────────────────────────────────
code_vars = set()
for py in sorted(root.rglob("backend/src/*.py")):
    for m in re.finditer(r'os\.environ\.get\(["\']([A-Z_]+)', py.read_text()):
        code_vars.add(m.group(1))

env_example = set()
for line in root.joinpath(".env.example").read_text().splitlines():
    m = re.match(r"^([A-Z_]+)=", line)
    if m:
        env_example.add(m.group(1))

missing = sorted(code_vars - env_example)
if missing:
    print("❌ Variables missing from .env.example:", " ".join(missing))
    errors += 1
else:
    print("✅ All env vars covered in .env.example")

# ── 2. Routers count ──────────────────────────────────────────────────────
router_dir = root.joinpath("backend/src/routers")
actual_routers = len([f for f in sorted(router_dir.glob("*.py")) if f.name != "__init__.py" and f.is_file()]) + \
         len([d for d in sorted(router_dir.iterdir()) if d.is_dir() and d.joinpath("__init__.py").exists()])
print(f"✅ Routers: {actual_routers}")

# ── 3. Repository count ───────────────────────────────────────────────────
actual_repos = len([f for f in sorted(root.joinpath("backend/src/repository").glob("*.py")) if f.name != "__init__.py"])
print(f"✅ Repository: {actual_repos}")

# ── 4. Workstation modules ────────────────────────────────────────────────
modules = [
    d for d in root.joinpath("frontend/src/components/studio/workspace").iterdir()
    if d.is_dir() and d.name != "shared" and d.name != "__tests__"
]
print(f"✅ Workstation modules: {len(modules)}")

# ── Report ────────────────────────────────────────────────────────────────
if errors:
    print(f"❌ {errors} doc inconsistency(ies) found")
    sys.exit(1)
print("✅ All checks passed")
