"""Shared utility functions for BSGateway."""

from __future__ import annotations

import json
from typing import Any


def safe_json_loads(raw: str | dict | None, fallback: dict | None = None) -> dict:
    """Safely parse JSON string, returning fallback on error."""
    if raw is None:
        return fallback or {}
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return fallback or {}


def parse_jsonb_value(raw: Any) -> Any:
    """Parse JSONB value from DB record."""
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw
    return raw
