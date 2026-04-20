"""Standalone executor implementations for the BSGateway worker.

Kept self-contained so the worker package doesn't depend on the full
``bsgateway`` backend (which pulls in asyncpg, fastapi, etc.).
"""

from __future__ import annotations

import asyncio
import shutil
import sys
from dataclasses import dataclass
from typing import Any, Literal, Protocol, runtime_checkable


@dataclass
class ExecutionResult:
    success: bool
    stdout: str = ""
    stderr: str = ""
    error_message: str | None = None
    error_category: Literal["environment", "tool", "rate_limit", ""] = ""


@runtime_checkable
class ExecutorProtocol(Protocol):
    async def execute(self, prompt: str, context: dict[str, Any]) -> ExecutionResult: ...

    def supported_task_types(self) -> list[str]: ...


# ─── Claude Code CLI executor ─────────────────────────────────────────


class ClaudeCodeExecutor:
    """Run ``claude --print`` as a subprocess."""

    def __init__(
        self,
        timeout_seconds: int = 3600,
        total_timeout_seconds: int = 7200,
        rate_limit_retries: int = 3,
        rate_limit_wait_seconds: int = 60,
    ) -> None:
        self._cmd = self._resolve_cmd()
        self._timeout = timeout_seconds
        self._total_timeout = total_timeout_seconds
        self._rate_limit_retries = rate_limit_retries
        self._rate_limit_wait = rate_limit_wait_seconds

    @staticmethod
    def _resolve_cmd() -> str:
        resolved = shutil.which("claude")
        if resolved:
            return resolved
        if sys.platform == "win32":
            resolved = shutil.which("claude.cmd")
            if resolved:
                return resolved
        return "claude"

    def supported_task_types(self) -> list[str]:
        return ["coding", "refactor", "bugfix", "test"]

    async def execute(self, prompt: str, context: dict[str, Any]) -> ExecutionResult:
        task_id = context.get("task_id", "unknown")
        workspace = context.get("workspace_dir", ".")
        try:
            return await asyncio.wait_for(
                self._retry_loop(prompt, task_id, workspace),
                timeout=self._total_timeout,
            )
        except TimeoutError:
            return ExecutionResult(
                success=False,
                error_message=f"Total execution timed out after {self._total_timeout}s",
                error_category="environment",
            )

    async def _retry_loop(self, prompt: str, task_id: str, workspace: str) -> ExecutionResult:
        result: ExecutionResult | None = None
        for attempt in range(self._rate_limit_retries + 1):
            result = await self._run(prompt, task_id, workspace)
            if result.success:
                return result
            if not self._is_rate_limited((result.stdout or "") + (result.stderr or "")):
                return result
            if attempt >= self._rate_limit_retries:
                return result
            await asyncio.sleep(self._rate_limit_wait)
        assert result is not None
        return result

    @staticmethod
    def _is_rate_limited(output: str) -> bool:
        lower = output.lower()
        return "hit your limit" in lower or "rate limit" in lower

    async def _run(self, prompt: str, task_id: str, workspace: str) -> ExecutionResult:
        process: asyncio.subprocess.Process | None = None
        try:
            cmd_args = [self._cmd, "--print", "--dangerously-skip-permissions"]
            process = await asyncio.create_subprocess_exec(
                *cmd_args,
                cwd=workspace,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=prompt.encode("utf-8")),
                timeout=self._timeout,
            )
            rc = process.returncode
            return ExecutionResult(
                success=rc == 0,
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace"),
                error_message=stderr.decode("utf-8", errors="replace") if rc != 0 else None,
                error_category="" if rc == 0 else "tool",
            )
        except TimeoutError:
            return ExecutionResult(
                success=False,
                error_message=f"Execution timed out after {self._timeout}s",
                error_category="environment",
            )
        except (FileNotFoundError, PermissionError, OSError) as e:
            return ExecutionResult(
                success=False,
                error_message=str(e),
                error_category="environment",
            )
        finally:
            if process is not None and process.returncode is None:
                try:
                    process.kill()
                    await process.wait()
                except ProcessLookupError:
                    pass


# ─── Codex CLI executor (subprocess) ─────────────────────────────────


class CodexExecutor:
    """Run ``codex --quiet --full-auto`` as a subprocess."""

    def __init__(self, timeout_seconds: int = 3600) -> None:
        self._cmd = shutil.which("codex") or "codex"
        self._timeout = timeout_seconds

    def supported_task_types(self) -> list[str]:
        return ["coding", "refactor", "bugfix", "test"]

    async def execute(self, prompt: str, context: dict[str, Any]) -> ExecutionResult:
        workspace = context.get("workspace_dir", ".")
        process: asyncio.subprocess.Process | None = None
        try:
            process = await asyncio.create_subprocess_exec(
                self._cmd,
                "--quiet",
                "--full-auto",
                cwd=workspace,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=prompt.encode("utf-8")),
                timeout=self._timeout,
            )
            rc = process.returncode
            return ExecutionResult(
                success=rc == 0,
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace"),
                error_message=stderr.decode("utf-8", errors="replace") if rc != 0 else None,
                error_category="" if rc == 0 else "tool",
            )
        except TimeoutError:
            return ExecutionResult(
                success=False,
                error_message=f"Execution timed out after {self._timeout}s",
                error_category="environment",
            )
        except (FileNotFoundError, PermissionError, OSError) as e:
            return ExecutionResult(
                success=False,
                error_message=str(e),
                error_category="environment",
            )
        finally:
            if process is not None and process.returncode is None:
                try:
                    process.kill()
                    await process.wait()
                except ProcessLookupError:
                    pass


# ─── Factory ──────────────────────────────────────────────────────────


_EXECUTORS: dict[str, type] = {
    "claude_code": ClaudeCodeExecutor,
    "codex": CodexExecutor,
}


def create_executor(executor_type: str) -> ExecutorProtocol:
    cls = _EXECUTORS.get(executor_type)
    if cls is None:
        raise ValueError(f"Unknown executor type: {executor_type}")
    return cls()
