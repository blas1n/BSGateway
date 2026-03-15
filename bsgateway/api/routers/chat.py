from __future__ import annotations

import json
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse

from bsgateway.api.deps import AuthContext, get_auth_context, get_encryption_key, get_pool
from bsgateway.chat.ratelimit import RateLimiter
from bsgateway.chat.service import ChatError, ChatService

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["chat"])


def _get_redis(request: Request) -> Any:
    """Extract optional Redis client from app state."""
    return getattr(request.app.state, "redis", None)


def _error_response(
    status_code: int, message: str, error_type: str, code: str | None = None,
) -> JSONResponse:
    """Return an OpenAI-compatible error response."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "message": message,
                "type": error_type,
                "param": None,
                "code": code,
            }
        },
    )


@router.post(
    "/chat/completions",
    summary="Chat completions",
    responses={
        401: {"description": "Invalid or expired API key"},
        429: {"description": "Rate limit exceeded"},
        502: {"description": "Upstream provider error"},
    },
)
async def chat_completions(
    request: Request,
    auth: AuthContext = Depends(get_auth_context),
) -> Any:
    """OpenAI-compatible chat completions with tenant-based routing."""
    body = await request.json()

    # Validate messages
    if "messages" not in body or not body["messages"]:
        return _error_response(
            400, "messages is required and must be non-empty",
            "invalid_request_error", "invalid_messages",
        )

    pool = get_pool(request)
    encryption_key = get_encryption_key(request)
    redis = _get_redis(request)

    # Rate limiting (if Redis available and tenant has rate_limit config)
    if redis:
        from bsgateway.tenant.repository import TenantRepository

        tenant_repo = TenantRepository(pool)
        tenant_row = await tenant_repo.get_tenant(auth.tenant_id)
        if tenant_row:
            import json as json_mod

            raw_settings = tenant_row["settings"]
            settings = (
                json_mod.loads(raw_settings)
                if isinstance(raw_settings, str)
                else (raw_settings or {})
            )
            rate_limit = settings.get("rate_limit", {})
            rpm = rate_limit.get("requests_per_minute", 0)
            if rpm > 0:
                limiter = RateLimiter(redis)
                result = await limiter.check(str(auth.tenant_id), rpm)
                if not result.allowed:
                    return JSONResponse(
                        status_code=429,
                        content={
                            "error": {
                                "message": "Rate limit exceeded",
                                "type": "rate_limit_error",
                                "param": None,
                                "code": "rate_limit_exceeded",
                            }
                        },
                        headers={
                            "X-RateLimit-Limit": str(result.limit),
                            "X-RateLimit-Remaining": str(result.remaining),
                            "X-RateLimit-Reset": str(result.reset_at),
                        },
                    )

    svc = ChatService(pool, encryption_key, redis)

    try:
        response = await svc.complete(auth.tenant_id, body)
    except ChatError as e:
        return _error_response(e.status_code, str(e), "invalid_request_error", e.code)
    except Exception as e:
        logger.error("chat_completion_failed", error=str(e), exc_info=True)
        return _error_response(502, "Upstream provider error", "upstream_error")

    # Streaming response
    if body.get("stream"):
        async def event_stream():
            try:
                async for chunk in response:
                    data = chunk.model_dump() if hasattr(chunk, "model_dump") else chunk
                    yield f"data: {json.dumps(data)}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as exc:
                logger.error("stream_error", error=str(exc), exc_info=True)
                error_data = {
                    "error": {
                        "message": "Stream interrupted",
                        "type": "upstream_error",
                        "param": None,
                        "code": "stream_error",
                    }
                }
                yield f"data: {json.dumps(error_data)}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # Non-streaming response
    if hasattr(response, "model_dump"):
        return response.model_dump()
    return response
