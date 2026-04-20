"""Worker configuration — loaded from environment or .env file."""

from __future__ import annotations

import socket

from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    """Settings for the BSGateway worker process."""

    # BSGateway API URL
    server_url: str = "http://localhost:8000"

    # Worker identity (from registration)
    worker_token: str = ""
    worker_name: str = socket.gethostname()

    # Install token — required ONLY on first run to register the worker.
    # Minted by an admin via the gateway UI. Once registered, worker_token is
    # saved to .env and this is no longer used.
    install_token: str = ""

    # Polling
    poll_interval_seconds: int = 5

    # Execution
    max_parallel_tasks: int = 5
    skip_permissions: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_prefix="BSGATEWAY_", extra="ignore")


settings = WorkerSettings()
