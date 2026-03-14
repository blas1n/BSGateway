from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from bsgateway.routing.classifiers.base import (
    extract_all_text,
    extract_system_prompt,
    extract_user_text,
)


@dataclass
class RuleCondition:
    """A single condition within a routing rule."""

    condition_type: str  # text_pattern, token_count, message, tool, intent, model_requested
    field: str
    operator: str  # eq, contains, regex, gt, lt, gte, lte, between, in, not_in
    value: Any
    negate: bool = False


@dataclass
class RoutingRule:
    """A routing rule with priority and conditions."""

    id: str
    tenant_id: str
    name: str
    priority: int
    is_active: bool
    is_default: bool
    target_model: str
    conditions: list[RuleCondition] = field(default_factory=list)


@dataclass
class TenantModel:
    """A model registered by a tenant."""

    model_name: str
    provider: str
    litellm_model: str
    api_key_encrypted: str | None = None
    api_base: str | None = None
    extra_params: dict = field(default_factory=dict)


@dataclass
class TenantConfig:
    """Full tenant configuration loaded from DB cache."""

    tenant_id: str
    slug: str
    models: dict[str, TenantModel]
    rules: list[RoutingRule]  # sorted by priority ascending
    settings: dict = field(default_factory=dict)


@dataclass
class RuleMatch:
    """Result of rule evaluation."""

    rule: RoutingRule
    target_model: str
    trace: list[dict] | None = None


@dataclass
class EvaluationContext:
    """Pre-extracted fields from a request, evaluated once per request."""

    user_text: str
    system_prompt: str
    all_text: str
    estimated_tokens: int
    conversation_turns: int
    has_code_blocks: bool
    has_error_trace: bool
    tool_count: int
    tool_names: list[str]
    original_model: str
    classified_intent: str | None = None

    @classmethod
    def from_request(cls, data: dict) -> EvaluationContext:
        messages = data.get("messages", [])
        user_text = extract_user_text(messages)
        all_text = extract_all_text(messages)
        system_prompt = extract_system_prompt(data)

        tools = data.get("tools", [])
        tool_names = []
        for t in tools:
            fn = t.get("function", {})
            if fn.get("name"):
                tool_names.append(fn["name"])

        return cls(
            user_text=user_text,
            system_prompt=system_prompt,
            all_text=all_text,
            estimated_tokens=int(len(all_text.split()) * 1.3) if all_text else 0,
            conversation_turns=len(
                [m for m in messages if m.get("role") == "user"]
            ),
            has_code_blocks=bool(re.search(r"```", all_text)),
            has_error_trace=any(
                p in all_text
                for p in ["Traceback", "Error:", "Exception"]
            ),
            tool_count=len(tools),
            tool_names=tool_names,
            original_model=data.get("model", ""),
        )
