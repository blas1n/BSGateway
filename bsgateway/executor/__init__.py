"""Executor module — pluggable task executors (Claude Code CLI, Codex, etc.).

Executors are registered at import time. Use ``create_executor(name)`` to
obtain an instance by name (the ``litellm_model`` value stored in
``tenant_models`` when ``provider='executor'``).
"""

from __future__ import annotations

from bsgateway.executor.base import ExecutionResult, ExecutorProtocol
from bsgateway.executor.claude_code import ClaudeCodeExecutor
from bsgateway.executor.codex import CodexExecutor
from bsgateway.executor.registry import ExecutorRegistry

_registry = ExecutorRegistry()
_registry.register("claude_code", ClaudeCodeExecutor)
_registry.register("codex", CodexExecutor)


def create_executor(executor_type: str) -> ExecutorProtocol:
    """Create an executor instance by type name."""
    return _registry.get(executor_type)


__all__ = [
    "ExecutionResult",
    "ExecutorProtocol",
    "create_executor",
]
