"""Tests for worker.main — register, poll_and_execute loop."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from worker.executors import ExecutionResult

# ─── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture()
def mock_settings(monkeypatch: pytest.MonkeyPatch):
    """Provide a WorkerSettings with defaults suitable for tests."""
    monkeypatch.setenv("BSGATEWAY_SERVER_URL", "http://test-server:8000")
    monkeypatch.setenv("BSGATEWAY_WORKER_TOKEN", "")
    monkeypatch.setenv("BSGATEWAY_WORKER_NAME", "test-worker")
    monkeypatch.setenv("BSGATEWAY_POLL_INTERVAL_SECONDS", "1")

    from worker.config import WorkerSettings

    return WorkerSettings()


# ─── detect_capabilities ─────────────────────────────────────────────


def test_detect_capabilities_claude_only() -> None:
    """Detect claude when it exists on PATH."""
    from worker.main import detect_capabilities

    def _which(cmd: str) -> str | None:
        return "/usr/bin/claude" if cmd == "claude" else None

    with patch("shutil.which", side_effect=_which):
        caps = detect_capabilities()
    assert "claude_code" in caps
    assert "codex" not in caps


def test_detect_capabilities_both() -> None:
    """Detect both claude and codex."""
    from worker.main import detect_capabilities

    with patch("shutil.which", return_value="/usr/bin/x"):
        caps = detect_capabilities()
    assert "claude_code" in caps
    assert "codex" in caps


def test_detect_capabilities_none() -> None:
    """Return empty list when no executors found."""
    from worker.main import detect_capabilities

    with patch("shutil.which", return_value=None):
        caps = detect_capabilities()
    assert caps == []


# ─── register ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_register_success(tmp_path) -> None:
    """register() posts to /api/v1/workers/register and writes token to .env."""
    from worker.main import register

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": "w-1", "token": "tok-new"}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with (
        patch("httpx.AsyncClient", return_value=mock_client),
        patch("worker.main.detect_capabilities", return_value=["claude_code"]),
        patch("worker.main._update_env_file") as mock_update,
    ):
        await register(
            name="test-worker",
            server_url="http://localhost:8000",
            install_token="fake-install-token",
        )

    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert call_args[0][0] == "/api/v1/workers/register"
    body = call_args[1]["json"]
    assert body["name"] == "test-worker"
    assert "claude_code" in body["capabilities"]

    mock_update.assert_called_once()
    env_updates = mock_update.call_args[0][1]
    assert env_updates["BSGATEWAY_WORKER_TOKEN"] == "tok-new"


# ─── heartbeat + poll + execute cycle ─────────────────────────────────


@pytest.mark.asyncio
async def test_poll_and_execute_one_task() -> None:
    """poll_and_execute processes a single task and reports result."""
    from worker.main import _handle_task

    mock_executor = AsyncMock()
    mock_executor.execute = AsyncMock(
        return_value=ExecutionResult(success=True, stdout="done"),
    )

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=MagicMock(status_code=200))

    task = {"task_id": "t-1", "prompt": "fix the bug", "title": "Fix bug"}
    headers = {"X-Worker-Token": "tok-123"}

    await _handle_task(task, mock_executor, mock_client, headers)

    # Verify executor was called with the prompt
    mock_executor.execute.assert_called_once()
    call_args = mock_executor.execute.call_args
    assert call_args[0][0] == "fix the bug"

    # Verify result was reported
    report_call = mock_client.post.call_args
    assert report_call[0][0] == "/api/v1/workers/result"
    body = report_call[1]["json"]
    assert body["task_id"] == "t-1"
    assert body["success"] is True
    assert body["output"] == "done"


@pytest.mark.asyncio
async def test_handle_task_failure() -> None:
    """Failed executor result reports error_message."""
    from worker.main import _handle_task

    mock_executor = AsyncMock()
    mock_executor.execute = AsyncMock(
        return_value=ExecutionResult(
            success=False,
            error_message="timeout",
            error_category="environment",
        ),
    )

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=MagicMock(status_code=200))

    task = {"task_id": "t-2", "prompt": "do stuff", "title": ""}
    headers = {"X-Worker-Token": "tok-123"}

    await _handle_task(task, mock_executor, mock_client, headers)

    body = mock_client.post.call_args[1]["json"]
    assert body["task_id"] == "t-2"
    assert body["success"] is False
    assert body["error_message"] == "timeout"


# ─── _update_env_file ────────────────────────────────────────────────


def test_update_env_file_creates(tmp_path) -> None:
    """_update_env_file creates a new .env if missing."""
    from worker.main import _update_env_file

    env_path = tmp_path / ".env"
    _update_env_file(str(env_path), {"KEY": "val"})
    assert "KEY=val" in env_path.read_text()


def test_update_env_file_updates_existing(tmp_path) -> None:
    """_update_env_file replaces existing keys, preserves others."""
    from worker.main import _update_env_file

    env_path = tmp_path / ".env"
    env_path.write_text("A=1\nB=2\n")
    _update_env_file(str(env_path), {"B": "3", "C": "4"})
    content = env_path.read_text()
    assert "A=1" in content
    assert "B=3" in content
    assert "C=4" in content
    assert "B=2" not in content


# ─── select_executor ─────────────────────────────────────────────────


def test_select_executor_claude() -> None:
    """select_executor returns ClaudeCodeExecutor for claude_code."""
    from worker.main import select_executor

    executor = select_executor("claude_code", skip_permissions=True)
    from worker.executors import ClaudeCodeExecutor

    assert isinstance(executor, ClaudeCodeExecutor)


def test_select_executor_codex() -> None:
    """select_executor returns CodexExecutor for codex."""
    from worker.main import select_executor

    executor = select_executor("codex", skip_permissions=True)
    from worker.executors import CodexExecutor

    assert isinstance(executor, CodexExecutor)


def test_select_executor_unknown() -> None:
    """select_executor raises ValueError for unknown type."""
    from worker.main import select_executor

    with pytest.raises(ValueError, match="Unknown executor"):
        select_executor("nonexistent")


# ─── register with labels ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_register_with_labels() -> None:
    """register() includes labels in the payload when provided."""
    from worker.main import register

    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "w-2", "token": "tok-lab"}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with (
        patch("httpx.AsyncClient", return_value=mock_client),
        patch("worker.main.detect_capabilities", return_value=[]),
        patch("worker.main._update_env_file"),
    ):
        token = await register("w", "http://x", "install-tok", labels=["env:prod"])

    assert token == "tok-lab"
    body = mock_client.post.call_args[1]["json"]
    assert body["labels"] == ["env:prod"]
    # Fallback when no capabilities detected
    assert body["capabilities"] == ["claude_code"]


# ─── _handle_task falls back to title ────────────────────────────────


@pytest.mark.asyncio
async def test_handle_task_uses_title_fallback() -> None:
    """When prompt is missing, _handle_task falls back to title."""
    from worker.main import _handle_task

    mock_executor = AsyncMock()
    mock_executor.execute = AsyncMock(
        return_value=ExecutionResult(success=True, stdout="ok"),
    )
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=MagicMock())

    task = {"task_id": "t-3", "title": "title fallback"}
    await _handle_task(task, mock_executor, mock_client, {"X-Worker-Token": "t"})

    prompt_used = mock_executor.execute.call_args[0][0]
    assert prompt_used == "title fallback"


# ─── poll_and_execute loop ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_poll_and_execute_registers_when_no_token(monkeypatch) -> None:
    """poll_and_execute calls register when worker_token is empty."""
    from worker import main as worker_main

    monkeypatch.setattr(worker_main.settings, "worker_token", "")
    monkeypatch.setattr(worker_main.settings, "worker_name", "test")
    monkeypatch.setattr(worker_main.settings, "server_url", "http://localhost")
    monkeypatch.setattr(worker_main.settings, "poll_interval_seconds", 1)

    register_mock = AsyncMock(return_value="new-token")
    monkeypatch.setattr(worker_main, "register", register_mock)
    monkeypatch.setattr(worker_main, "detect_capabilities", lambda: ["claude_code"])

    # Make select_executor return a mock
    mock_executor = MagicMock()
    monkeypatch.setattr(worker_main, "select_executor", lambda *a, **kw: mock_executor)

    # Mock httpx client to poll once then raise to break loop
    poll_response = MagicMock()
    poll_response.json.return_value = []
    poll_response.raise_for_status = MagicMock()

    call_count = 0

    async def mock_post(url, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count > 2:
            raise KeyboardInterrupt  # Break loop
        return poll_response

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = mock_post
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(KeyboardInterrupt):
            await worker_main.poll_and_execute()

    register_mock.assert_called_once_with("test", "http://localhost", "")


@pytest.mark.asyncio
async def test_poll_and_execute_dispatches_tasks(monkeypatch) -> None:
    """poll_and_execute dispatches received tasks to executor."""
    from worker import main as worker_main

    monkeypatch.setattr(worker_main.settings, "worker_token", "tok-ok")
    monkeypatch.setattr(worker_main.settings, "poll_interval_seconds", 0)
    monkeypatch.setattr(worker_main.settings, "max_parallel_tasks", 5)
    monkeypatch.setattr(worker_main, "detect_capabilities", lambda: ["claude_code"])

    execute_called = asyncio.Event()

    async def fake_execute(prompt, context):
        execute_called.set()
        return ExecutionResult(success=True, stdout="output")

    mock_executor = MagicMock()
    mock_executor.execute = fake_execute
    monkeypatch.setattr(worker_main, "select_executor", lambda *a, **kw: mock_executor)

    poll_count = 0

    async def mock_post(url, **kwargs):
        nonlocal poll_count
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        if "/poll" in url:
            poll_count += 1
            if poll_count == 1:
                resp.json.return_value = [{"task_id": "t-1", "prompt": "hi"}]
            else:
                # Wait for executor to finish, then break
                await asyncio.sleep(0.05)
                raise KeyboardInterrupt
        else:
            resp.json.return_value = {}
        return resp

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = mock_post
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(KeyboardInterrupt):
            await worker_main.poll_and_execute()

    assert execute_called.is_set()


@pytest.mark.asyncio
async def test_poll_and_execute_handles_connect_error(monkeypatch) -> None:
    """poll_and_execute logs warning on ConnectError and retries."""
    from worker import main as worker_main

    monkeypatch.setattr(worker_main.settings, "worker_token", "tok-ok")
    monkeypatch.setattr(worker_main.settings, "poll_interval_seconds", 0)
    monkeypatch.setattr(worker_main, "detect_capabilities", lambda: ["claude_code"])
    monkeypatch.setattr(worker_main, "select_executor", lambda *a, **kw: MagicMock())

    call_count = 0

    async def mock_post(url, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise httpx.ConnectError("refused")
        raise KeyboardInterrupt

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = mock_post
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(KeyboardInterrupt):
            await worker_main.poll_and_execute()

    assert call_count >= 2


@pytest.mark.asyncio
async def test_poll_and_execute_401_exits(monkeypatch) -> None:
    """poll_and_execute exits on 401 auth failure."""
    from worker import main as worker_main

    monkeypatch.setattr(worker_main.settings, "worker_token", "bad-tok")
    monkeypatch.setattr(worker_main.settings, "poll_interval_seconds", 0)
    monkeypatch.setattr(worker_main, "detect_capabilities", lambda: ["claude_code"])
    monkeypatch.setattr(worker_main, "select_executor", lambda *a, **kw: MagicMock())

    async def mock_post(url, **kwargs):
        resp = httpx.Response(401, request=httpx.Request("POST", url))
        raise httpx.HTTPStatusError("401", request=resp.request, response=resp)

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = mock_post
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(SystemExit) as exc_info:
            await worker_main.poll_and_execute()
    assert exc_info.value.code == 1
