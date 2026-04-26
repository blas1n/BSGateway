"""BSGateway settings.

Phase A Batch 5: extends :class:`bsvibe_fastapi.FastApiSettings` so the
CORS / CSV-list / structlog plumbing matches the four-product baseline
(BSupervisor PR #13 §M18). BSGateway-specific knobs (gateway YAML
path, encryption key, BSupervisor service-account credentials, …)
remain on this subclass.

The legacy ``cors_allowed_origins: str`` field is replaced by the
shared ``Annotated[list[str], NoDecode]`` shape inherited from
:class:`FastApiSettings`. Existing deployments that ship
``CORS_ALLOWED_ORIGINS=http://a,http://b`` keep working unchanged.
"""

from __future__ import annotations

from pathlib import Path

import structlog
from bsvibe_fastapi import FastApiSettings
from pydantic_settings import SettingsConfigDict

_config_logger = structlog.get_logger(__name__)


class Settings(FastApiSettings):
    """BSGateway configuration via environment variables."""

    gateway_config_path: Path = Path("gateway.yaml")
    collector_database_url: str | None = None
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_password: str = ""
    log_level: str = "INFO"

    # API server
    api_port: int = 8000
    api_host: str = "0.0.0.0"

    # Auth (BSVibe-Auth)
    bsvibe_auth_url: str = "https://auth.bsvibe.dev"
    encryption_key: str = ""  # 32-byte hex string for AES-256-GCM

    # ----------------------------------------------------------------------
    # Phase 0 P0.7 — service-account credentials for minting BSupervisor JWTs.
    # ----------------------------------------------------------------------
    # Long-lived BSVibe-Auth user access token for a dedicated service
    # account user (admin/owner of the tenant below). Generated out-of-band
    # via the BSVibe-Auth admin console; rotated quarterly.
    bsvibe_service_account_token: str = ""
    # Tenant the service-account user is operating on behalf of.
    bsvibe_service_account_tenant_id: str = ""

    # ----------------------------------------------------------------------
    # Phase 0 P0.7 — BSupervisor preflight integration.
    # ----------------------------------------------------------------------
    bsupervisor_url: str = ""
    bsupervisor_audit_enabled: bool = False
    bsupervisor_audit_timeout_ms: int = 200
    # "open" → fail-open (default, matches BSNexus's pre-cutover behaviour);
    # "closed" → block runs when BSupervisor is unreachable.
    bsupervisor_audit_fail_mode: str = "open"

    # Frontend dist directory (for serving dashboard static files)
    frontend_dist_dir: str = ""

    # FastApiSettings.cors_allowed_origins is Annotated[list[str], NoDecode]
    # with a CSV field_validator. Override the default to "" → [] (legacy
    # behaviour: when unset, fall back to localhost in app.create_app).
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def encryption_key_bytes(self) -> bytes:
        """Return the encryption key as raw bytes.

        Raises RuntimeError if ENCRYPTION_KEY is not set — provider API keys
        require encryption and must not be stored in plaintext.
        """
        if not self.encryption_key:
            raise RuntimeError(
                "ENCRYPTION_KEY is required — provider API keys cannot be "
                "stored without encryption. Generate one with: "
                'python -c "import os; print(os.urandom(32).hex())"'
            )
        try:
            key = bytes.fromhex(self.encryption_key)
        except ValueError as e:
            raise ValueError("ENCRYPTION_KEY must be a valid 64-character hex string") from e
        if len(key) != 32:
            raise ValueError("ENCRYPTION_KEY must be exactly 64 hex characters (32 bytes)")
        return key


settings = Settings()
