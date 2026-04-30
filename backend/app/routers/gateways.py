from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from ulid import ULID

from .. import logging as log
from ..config import settings
from ..deps import Principal, current_principal
from ..models import Gateway, GatewayCreate
from ..services import agentcore_gateway, dynamo, secrets_manager

router = APIRouter(prefix="/gateways", tags=["gateways"])


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _to_model(item: dict[str, Any]) -> Gateway:
    data = {k: v for k, v in item.items() if k not in ("PK", "SK")}
    return Gateway(**data)


def _gateway_secret_key(gateway_id: str) -> str:
    return f"{gateway_id}/api-token"


@router.get("", response_model=list[Gateway])
async def list_gateways(p: Principal = Depends(current_principal)) -> list[Gateway]:
    return [_to_model(i) for i in dynamo.list_gateways(p.tenant_id)]


@router.get("/{gateway_id}", response_model=Gateway)
async def get_gateway(gateway_id: str, p: Principal = Depends(current_principal)) -> Gateway:
    item = dynamo.get_gateway(p.tenant_id, gateway_id)
    if not item:
        raise HTTPException(404, "gateway not found")
    return _to_model(item)


@router.post("", response_model=Gateway, status_code=status.HTTP_201_CREATED)
async def create_gateway(
    body: GatewayCreate, p: Principal = Depends(current_principal)
) -> Gateway:
    gateway_id = f"gw_{ULID().hex[:10]}"
    secret_key = _gateway_secret_key(gateway_id)

    # Stash the upstream API token in Secrets Manager so it never sits on
    # the Gateway item. The credential provider on AWS holds its own copy
    # (created below by agentcore_gateway.create); we keep this one so the
    # operator can rotate it via the same UI as bot tokens.
    secrets_manager.create(p.tenant_id, secret_key, body.token)

    now = _now()
    item: dict[str, Any] = {
        "id": gateway_id,
        "tenantId": p.tenant_id,
        "ownerUserId": p.user_id,
        "name": body.name,
        "description": body.description,
        "status": "creating",
        "gatewayArn": None,
        "gatewayUrl": None,
        "targetId": None,
        "credentialProviderArn": None,
        "secretId": secret_key,
        "lastError": None,
        "createdAt": now,
        "updatedAt": now,
    }
    dynamo.put_gateway(item)

    try:
        provisioned = agentcore_gateway.create(
            name=f"{p.tenant_id}-{gateway_id}",
            openapi_spec=body.openapiSpec,
            token=body.token,
            region=settings.region,
        )
    except Exception as e:
        # Roll back: remove the secret we just created and mark the item errored.
        try:
            secrets_manager.delete(p.tenant_id, secret_key)
        except Exception as cleanup_err:
            log.log(
                30,
                "gateway.secret_cleanup_failed",
                gateway_id=gateway_id,
                error=str(cleanup_err),
            )
        dynamo.update_gateway(
            p.tenant_id,
            gateway_id,
            {"status": "error", "lastError": str(e)},
        )
        log.log(40, "gateway.create_failed", gateway_id=gateway_id, error=str(e))
        raise HTTPException(502, f"gateway provisioning failed: {e}") from e

    updated = dynamo.update_gateway(
        p.tenant_id,
        gateway_id,
        {
            "status": "ready",
            "gatewayArn": provisioned["gatewayArn"],
            "gatewayUrl": provisioned["gatewayUrl"],
            "targetId": provisioned["targetId"],
            "credentialProviderArn": provisioned["credentialProviderArn"],
        },
    )
    log.log(20, "gateway.created", gateway_id=gateway_id, actor=p.email)
    return _to_model(updated)


@router.delete("/{gateway_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_gateway(gateway_id: str, p: Principal = Depends(current_principal)) -> None:
    item = dynamo.get_gateway(p.tenant_id, gateway_id)
    if not item:
        raise HTTPException(404, "gateway not found")

    # Block deletion if any bot's function references it.
    bots = dynamo.list_bots(p.tenant_id)
    in_use: list[str] = []
    for b in bots:
        for fn in _all_functions(b):
            if gateway_id in (fn.get("gatewayIds") or []):
                in_use.append(b["id"])
                break
    if in_use:
        raise HTTPException(409, f"gateway in use by bots: {', '.join(in_use)}")

    agentcore_gateway.destroy(
        gateway_arn=item.get("gatewayArn"),
        target_id=item.get("targetId"),
        credential_provider_arn=item.get("credentialProviderArn"),
        region=settings.region,
    )
    try:
        secrets_manager.delete(p.tenant_id, item["secretId"])
    except Exception as e:
        log.log(30, "gateway.secret_cleanup_failed", gateway_id=gateway_id, error=str(e))
    dynamo.delete_gateway(p.tenant_id, gateway_id)
    log.log(20, "gateway.deleted", gateway_id=gateway_id, actor=p.email)


def _all_functions(bot: dict[str, Any]):
    if bot.get("defaultFunction"):
        yield bot["defaultFunction"]
    for c in bot.get("commands") or []:
        if c.get("function"):
            yield c["function"]
