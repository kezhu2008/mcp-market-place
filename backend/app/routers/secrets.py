from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from ulid import ULID

from .. import logging as log
from ..deps import Principal, current_principal
from ..models import Secret, SecretCreate, SecretRotate
from ..services import dynamo, secrets_manager

router = APIRouter(prefix="/secrets", tags=["secrets"])


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _to_model(item: dict[str, Any]) -> Secret:
    # Strip DDB keys, never expose SM value.
    data: dict[str, Any] = {k: v for k, v in item.items() if k not in ("PK", "SK", "ttl")}
    return Secret(**data)


@router.get("", response_model=list[Secret])
async def list_secrets(p: Principal = Depends(current_principal)) -> list[Secret]:
    return [_to_model(i) for i in dynamo.list_secrets(p.tenant_id)]


@router.post("", response_model=Secret, status_code=status.HTTP_201_CREATED)
async def create_secret(body: SecretCreate, p: Principal = Depends(current_principal)) -> Secret:
    secret_id = f"sec_{ULID().hex[:10]}"
    arn = secrets_manager.create(p.tenant_id, secret_id, body.value)
    now = _now()
    item: dict[str, Any] = {
        "id": secret_id,
        "tenantId": p.tenant_id,
        "ownerUserId": p.user_id,
        "visibility": "private",
        "priceCents": 0,
        "name": body.name,
        "description": body.description,
        "smArn": arn,
        "lastRotatedAt": now,
        "lastUsedAt": None,
        "createdAt": now,
    }
    dynamo.put_secret_meta(item)
    log.log(20, "secret.created", secret_id=secret_id, actor=p.email)
    return Secret(**item)


@router.post("/{secret_id}/rotate", response_model=Secret)
async def rotate_secret(
    secret_id: str, body: SecretRotate, p: Principal = Depends(current_principal)
) -> Secret:
    item = dynamo.get_secret_meta(p.tenant_id, secret_id)
    if not item:
        raise HTTPException(404, "secret not found")
    secrets_manager.put(p.tenant_id, secret_id, body.value)
    dynamo.update_secret_meta(p.tenant_id, secret_id, {"lastRotatedAt": _now()})
    refreshed = dynamo.get_secret_meta(p.tenant_id, secret_id)
    assert refreshed is not None
    log.log(20, "secret.rotated", secret_id=secret_id, actor=p.email)
    return _to_model(refreshed)


@router.delete("/{secret_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_secret(secret_id: str, p: Principal = Depends(current_principal)) -> None:
    item = dynamo.get_secret_meta(p.tenant_id, secret_id)
    if not item:
        raise HTTPException(404, "secret not found")
    # Block if any Bot references it.
    bots = dynamo.list_bots(p.tenant_id)
    in_use = [b["id"] for b in bots if b.get("secretId") == secret_id]
    if in_use:
        raise HTTPException(409, f"secret in use by bots: {', '.join(in_use)}")
    secrets_manager.delete(p.tenant_id, secret_id)
    dynamo.delete_secret_meta(p.tenant_id, secret_id)
    log.log(20, "secret.deleted", secret_id=secret_id, actor=p.email)
