"""P9 error code presence."""

import pytest
from core.error_codes import ErrorCode


@pytest.mark.unit
def test_p9_error_codes_exist() -> None:
    assert ErrorCode.ASSET_NOT_FOUND.value == "ASSET_001"
    assert ErrorCode.TEMPLATE_NOT_FOUND.value == "COMPOSE_001"
    assert ErrorCode.GENERATION_LIMIT.value == "GEN_001"
