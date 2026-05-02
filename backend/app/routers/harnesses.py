from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from ulid import ULID

from .. import logging as log
from ..config import settings
from ..deps import Principal, current_principal
from ..models import (
    Harness,
    HarnessCreate,
    HarnessGatewayUpdate,
    HarnessTestRequest,
    TestFunctionResponse,
)
from ..services import agentcore_harness, bedrock, dynamo

router = APIRouter(prefix="/harnesses", tags=["harnesses"])


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _to_model(item: dict[str, Any]) -> Harness:
    data = {k: v for k, v in item.items() if k not in ("PK", "SK")}
    return Harness(**data)


@router.get("", response_model=list[Harness])
async def list_harnesses(p: Principal = Depends(current_principal)) -> list[Harness]:
    return [_to_model(i) for i in dynamo.list_harnesses(p.tenant_id)]


@router.get("/{harness_id}", response_model=Harness)
async def get_harness(harness_id: str, p: Principal = Depends(current_principal)) -> Harness:
    item = dynamo.get_harness(p.tenant_id, harness_id)
    if not item:
        raise HTTPException(404, "harness not found")
    return _to_model(item)


@router.post("", response_model=Harness, status_code=status.HTTP_201_CREATED)
async def create_harness(body: HarnessCreate, p: Principal = Depends(current_principal)) -> Harness:
    # Validate referenced gateways exist and belong to the tenant.
    for gid in body.gatewayIds:
        if not dynamo.get_gateway(p.tenant_id, gid):
            raise HTTPException(404, f"gateway not found: {gid}")

    harness_id = f"hns_{ULID().hex[:10]}"
    now = _now()
    item: dict[str, Any] = {
        "id": harness_id,
        "tenantId": p.tenant_id,
        "ownerUserId": p.user_id,
        "name": body.name,
        "description": body.description,
        "model": body.model,
        "systemPrompt": body.systemPrompt,
        "qualifier": None,
        "gatewayIds": list(body.gatewayIds),
        "status": "creating",
        "agentRuntimeArn": None,
        "agentRuntimeId": None,
        "lastError": None,
        "createdAt": now,
        "updatedAt": now,
    }
    dynamo.put_harness(item)

    try:
        provisioned = agentcore_harness.create(
            # AgentCore agentRuntimeName must match [a-zA-Z][a-zA-Z0-9_]{0,47}
            # — letters/digits/underscores only, no hyphens.
            name=f"{p.tenant_id}_{harness_id}",
            model=body.model,
            system_prompt=body.systemPrompt,
            image_uri=settings.platform_harness_image_uri,
            role_arn=settings.platform_harness_role_arn,
            region=settings.region,
        )
    except Exception as e:
        dynamo.update_harness(
            p.tenant_id,
            harness_id,
            {"status": "error", "lastError": str(e)},
        )
        log.log(40, "harness.create_failed", harness_id=harness_id, error=str(e))
        raise HTTPException(502, f"harness provisioning failed: {e}") from e

    updated = dynamo.update_harness(
        p.tenant_id,
        harness_id,
        {
            "status": "ready",
            "agentRuntimeArn": provisioned["agentRuntimeArn"],
            "agentRuntimeId": provisioned["agentRuntimeId"],
            "qualifier": provisioned.get("qualifier"),
        },
    )
    log.log(20, "harness.created", harness_id=harness_id, actor=p.email)
    return _to_model(updated)


@router.patch("/{harness_id}", response_model=Harness)
async def update_harness_gateways(
    harness_id: str,
    body: HarnessGatewayUpdate,
    p: Principal = Depends(current_principal),
) -> Harness:
    """Patch the only post-create mutable field — gatewayIds. Pure DDB write."""
    item = dynamo.get_harness(p.tenant_id, harness_id)
    if not item:
        raise HTTPException(404, "harness not found")
    for gid in body.gatewayIds:
        if not dynamo.get_gateway(p.tenant_id, gid):
            raise HTTPException(404, f"gateway not found: {gid}")
    updated = dynamo.update_harness(p.tenant_id, harness_id, {"gatewayIds": list(body.gatewayIds)})
    return _to_model(updated)


