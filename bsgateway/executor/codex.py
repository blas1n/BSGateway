"""Codex executor — code generation via LiteLLM."""

from __future__ import annotations

from typing import Any

import structlog
from litellm import acompletion

from bsgateway.executor.base import ExecutionResult
from bsgateway.executor.config import executor_settings

logger = structlog.get_logger(__name__)


class CodexExecutor:
    """Execute coding tasks via OpenAI Codex (or any LiteLLM-compatible model)."""

    def __init__(self) -> None:
        self._default_model = executor_settings.codex_default_model

    def supported_task_types(self) -> list[str]:
        return ["coding", "refactor", "bugfix", "test"]

    async def execute(self, prompt: str, context: dict[str, Any]) -> ExecutionResult:
        model = context.get("model", self._default_model)
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": context.get("max_tokens", 16384),
            "temperature": context.get("temperature", 0.0),
        }
        if context.get("api_key"):
            kwargs["api_key"] = context["api_key"]
        if context.get("api_base"):
            kwargs["api_base"] = context["api_base"]

        try:
            response = await acompletion(**kwargs)
            content = response.choices[0].message.content or ""
            return ExecutionResult(success=True, stdout=content)
        except Exception as e:
            logger.error("codex_executor_error", error=str(e))
            return ExecutionResult(
                success=False,
                error_message=str(e),
                error_category="environment",
            )
