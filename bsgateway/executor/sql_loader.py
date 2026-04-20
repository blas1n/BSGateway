"""Named-query SQL loader for executor module."""

from __future__ import annotations

from pathlib import Path

_SQL_DIR = Path(__file__).parent / "sql"


class ExecutorSqlLoader:
    """Load named queries and schema DDL from executor/sql/."""

    def __init__(self) -> None:
        self._queries: dict[str, str] = {}

    def schema(self) -> str:
        return (_SQL_DIR / "executor_schema.sql").read_text()

    def query(self, name: str) -> str:
        if not self._queries:
            self._parse_queries()
        return self._queries[name]

    def _parse_queries(self) -> None:
        content = (_SQL_DIR / "executor_queries.sql").read_text()
        current_name: str | None = None
        current_lines: list[str] = []
        for line in content.splitlines():
            if line.strip().startswith("-- name:"):
                if current_name:
                    self._queries[current_name] = "\n".join(current_lines).strip()
                current_name = line.strip().split("-- name:")[1].strip()
                current_lines = []
            else:
                current_lines.append(line)
        if current_name:
            self._queries[current_name] = "\n".join(current_lines).strip()
