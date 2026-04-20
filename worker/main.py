"""BSGateway Worker — polls for tasks, executes via CLI executors, reports results.

Usage:
    python -m worker
"""

from __future__ import annotations

import asyncio
import shutil
import sys
from typing import Any

import httpx
import structlog

from worker.config import settings
from worker.executors import ExecutionResult, ExecutorProtocol, create_executor

logger = structlog.get_logger(__name__)


# ─── Capabilities ────────────────────────────────────────────────────


def detect_capabilities() -> list[str]:
    """Detect which CLI executors are available on this machine."""
    caps: list[str] = []
    if shutil.which("claude"):
        caps.append("claude_code")
    if shutil.which("codex"):
        caps.append("codex")
    return caps


# ─── Executor selection ──────────────────────────────────────────────


def select_executor(executor_type: str) -> ExecutorProtocol:
    """Create an executor instance by type. Raises ValueError if unknown."""
    return create_executor(executor_type)


# ─── Registration ────────────────────────────────────────────────────


async def register(
    name: str,
    server_url: str,
    install_token: str,
    labels: list[str] | None = None,
) -> str:
    """Register this worker with the BSGateway server.

    ``install_token`` is minted by an admin via the gateway UI
    (Models → Install Worker → Generate Token). Used only once — the
    returned worker token is persisted to ``.env`` for subsequent runs.

    Returns the worker token.
    """
    if not install_token:
        raise ValueError(
            "install_token is required for first-time registration. "
            "Set BSGATEWAY_INSTALL_TOKEN to a token minted via the gateway UI."
        )

    capabilities = detect_capabilities()
    if not capabilities:
        capabilities = ["claude_code"]

    async with httpx.AsyncClient(base_url=server_url, timeout=30) as client:
        payload: dict[str, Any] = {
            "name": name,
            "capabilities": capabilities,
        }
        if labels:
            payload["labels"] = labels

        res = await client.post(
            "/api/v1/workers/register",
            json=payload,
            headers={"X-Install-Token": install_token},
        )
        res.raise_for_status()
        data = res.json()

    token = data["token"]
    worker_id = data["id"]

    _update_env_file(
        ".env",
        {
            "BSGATEWAY_WORKER_TOKEN": token,
            "BSGATEWAY_WORKER_NAME": name,
            "BSGATEWAY_SERVER_URL": server_url,
        },
    )

    logger.info(
        "worker_registered",
        worker_id=worker_id,
        name=name,
        capabilities=capabilities,
    )
    return token


# ─── Task handling ───────────────────────────────────────────────────


async def _handle_task(
    task: dict[str, Any],
    executor: ExecutorProtocol,
    client: httpx.AsyncClient,
    headers: dict[str, str],
) -> None:
    """Execute a single task and report the result."""
    task_id = task["task_id"]
    prompt = task.get("prompt") or task.get("title", "")
    context: dict[str, Any] = {
        "task_id": task_id,
        "workspace_dir": task.get("workspace_dir", "."),
    }

    logger.info("task_received", task_id=task_id)

    result: ExecutionResult = await executor.execute(prompt, context)

    await client.post(
        "/api/v1/workers/result",
        headers=headers,
        json={
            "task_id": task_id,
            "success": result.success,
            "output": result.stdout,
            "error_message": result.error_message,
        },
    )
    logger.info("task_completed", task_id=task_id, success=result.success)


# ─── Main loop ───────────────────────────────────────────────────────


async def poll_and_execute() -> None:
    """Main loop: heartbeat -> poll -> execute -> report."""
    if not settings.worker_token:
        logger.info("no_token_found", hint="Registering with server...")
        token = await register(
            settings.worker_name,
            settings.server_url,
            settings.install_token,
        )
        settings.worker_token = token

    # Auto-detect executor: prefer claude_code
    capabilities = detect_capabilities()
    executor_type = capabilities[0] if capabilities else "claude_code"
    executor = select_executor(executor_type)

    logger.info(
        "worker_starting",
        name=settings.worker_name,
        executor=executor_type,
        server=settings.server_url,
    )

    headers = {"X-Worker-Token": settings.worker_token}
    in_flight: set[asyncio.Task[None]] = set()
    max_parallel = settings.max_parallel_tasks

    async def _run_task(task: dict[str, Any]) -> None:
        try:
            await _handle_task(task, executor, client, headers)
        except Exception:
            logger.exception("task_execution_error", task_id=task.get("task_id"))

    async with httpx.AsyncClient(base_url=settings.server_url, timeout=30) as client:
        while True:
            try:
                # Clean up completed tasks
                done = {t for t in in_flight if t.done()}
                in_flight -= done

                # Heartbeat
                await client.post("/api/v1/workers/heartbeat", headers=headers)

                # Only poll if we have capacity
                if len(in_flight) >= max_parallel:
                    await asyncio.sleep(settings.capacity_wait_seconds)
                    continue

                slots = max_parallel - len(in_flight)
                res = await client.post(
                    "/api/v1/workers/poll",
                    headers=headers,
                    params={"count": min(slots, settings.poll_batch_max)},
                )
                res.raise_for_status()
                tasks: list[dict[str, Any]] = res.json()

                if not tasks:
                    await asyncio.sleep(settings.poll_interval_seconds)
                    continue

                for task in tasks:
                    t = asyncio.create_task(_run_task(task))
                    in_flight.add(t)

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    logger.error("auth_failed", hint="Invalid token. Re-register.")
                    sys.exit(1)
                logger.error("http_error", status=e.response.status_code)
                await asyncio.sleep(settings.poll_interval_seconds)
            except httpx.ConnectError:
                logger.warning("server_unreachable", url=settings.server_url)
                await asyncio.sleep(settings.poll_interval_seconds * 3)
            except Exception:
                logger.exception("worker_error")
                await asyncio.sleep(settings.poll_interval_seconds)


# ─── Env file helper ─────────────────────────────────────────────────


def _update_env_file(path: str, updates: dict[str, str]) -> None:
    """Update or create a .env file with the given key-value pairs."""
    lines: list[str] = []
    try:
        with open(path) as f:
            lines = f.readlines()
    except FileNotFoundError:
        pass

    existing: set[str] = set()
    new_lines: list[str] = []
    for line in lines:
        key = line.split("=", 1)[0].strip()
        if key in updates:
            new_lines.append(f"{key}={updates[key]}\n")
            existing.add(key)
        else:
            new_lines.append(line)
    for key, value in updates.items():
        if key not in existing:
            new_lines.append(f"{key}={value}\n")
    with open(path, "w") as f:
        f.writelines(new_lines)


# ─── Entry point ─────────────────────────────────────────────────────


async def _amain() -> None:
    await poll_and_execute()


def main() -> None:
    """Synchronous entry point for ``bsgateway-worker`` script."""
    asyncio.run(_amain())
