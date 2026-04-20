"""Executor protocol and shared data types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol, runtime_checkable


@dataclass
class ExecutionResult:
    """Result of an executor invocation."""

    success: bool
    stdout: str = ""
    stderr: str = ""
    error_message: str | None = None
    error_category: Literal["environment", "tool", "rate_limit", ""] = ""


@runtime_checkable
class ExecutorProtocol(Protocol):
    """Structural interface every executor must satisfy."""

    async def execute(self, prompt: str, context: dict[str, Any]) -> ExecutionResult: ...

    def supported_task_types(self) -> list[str]: ...
