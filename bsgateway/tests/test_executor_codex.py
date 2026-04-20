"""Tests for Codex executor."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bsgateway.executor.codex import CodexExecutor


@pytest.fixture
def executor() -> CodexExecutor:
    return CodexExecutor()


class TestCodexExecutor:
    async def test_successful_execution(self, executor: CodexExecutor) -> None:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="generated code"))]

        with patch("bsgateway.executor.codex.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            result = await executor.execute("write a function", {})

        assert result.success is True
        assert result.stdout == "generated code"

    async def test_uses_context_model_override(self, executor: CodexExecutor) -> None:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="ok"))]

        with patch("bsgateway.executor.codex.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            await executor.execute("prompt", {"model": "openai/gpt-4o"})

        call_kwargs = mock_llm.call_args[1]
        assert call_kwargs["model"] == "openai/gpt-4o"

    async def test_uses_context_api_key(self, executor: CodexExecutor) -> None:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="ok"))]

        with patch("bsgateway.executor.codex.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            await executor.execute(
                "prompt", {"api_key": "sk-test", "api_base": "https://api.example.com"}
            )

        call_kwargs = mock_llm.call_args[1]
        assert call_kwargs["api_key"] == "sk-test"
        assert call_kwargs["api_base"] == "https://api.example.com"

    async def test_api_error_returns_failure(self, executor: CodexExecutor) -> None:
        with patch("bsgateway.executor.codex.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = RuntimeError("API error")
            result = await executor.execute("prompt", {})

        assert result.success is False
        assert "API error" in (result.error_message or "")

    async def test_null_content_returns_empty(self, executor: CodexExecutor) -> None:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=None))]

        with patch("bsgateway.executor.codex.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            result = await executor.execute("prompt", {})

        assert result.success is True
        assert result.stdout == ""

    def test_supported_task_types(self, executor: CodexExecutor) -> None:
        types = executor.supported_task_types()
        assert "coding" in types
