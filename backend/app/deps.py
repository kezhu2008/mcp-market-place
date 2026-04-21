"""Cognito JWT verification + tenant/user resolver."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Depends, Header, HTTPException, status
from jwt import PyJWKClient

from .config import settings


@dataclass(frozen=True)
class Principal:
    user_id: str  # Cognito sub
    email: str
    tenant_id: str


@lru_cache(maxsize=1)
def _jwks_client() -> PyJWKClient | None:
    if not settings.cognito_user_pool_id:
        return None
    url = (
        f"https://cognito-idp.{settings.region}.amazonaws.com/"
        f"{settings.cognito_user_pool_id}/.well-known/jwks.json"
    )
    return PyJWKClient(url)


def _verify(token: str) -> dict:
    client = _jwks_client()
    if client is None:
        # Permissive local mode: no Cognito configured yet.
        return {"sub": "local-user", "email": "local@example.com"}
    signing_key = client.get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=settings.cognito_client_id or None,
        options={"verify_aud": bool(settings.cognito_client_id)},
    )


async def current_principal(
    authorization: str | None = Header(default=None),
) -> Principal:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")
    token = authorization.split(" ", 1)[1]
    try:
        claims = _verify(token)
    except Exception as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"invalid token: {e}") from e
    return Principal(
        user_id=claims.get("sub", ""),
        email=claims.get("email", ""),
        tenant_id=settings.default_tenant_id,  # Phase 1: hardcoded
    )


RequireUser = Depends(current_principal)
