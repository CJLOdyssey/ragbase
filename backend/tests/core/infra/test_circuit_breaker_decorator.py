"""Circuit breaker decorator + concurrency + shared instance tests."""

import asyncio

import pytest
from core.infra.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError, State, llm_circuit


class TestDecorator:
    @pytest.mark.asyncio
    async def test_success_path(self):
        cb = CircuitBreaker(name="d", maxfail=3)
        @cb
        async def f(x):
            return x * 2
        assert await f(5) == 10
        assert cb.state == State.CLOSED

    @pytest.mark.asyncio
    async def test_failure_path(self):
        cb = CircuitBreaker(name="d", maxfail=2)
        @cb
        async def f():
            raise ValueError
        with pytest.raises(ValueError):
            await f()
        with pytest.raises(ValueError):
            await f()
        assert cb.state == State.OPEN

    @pytest.mark.asyncio
    async def test_opens_and_blocks(self):
        cb = CircuitBreaker(name="d", maxfail=1)
        @cb
        async def f():
            raise RuntimeError
        with pytest.raises(RuntimeError):
            await f()
        with pytest.raises(CircuitBreakerOpenError):
            await f()

    @pytest.mark.asyncio
    async def test_passes_through_cb_error(self):
        cb = CircuitBreaker(name="d", maxfail=1)
        @cb
        async def f():
            return "ok"
        await cb._acquire()
        await cb._on_failure()
        with pytest.raises(CircuitBreakerOpenError):
            await f()

    @pytest.mark.asyncio
    async def test_recovery_after_half_open(self):
        cb = CircuitBreaker(name="d", maxfail=1, reset_timeout=0)
        @cb
        async def f(bad):
            if bad:
                raise ValueError
            return "ok"
        with pytest.raises(ValueError):
            await f(True)
        assert await f(False) == "ok"
        assert cb.state == State.CLOSED

    @pytest.mark.asyncio
    async def test_wrapped_func_raises_cb_error(self):
        cb = CircuitBreaker(name="d", maxfail=3)
        @cb
        async def f():
            raise CircuitBreakerOpenError("inner")
        with pytest.raises(CircuitBreakerOpenError):
            await f()
        assert cb.failures == 0


class TestConcurrency:
    @pytest.mark.asyncio
    async def test_concurrent_acquire(self):
        cb = CircuitBreaker(name="c", maxfail=10)
        async def fail():
            await cb._acquire()
            await cb._on_failure()
        await asyncio.gather(*(fail() for _ in range(5)))
        assert cb.failures == 5
        assert cb.state == State.CLOSED


class TestSharedCircuit:
    def test_llm_circuit_exists(self):
        assert llm_circuit.name == "llm_api"
        assert llm_circuit.state == State.CLOSED

    def test_env_var_config(self, monkeypatch):
        """llm_circuit 阈值接线自 env_int/env_float（LLM_CB_MAXFAIL/LLM_CB_RESET）。

        不 reload 模块——reload 会替换模块级 CircuitBreaker/State 类对象，
        使文件顶部 import 绑定的旧枚举与新实例的 == 比较失效（跨测试污染）。
        单例在 import 时固化配置（无法回溯当时 env），故只验证生产接线单元：
        env_int/env_float 对 LLM_CB_* 的解析路径（默认值 + 环境覆盖）。
        """
        from core.env import env_float, env_int

        monkeypatch.delenv("LLM_CB_MAXFAIL", raising=False)
        monkeypatch.delenv("LLM_CB_RESET", raising=False)
        assert env_int("LLM_CB_MAXFAIL", 5) == 5
        assert env_float("LLM_CB_RESET", 60) == 60.0

        monkeypatch.setenv("LLM_CB_MAXFAIL", "10")
        monkeypatch.setenv("LLM_CB_RESET", "120")
        assert env_int("LLM_CB_MAXFAIL", 5) == 10
        assert env_float("LLM_CB_RESET", 60) == 120.0
