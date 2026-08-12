"""Token-budget repository tests (unit, in-memory sqlite)."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.infra.database import KeyUsageLog, get_session_factory
from repository.keys_crud import sum_user_tokens_since


async def _insert_usage(user_id: str, tokens: int, created_at: datetime) -> None:
    factory = get_session_factory()
    async with factory() as session:
        session.add(
            KeyUsageLog(
                id=str(uuid4()),
                user_id=user_id,
                run_id=None,
                provider="test",
                model="test-model",
                tokens_prompt=tokens,
                tokens_completion=0,
                tokens_total=tokens,
                created_at=created_at,
            )
        )
        await session.commit()


class TestSumUserTokensSince:
    async def test_sums_only_rows_within_window(self):
        now = datetime.now(UTC)
        await _insert_usage("u1", 100, now - timedelta(hours=1))
        await _insert_usage("u1", 250, now - timedelta(minutes=5))
        await _insert_usage("u1", 500, now - timedelta(days=2))
        await _insert_usage("u2", 900, now)

        since = now - timedelta(days=1)
        assert await sum_user_tokens_since("u1", since) == 350
        assert await sum_user_tokens_since("u2", since) == 900

    async def test_zero_when_no_rows(self):
        assert await sum_user_tokens_since("nobody", datetime.now(UTC)) == 0
