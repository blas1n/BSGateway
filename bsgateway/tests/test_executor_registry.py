"""Tests for executor registry and base types."""

from __future__ import annotations

import pytest

from bsgateway.executor.base import ExecutionResult, ExecutorProtocol
from bsgateway.executor.registry import ExecutorRegistry


class _StubExecutor:
    """Minimal executor for testing."""

    async def execute(self, prompt: str, context: dict) -> ExecutionResult:
        return ExecutionResult(success=True, stdout=prompt)

    def supported_task_types(self) -> list[str]:
        return ["coding"]


class TestExecutionResult:
    def test_success_result(self) -> None:
        r = ExecutionResult(success=True, stdout="output")
        assert r.success is True
        assert r.stdout == "output"
        assert r.error_message is None

    def test_failure_result(self) -> None:
        r = ExecutionResult(success=False, error_message="boom", error_category="tool")
        assert r.success is False
        assert r.error_message == "boom"
        assert r.error_category == "tool"


class TestExecutorRegistry:
    def test_register_and_get(self) -> None:
        reg = ExecutorRegistry()
        reg.register("stub", _StubExecutor)
        executor = reg.get("stub")
        assert isinstance(executor, _StubExecutor)

    def test_get_unknown_raises(self) -> None:
        reg = ExecutorRegistry()
        with pytest.raises(KeyError, match="stub"):
            reg.get("stub")

    def test_is_available(self) -> None:
        reg = ExecutorRegistry()
        assert reg.is_available("stub") is False
        reg.register("stub", _StubExecutor)
        assert reg.is_available("stub") is True

    def test_list_available(self) -> None:
        reg = ExecutorRegistry()
        reg.register("a", _StubExecutor)
        reg.register("b", _StubExecutor)
        assert sorted(reg.list_available()) == ["a", "b"]

    def test_duplicate_register_skips(self) -> None:
        reg = ExecutorRegistry()
        reg.register("stub", _StubExecutor)
        reg.register("stub", _StubExecutor)  # should not raise
        assert reg.is_available("stub")

    def test_stub_satisfies_protocol(self) -> None:
        assert isinstance(_StubExecutor(), ExecutorProtocol)
