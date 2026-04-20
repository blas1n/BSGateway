"""Executor configuration via environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class ExecutorSettings(BaseSettings):
    """Settings for executor backends, loaded from EXECUTOR_* env vars."""

    # Claude Code CLI
    claude_code_timeout_seconds: int = 3600
    claude_code_total_timeout_seconds: int = 7200
    claude_code_rate_limit_retries: int = 3
    claude_code_rate_limit_wait_seconds: int = 60

    # Codex
    codex_default_model: str = "openai/codex-mini"

    # Worker dispatch loop (ChatService._execute_via_worker)
    worker_default_timeout_seconds: int = 600
    worker_poll_interval_seconds: float = 1.0
    routing_log_timeout_seconds: float = 30.0

    model_config = SettingsConfigDict(env_file=".env", env_prefix="EXECUTOR_", extra="ignore")


executor_settings = ExecutorSettings()
