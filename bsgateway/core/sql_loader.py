"""Generic named-query SQL loader.

All domain repositories share the same `-- name: xxx` convention.
This module provides a single reusable loader to eliminate duplication.
"""

from __future__ import annotations

from pathlib import Path

# All SQL files live under routing/sql/
_SQL_DIR = Path(__file__).parent.parent / "routing" / "sql"


class NamedSqlLoader:
    """Load named queries and schema DDL from the shared sql/ directory."""

    def __init__(self, schema_file: str, query_file: str) -> None:
        self._schema_file = schema_file
        self._query_file = query_file
        self._queries: dict[str, str] = {}

    def schema(self) -> str:
        return (_SQL_DIR / self._schema_file).read_text()

    def query(self, name: str) -> str:
        if not self._queries:
            self._parse_queries()
        return self._queries[name]

    def _parse_queries(self) -> None:
        content = (_SQL_DIR / self._query_file).read_text()
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
