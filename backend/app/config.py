"""Runtime configuration pulled from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    region: str
    table_name: str
    secrets_prefix: str
    cognito_user_pool_id: str
    cognito_client_id: str
    webhook_base_url: str
    default_tenant_id: str  # Phase 1: single-tenant hardcoded


def load_settings() -> Settings:
    return Settings(
        region=os.environ.get("AWS_REGION", "ap-southeast-2"),
        table_name=os.environ.get("TABLE_NAME", "mcp_platform_prod"),
        secrets_prefix=os.environ.get("SECRETS_PREFIX", "mcp-platform"),
        cognito_user_pool_id=os.environ.get("COGNITO_USER_POOL_ID", ""),
        cognito_client_id=os.environ.get("COGNITO_CLIENT_ID", ""),
        webhook_base_url=os.environ.get("WEBHOOK_BASE_URL", ""),
        default_tenant_id=os.environ.get("DEFAULT_TENANT_ID", "t_default"),
    )


settings = load_settings()