@router.post("/{harness_id}/redeploy", response_model=Harness)
async def redeploy_harness(
    harness_id: str,
    p: Principal = Depends(current_principal),
) -> Harness:
    """Re-provision an existing harness. Tears down the prior AgentCore
    runtime (if any) and re-creates with the harness's stored config.
    Allowed when status is ``ready`` or ``error``; refused while
    ``creating`` to avoid racing an in-flight provision."""
    item = dynamo.get_harness(p.tenant_id, harness_id)
    if not item:
        raise HTTPException(404, "harness not found")
    if item.get("status") == "creating":
        raise HTTPException(409, "harness is creating; wait for it to settle")

    dynamo.update_harness(
        p.tenant_id,
        harness_id,
        {"status": "creating", "lastError": None},
    )

    runtime_name = f"{p.tenant_id}_{harness_id}"
    runtime_id = item.get("agentRuntimeId")
    # If our DB lost the pointer (e.g. an earlier failed redeploy nulled
    # it), try to adopt the existing runtime by name before falling back
    # to create — otherwise create would hit ConflictException.
    if not runtime_id:
        try:
            existing = agentcore_harness.find_by_name(runtime_name, settings.region)
        except Exception as e:  # noqa: BLE001 — lookup is best-effort
            log.log(30, "harness.adopt_lookup_failed", harness_id=harness_id, error=str(e))
            existing = None
        if existing:
            runtime_id = existing["agentRuntimeId"]

    try:
        if runtime_id:
            # Prefer update — preserves arn/id and avoids the async-delete
            # race that delete+recreate hits.
            provisioned = agentcore_harness.update(
                agent_runtime_id=runtime_id,
                model=item["model"],
                system_prompt=item.get("systemPrompt") or "",
                image_uri=settings.platform_harness_image_uri,
                role_arn=settings.platform_harness_role_arn,
                region=settings.region,
            )
        else:
            provisioned = agentcore_harness.create(
                name=runtime_name,
                model=item["model"],
                system_prompt=item.get("systemPrompt") or "",
                image_uri=settings.platform_harness_image_uri,
                role_arn=settings.platform_harness_role_arn,
                region=settings.region,
            )
    except Exception as e:
        dynamo.update_harness(
            p.tenant_id,
            harness_id,
            {"status": "error", "lastError": str(e)},
        )
        log.log(40, "harness.redeploy_failed", harness_id=harness_id, error=str(e))
        raise HTTPException(502, f"harness redeploy failed: {e}") from e

    updated = dynamo.update_harness(
        p.tenant_id,
        harness_id,
        {
            "status": "ready",
            "agentRuntimeArn": provisioned["agentRuntimeArn"],
            "agentRuntimeId": provisioned["agentRuntimeId"],
            "qualifier": provisioned.get("qualifier"),
        },
    )
    log.log(20, "harness.redeployed", harness_id=harness_id, actor=p.email)
    return _to_model(updated)


@router.post("/{harness_id}/test", response_model=TestFunctionResponse)
async def test_harness(
    harness_id: str,
    body: HarnessTestRequest,
    p: Principal = Depends(current_principal),
) -> TestFunctionResponse:
    fn, gateways = bedrock.resolve_harness(p.tenant_id, harness_id)
    if fn is None:
        item = dynamo.get_harness(p.tenant_id, harness_id)
        if not item:
            raise HTTPException(404, "harness not found")
        raise HTTPException(400, f"harness is {item.get('status')}, not ready")

    try:
        out, latency, raw = bedrock.invoke_harness(
            fn,
            body.text,
            session_key=f"test-{harness_id}-{p.user_id}",
            region=settings.region,
            gateways=gateways,
        )
    except bedrock.HarnessError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:
        raise HTTPException(502, f"harness invocation failed: {e}") from e

    return TestFunctionResponse(output=out, latencyMs=latency, raw=raw)


@router.delete("/{harness_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_harness(harness_id: str, p: Principal = Depends(current_principal)) -> None:
    item = dynamo.get_harness(p.tenant_id, harness_id)
    if not item:
        raise HTTPException(404, "harness not found")

    # Block when any bot's function references this harness.
    bots = dynamo.list_bots(p.tenant_id)
    in_use: list[str] = []
    for b in bots:
        for fn in _all_functions(b):
            if fn.get("harnessId") == harness_id:
                in_use.append(b["id"])
                break
    if in_use:
        raise HTTPException(409, f"harness in use by bots: {', '.join(in_use)}")

    agentcore_harness.destroy(
        agent_runtime_arn=item.get("agentRuntimeArn"),
        region=settings.region,
    )
    dynamo.delete_harness(p.tenant_id, harness_id)
    log.log(20, "harness.deleted", harness_id=harness_id, actor=p.email)


def _all_functions(bot: dict[str, Any]):
    if bot.get("defaultFunction"):
        yield bot["defaultFunction"]
    for c in bot.get("commands") or []:
        if c.get("function"):
            yield c["function"]
