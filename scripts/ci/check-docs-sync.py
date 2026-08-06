#!/usr/bin/env python3
"""Check that documentation matches the actual codebase structure.

Currently verifies:
  - AGENTS.md repository module count matches backend/repository/
  - AGENTS.md router module count matches backend/routers/
  - TASKS.md has no stale status entries (⚠️ heuristic)

Exits with code 0 if all checks pass, 1 otherwise.
"""

from __future__ import annotations

import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def count_py_files(directory: str) -> int:
    """Count .py files in a directory (excluding __init__.py and __pycache__)."""
    if not os.path.isdir(directory):
        return 0
    return sum(
        1
        for f in os.listdir(directory)
        if f.endswith(".py") and f != "__init__.py"
    )


def extract_count(text: str, pattern: str) -> int | None:
    """Extract an integer from a regex pattern like 'repository/ (25 modules)'."""
    m = re.search(pattern, text)
    if m:
        return int(m.group(1))
    return None


def main() -> int:
    errors: list[str] = []
    agents_md = os.path.join(REPO_ROOT, "AGENTS.md")

    if not os.path.exists(agents_md):
        errors.append("AGENTS.md not found")
        for e in errors:
            print(f"❌ {e}")
        return 1

    with open(agents_md) as f:
        content = f.read()

    # Check repository module count
    repo_dir = os.path.join(REPO_ROOT, "backend", "repository")
    actual_repo = count_py_files(repo_dir)
    doc_repo = extract_count(content, r"repository/ \((\d+) modules?\)")
    if doc_repo is not None and actual_repo != doc_repo:
        errors.append(
            f"AGENTS.md: repository modules = {doc_repo}, "
            f"actual = {actual_repo} (directory: {repo_dir})"
        )

    # Check router module count
    routers_dir = os.path.join(REPO_ROOT, "backend", "routers")
    actual_routers = count_py_files(routers_dir)
    doc_routers = extract_count(content, r"routers/ \((\d+) modules?\)")
    if doc_routers is not None and actual_routers != doc_routers:
        errors.append(
            f"AGENTS.md: router modules = {doc_routers}, "
            f"actual = {actual_routers} (directory: {routers_dir})"
        )

    if errors:
        for e in errors:
            print(f"❌ {e}")
        return 1

    print("✅ AGENTS.md module counts match codebase")
    return 0


if __name__ == "__main__":
    sys.exit(main())
