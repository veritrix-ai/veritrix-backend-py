from __future__ import annotations

import base64
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


def clerk_domain_from_publishable_key(publishable_key: str) -> str | None:
    """Decode Clerk publishable key (pk_test_...) into the instance domain."""
    parts = publishable_key.strip().split("_", 2)
    if len(parts) != 3 or not parts[2]:
        return None

    padded = parts[2] + "=" * (-len(parts[2]) % 4)
    try:
        domain = base64.b64decode(padded).decode("utf-8").rstrip("$")
    except (ValueError, UnicodeDecodeError):
        return None

    return domain or None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("shared/.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    ingest_port: int = 8001
    api_port: int = 8000

    clickhouse_host: str = "localhost"
    clickhouse_port: int = 8123
    clickhouse_db: str = "agentops"
    clickhouse_user: str = "default"
    clickhouse_password: str = ""

    database_url: str = "postgresql+asyncpg://agentops:agentops@localhost:5432/agentops"

    clerk_secret_key: str = ""
    clerk_publishable_key: str = ""
    clerk_jwks_url: str = ""

    # Comma-separated browser origins allowed to call the App API (CORS).
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:3000,http://127.0.0.1:3000"
    )

    ingest_rate_limit_per_minute: int = 1000

    def resolved_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def resolved_clerk_jwks_url(self) -> str:
        if self.clerk_jwks_url.strip():
            return self.clerk_jwks_url.strip()

        domain = clerk_domain_from_publishable_key(self.clerk_publishable_key)
        if domain:
            return f"https://{domain}/.well-known/jwks.json"

        return ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
