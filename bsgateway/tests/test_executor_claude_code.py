"""Tests for Claude Code CLI executor."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bsgateway.executor.claude_code import ClaudeCodeExecutor


@pytest.fixture
def executor() -> ClaudeCodeExecutor:
    return ClaudeCodeExecutor()


class TestClaudeCodeExecutor:
    async def test_successful_execution(self, executor: ClaudeCodeExecutor) -> None:
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"hello world", b"")
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await executor.execute("say hello", {"task_id": "t1"})

        assert result.success is True
        assert result.stdout == "hello world"
        assert result.error_message is None

    async def test_failed_execution(self, executor: ClaudeCodeExecutor) -> None:
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"", b"error occurred")
        mock_proc.returncode = 1

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await executor.execute("bad prompt", {"task_id": "t2"})

        assert result.success is False
        assert result.error_category == "tool"
        assert "error occurred" in (result.error_message or "")

    async def test_timeout_returns_error(self, executor: ClaudeCodeExecutor) -> None:
        mock_proc = AsyncMock()
        mock_proc.communicate.side_effect = TimeoutError()
        mock_proc.returncode = None
        mock_proc.kill = MagicMock()
        mock_proc.wait = AsyncMock()

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await executor.execute("slow prompt", {"task_id": "t3"})

        assert result.success is False
        assert result.error_category == "environment"
        assert "timed out" in (result.error_message or "").lower()

    async def test_cli_not_found_returns_error(self, executor: ClaudeCodeExecutor) -> None:
        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=FileNotFoundError("claude not found"),
        ):
            result = await executor.execute("prompt", {"task_id": "t4"})

        assert result.success is False
        assert result.error_category == "environment"

    async def test_rate_limit_retry(self, executor: ClaudeCodeExecutor) -> None:
        """Rate-limited first call, success on retry."""
        rate_limited = AsyncMock()
        rate_limited.communicate.return_value = (b"hit your limit", b"")
        rate_limited.returncode = 1

        success = AsyncMock()
        success.communicate.return_value = (b"done", b"")
        success.returncode = 0

        call_count = 0

        async def mock_exec(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return rate_limited if call_count == 1 else success

        with (
            patch("asyncio.create_subprocess_exec", side_effect=mock_exec),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            result = await executor.execute("prompt", {"task_id": "t5"})

        assert result.success is True
        assert result.stdout == "done"
        assert call_count == 2

    async def test_uses_workspace_from_context(self, executor: ClaudeCodeExecutor) -> None:
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"ok", b"")
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
            await executor.execute("prompt", {"workspace_dir": "/my/workspace"})

        _, kwargs = mock_exec.call_args
        assert kwargs["cwd"] == "/my/workspace"

    def test_supported_task_types(self, executor: ClaudeCodeExecutor) -> None:
        types = executor.supported_task_types()
        assert "coding" in types

    async def test_passes_prompt_via_stdin(self, executor: ClaudeCodeExecutor) -> None:
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"ok", b"")
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            await executor.execute("my prompt text", {"task_id": "t6"})

        mock_proc.communicate.assert_called_once_with(input=b"my prompt text")
