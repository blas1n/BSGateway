"""Claude Code CLI executor — runs ``claude --print`` as a subprocess."""

from __future__ import annotations

import asyncio
import shutil
import sys
from typing import Any

import structlog

from bsgateway.executor.base import ExecutionResult
from bsgateway.executor.config import executor_settings

logger = structlog.get_logger(__name__)


class ClaudeCodeExecutor:
    """Execute tasks via the Claude Code CLI."""

    def __init__(self) -> None:
        self._claude_cmd = self._resolve_claude_cmd()
        self._timeout = executor_settings.claude_code_timeout_seconds
        self._total_timeout = executor_settings.claude_code_total_timeout_seconds
        self._rate_limit_retries = executor_settings.claude_code_rate_limit_retries
        self._rate_limit_wait = executor_settings.claude_code_rate_limit_wait_seconds

    def supported_task_types(self) -> list[str]:
        return ["coding", "refactor", "bugfix", "test"]

    @staticmethod
    def _resolve_claude_cmd() -> str:
        resolved = shutil.which("claude")
        if resolved:
            return resolved
        if sys.platform == "win32":
            resolved = shutil.which("claude.cmd")
            if resolved:
                return resolved
        return "claude"

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    async def execute(self, prompt: str, context: dict[str, Any]) -> ExecutionResult:
        task_id = context.get("task_id", "unknown")
        workspace = context.get("workspace_dir", ".")
        try:
            return await asyncio.wait_for(
                self._retry_loop(prompt, task_id, workspace),
                timeout=self._total_timeout,
            )
        except TimeoutError:
            logger.error("claude_cli_total_timeout", task_id=task_id, timeout=self._total_timeout)
            return ExecutionResult(
                success=False,
                error_message=f"Total execution timed out after {self._total_timeout}s",
                error_category="environment",
            )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _retry_loop(self, prompt: str, task_id: str, workspace: str) -> ExecutionResult:
        result: ExecutionResult | None = None
        for attempt in range(self._rate_limit_retries + 1):
            result = await self._run_cli(prompt, task_id, workspace)
            if result.success:
                return result
            output = (result.stdout or "") + (result.stderr or "")
            if not self._is_rate_limited(output):
                return result
            if attempt >= self._rate_limit_retries:
                logger.error(
                    "claude_cli_rate_limit_exhausted",
                    task_id=task_id,
                    attempts=attempt + 1,
                )
                return result
            logger.warning(
                "claude_cli_rate_limited",
                task_id=task_id,
                attempt=attempt + 1,
                wait_seconds=self._rate_limit_wait,
            )
            await asyncio.sleep(self._rate_limit_wait)
        assert result is not None
        return result

    @staticmethod
    def _is_rate_limited(output: str) -> bool:
        lower = output.lower()
        return "hit your limit" in lower or "rate limit" in lower

    async def _run_cli(self, prompt: str, task_id: str, workspace: str) -> ExecutionResult:
        process: asyncio.subprocess.Process | None = None
        try:
            logger.info("claude_cli_start", task_id=task_id, cwd=workspace)
            cmd_args = [self._claude_cmd, "--print", "--dangerously-skip-permissions"]
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
            out = stdout.decode("utf-8", errors="replace")
            err = stderr.decode("utf-8", errors="replace")
            logger.info("claude_cli_done", task_id=task_id, rc=rc, stdout_len=len(out))
            return ExecutionResult(
                success=rc == 0,
                stdout=out,
                stderr=err,
                error_message=err if rc != 0 else None,
                error_category="" if rc == 0 else "tool",
            )
        except TimeoutError:
            logger.error("claude_cli_timeout", task_id=task_id, timeout=self._timeout)
            return ExecutionResult(
                success=False,
                error_message=f"Execution timed out after {self._timeout}s",
                error_category="environment",
            )
        except (FileNotFoundError, PermissionError, OSError) as e:
            logger.error("claude_cli_env_error", task_id=task_id, error=str(e))
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
