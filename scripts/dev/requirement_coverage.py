#!/usr/bin/env python3
"""
Generate requirement coverage report.

Usage:
    python scripts/requirement_coverage.py
    python scripts/requirement_coverage.py --check  # Exit with error if coverage < threshold
"""

import argparse
import re
import sys
from pathlib import Path


class RequirementInfo:
    def __init__(self, req_id: str, description: str, tests: list[str], covered: bool):
        self.req_id = req_id
        self.description = description
        self.tests = tests
        self.covered = covered


def parse_requirements_file(file_path: Path) -> dict[str, RequirementInfo]:
    """Parse the REQUIREMENTS.md file to extract requirements."""
    requirements = {}
    content = file_path.read_text()

    # Find all requirement rows in tables
    pattern = r'\|\s*(REQ-[\w-]+)\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*([✅❌])\s*\|'
    matches = re.findall(pattern, content)

    for req_id, desc, tests, status in matches:
        req_id = req_id.strip()
        desc = desc.strip()
        tests_str = tests.strip()
        covered = status.strip() == '✅'

        # Parse test names
        test_names = []
        if tests_str.startswith('`') and tests_str.endswith('`'):
            test_names = [t.strip('`') for t in tests_str.split('`, `')]
        elif tests_str.startswith('❌'):
            test_names = []

        requirements[req_id] = RequirementInfo(
            req_id=req_id,
            description=desc,
            tests=test_names,
            covered=covered
        )

    return requirements


def scan_test_files(test_dir: Path) -> dict[str, list[str]]:
    """Scan test files to find requirement markers."""
    req_tests: dict[str, list[str]] = {}

    for test_file in test_dir.rglob("test_*.py"):
        content = test_file.read_text()

        # Find all requirement markers
        pattern = r'@pytest\.mark\.requirement\(["\']([^"\']+)["\']\)'
        matches = re.findall(pattern, content)

        for req_id in matches:
            if req_id not in req_tests:
                req_tests[req_id] = []
            req_tests[req_id].append(test_file.stem)

    return req_tests


def generate_report(requirements: dict[str, RequirementInfo],
                    test_coverage: dict[str, list[str]],
                    check_mode: bool = False,
                    threshold: int = 80) -> int:
    """Generate requirement coverage report."""
    print("\n" + "=" * 70)
    print("REQUIREMENT COVERAGE REPORT")
    print("=" * 70)

    total_reqs = len(requirements)
    covered_reqs = sum(1 for r in requirements.values() if r.covered)
    coverage_pct = (covered_reqs / total_reqs * 100) if total_reqs > 0 else 0

    print(f"\n📊 Overall Coverage: {covered_reqs}/{total_reqs} ({coverage_pct:.1f}%)")
    print(f"🎯 Threshold: {threshold}%")

    # Group by module
    modules: dict[str, list[RequirementInfo]] = {}
    for req in requirements.values():
        module = req.req_id.split('-')[1] if '-' in req.req_id else 'Other'
        if module not in modules:
            modules[module] = []
        modules[module].append(req)

    print("\n📋 Coverage by Module:")
    print("-" * 50)

    for module, reqs in sorted(modules.items()):
        module_covered = sum(1 for r in reqs if r.covered)
        module_total = len(reqs)
        module_pct = (module_covered / module_total * 100) if module_total > 0 else 0
        status = "✅" if module_pct >= threshold else "⚠️"
        print(f"  {status} {module}: {module_covered}/{module_total} ({module_pct:.1f}%)")

    # Show uncovered requirements
    uncovered = [r for r in requirements.values() if not r.covered]
    if uncovered:
        print(f"\n❌ Uncovered Requirements ({len(uncovered)}):")
        print("-" * 50)
        for req in uncovered:
            print(f"  • {req.req_id}: {req.description}")

    # Show test mapping
    print(f"\n🧪 Test Coverage Mapping:")
    print("-" * 50)

    for req_id, tests in sorted(test_coverage.items()):
        req_info = requirements.get(req_id)
        if req_info:
            status = "✅" if req_info.covered else "⚠️"
            print(f"  {status} {req_id}: {', '.join(tests)}")

    # Check threshold
    if check_mode and coverage_pct < threshold:
        print(f"\n❌ Coverage {coverage_pct:.1f}% is below threshold {threshold}%")
        return 1

    print("\n" + "=" * 70)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate requirement coverage report")
    parser.add_argument("--check", action="store_true",
                        help="Exit with error if coverage < threshold")
    parser.add_argument("--threshold", type=int, default=80,
                        help="Coverage threshold percentage (default: 80)")
    parser.add_argument("--requirements-file", type=str,
                        default="backend/tests/REQUIREMENTS.md",
                        help="Path to requirements file")
    parser.add_argument("--test-dir", type=str,
                        default="backend/tests/",
                        help="Path to test directory")

    args = parser.parse_args()

    req_file = Path(args.requirements_file)
    test_dir = Path(args.test_dir)

    if not req_file.exists():
        print(f"❌ Requirements file not found: {req_file}")
        return 1

    requirements = parse_requirements_file(req_file)
    test_coverage = scan_test_files(test_dir)

    return generate_report(requirements, test_coverage, args.check, args.threshold)


if __name__ == "__main__":
    sys.exit(main())
