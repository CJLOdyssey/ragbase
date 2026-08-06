"""
Pytest plugin for requirement coverage tracking.

Usage:
    @pytest.mark.requirement("REQ-AUTH-001")
    async def test_login_success():
        ...

Run with:
    pytest --requirement-coverage
"""

import pytest
from collections import defaultdict
from pathlib import Path
from typing import Optional


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("requirement-coverage", "Requirement Coverage")
    group.addoption(
        "--requirement-coverage",
        action="store_true",
        default=False,
        help="Generate requirement coverage report",
    )
    group.addoption(
        "--requirement-coverage-file",
        action="store",
        default="tests/REQUIREMENTS.md",
        help="Path to requirements file (default: tests/REQUIREMENTS.md)",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        'requirement(req_id): mark test as covering a specific requirement',
    )


class RequirementCoverageData:
    def __init__(self) -> None:
        self.marked_tests: dict[str, list[str]] = defaultdict(list)
        self.all_tests: list[str] = []
        self.failed_tests: list[str] = []


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(
    session: pytest.Session,
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    if not config.getoption("--requirement-coverage"):
        return

    data = RequirementCoverageData()

    for item in items:
        test_id = item.nodeid
        data.all_tests.append(test_id)

        for marker in item.iter_markers("requirement"):
            req_id = marker.args[0] if marker.args else "UNKNOWN"
            data.marked_tests[req_id].append(test_id)

    session.config._requirement_coverage_data = data


def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[None]
) -> None:
    if not item.config.getoption("--requirement-coverage"):
        return

    if call.when == "call" and call.excinfo is not None:
        data = getattr(item.config, "_requirement_coverage_data", None)
        if data:
            data.failed_tests.append(item.nodeid)


def pytest_sessionfinish(
    session: pytest.Session, exitstatus: pytest.ExitCode
) -> None:
    if not session.config.getoption("--requirement-coverage"):
        return

    data = getattr(session.config, "_requirement_coverage_data", None)
    if not data:
        return

    req_file = Path(session.config.getoption("--requirement-coverage-file"))

    print("\n" + "=" * 70)
    print("REQUIREMENT COVERAGE REPORT")
    print("=" * 70)

    if data.marked_tests:
        print(f"\nTotal requirements covered: {len(data.marked_tests)}")
        print(f"Total tests with markers: {sum(len(v) for v in data.marked_tests.values())}")
        print(f"Total tests run: {len(data.all_tests)}")
        print(f"Failed tests: {len(data.failed_tests)}")

        print("\nRequirements by test:")
        for req_id, tests in sorted(data.marked_tests.items()):
            status = "✅" if not any(t in data.failed_tests for t in tests) else "❌"
            print(f"  {status} {req_id}: {len(tests)} test(s)")
            for test in tests:
                marker = "❌" if test in data.failed_tests else "  "
                print(f"      {marker} {test}")
    else:
        print("\nNo requirement markers found in tests.")
        print("Add @pytest.mark.requirement('REQ-XXX') to your tests.")

    if req_file.exists():
        print(f"\nRequirements file: {req_file}")
        print("See tests/REQUIREMENTS.md for the full traceability matrix.")

    print("=" * 70 + "\n")
