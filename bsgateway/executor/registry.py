"""Thread-safe executor registry."""

from __future__ import annotations

import threading

import structlog

from bsgateway.executor.base import ExecutorProtocol

logger = structlog.get_logger(__name__)


class ExecutorRegistry:
    """Singleton-style registry mapping names to executor classes."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._executors: dict[str, type] = {}

    def register(self, name: str, executor_cls: type) -> None:
        """Register an executor class. Silently skips if already registered."""
        with self._lock:
            if name in self._executors:
                return
            self._executors[name] = executor_cls
            logger.debug("executor_registered", name=name)

    def get(self, name: str) -> ExecutorProtocol:
        """Create and return an executor instance by name."""
        with self._lock:
            cls = self._executors.get(name)
        if cls is None:
            raise KeyError(f"Unknown executor: {name}")
        return cls()  # type: ignore[return-value]

    def is_available(self, name: str) -> bool:
        """Check if an executor is registered."""
        with self._lock:
            return name in self._executors

    def list_available(self) -> list[str]:
        """Return names of all registered executors."""
        with self._lock:
            return list(self._executors.keys())
