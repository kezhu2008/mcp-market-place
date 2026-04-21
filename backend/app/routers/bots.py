from __future__ import annotations

import secrets as pysecrets
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from ulid import ULID

from .. import logging as log
from ..config import settings
from ..deps import Principal, current_principal
from ..models import Bot, BotCreate, BotUpdate
from ..services import dynamo, secrets_manager, telegram

router = APIRouter(prefix="/bots", tags=["bots"])


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _to_model(item: dict[str, Any]) -> Bot:
    data = {
        k: v
        for k, v in item.items()
        if k not in ("PK", "SK", "GSI1PK", "GSI1SK", "ttl", "webhookSecretSMKey")
    }
    return Bot(**data)


def _webhook_secret_key(bot_id: str) -> str:
    return f"{bot_id}/webhook-secret"


def _write_event(bot_id: str, event_type: str, actor: str, msg: str, details: dict | None = None) -> None:
    dynamo.put_event(
        bot_id,
        {
            "id": f"ev_{ULID().hex[:10]}",
            "botId": bot_id,
            "ts": _now(),
            "type": event_type,
            "msg": msg,
            "actor": actor,
            "details": details or {},
        },
    )


@router.get("", response_model=list[Bot])
async def list_bots(p: Principal = Depends(current_principal)) -> list[Bot]:
    return [_to_model(i) for i in dynamo.list_bots(p.tenant_id)]


@router.post("", response_model=Bot, status_code=status.HTTP_201_CREATED)
async def create_bot(body: BotCreate, p: Principal = Depends(current_principal)) -> Bot:
    # Ensure secret exists and belongs to tenant.
    sec = dynamo.get_secret_meta(p.tenant_id, body.secretId)
    if not sec:
        raise HTTPException(404, f"secret not found: {body.secretId}")

    bot_id = f"bot_{ULID().hex[:10]}"
    webhook_path = f"wh_{ULID().hex[:14]}"
    webhook_secret_token = pysecrets.token_urlsafe(32)
    secrets_manager.create(p.tenant_id, _webhook_secret_key(bot_id), webhook_secret_token)

    now = _now()
    item = {
        "id": bot_id,
        "tenantId": p.tenant_id,
        "ownerUserId": p.user_id,
        "visibility": "private",
        "priceCents": 0,
        "name": body.name,
        "description": body.description,
        "type": body.type,
        "status": "draft",
        "secretId": body.secretId,
        "webhookPath": webhook_path,
        "commands": [c.model_dump() for c in body.commands],
        "deployedAt": None,
        "lastEventAt": None,
        "lastError": None,
        "requests24h": 0,
        "errors24h": 0,
        "createdAt": now,
        "updatedAt": now,
    }
    dynamo.put_bot(item)
    _write_event(bot_id, "bot.created", p.email, f"{body.name} created")
    log.log(20, "bot.created", bot_id=bot_id, actor=p.email)
    return _to_model(item)


@router.get("/{bot_id}", response_model=Bot)
async def get_bot(bot_id: str, p: Principal = Depends(current_principal)) -> Bot:
    item = dynamo.get_bot(p.tenant_id, bot_id)
    if not item:
        raise HTTPException(404, "bot not found")
    return _to_model(item)


@router.patch("/{bot_id}", response_model=Bot)
async def update_bot(bot_id: str, body: BotUpdate, p: Principal = Depends(current_principal)) -> Bot:
    item = dynamo.get_bot(p.tenant_id, bot_id)
    if not item:
        raise HTTPException(404, "bot not found")
    updates = {k: v for k, v in body.model_dump(exclude_unset=True).items()}
    if "commands" in updates and updates["commands"] is not None:
        updates["commands"] = [c if isinstance(c, dict) else c.model_dump() for c in updates["commands"]]
    updated = dynamo.update_bot(p.tenant_id, bot_id, updates)
    _write_event(bot_id, "bot.updated", p.email, "config updated")
    return _to_model(updated)


@router.post("/{bot_id}/deploy", response_model=Bot)
async def deploy_bot(bot_id: str, p: Principal = Depends(current_principal)) -> Bot:
    item = dynamo.get_bot(p.tenant_id, bot_id)
    if not item:
        raise HTTPException(404, "bot not found")

    updated = dynamo.update_bot(p.tenant_id, bot_id, {"status": "deploying"})
    _write_event(bot_id, "deploy.started", p.email, f"deploy initiated by {p.email}")

    try:
        token = secrets_manager.get(p.tenant_id, item["secretId"])
        webhook_secret = secrets_manager.get(p.tenant_id, _webhook_secret_key(bot_id))
        url = f"{settings.webhook_base_url.rstrip('/')}/{item['webhookPath']}"
        await telegram.set_webhook(token, url, webhook_secret)
    except Exception as e:
        dynamo.update_bot(p.tenant_id, bot_id, {"status": "error", "lastError": str(e)})
        _write_event(bot_id, "deploy.failed", p.email, f"deploy failed: {e}", {"error": str(e)})
        log.log(40, "deploy.failed", bot_id=bot_id, error=str(e))
        raise HTTPException(502, f"telegram setWebhook failed: {e}") from e

    updated = dynamo.update_bot(
        p.tenant_id,
        bot_id,
        {"status": "deployed", "deployedAt": _now(), "lastError": None},
    )
    _write_event(bot_id, "deploy.succeeded", p.email, "deployed")
    log.log(20, "deploy.succeeded", bot_id=bot_id, actor=p.email)
    return _to_model(updated)


@router.post("/{bot_id}/disable", response_model=Bot)
async def disable_bot(bot_id: str, p: Principal = Depends(current_principal)) -> Bot:
    item = dynamo.get_bot(p.tenant_id, bot_id)
    if not item:
        raise HTTPException(404, "bot not found")
    try:
        token = secrets_manager.get(p.tenant_id, item["secretId"])
        await telegram.delete_webhook(token)
    except Exception as e:
        log.log(30, "disable.webhook_cleanup_failed", bot_id=bot_id, error=str(e))
    updated = dynamo.update_bot(p.tenant_id, bot_id, {"status": "disabled"})
    _write_event(bot_id, "bot.disabled", p.email, "disabled")
    return _to_model(updated)


@router.delete("/{bot_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_bot(bot_id: str, p: Principal = Depends(current_principal)) -> None:
    item = dynamo.get_bot(p.tenant_id, bot_id)
    if not item:
        raise HTTPException(404, "bot not found")
    try:
        token = secrets_manager.get(p.tenant_id, item["secretId"])
        await telegram.delete_webhook(token)
    except Exception as e:
        log.log(30, "delete.webhook_cleanup_failed", bot_id=bot_id, error=str(e))
    try:
        secrets_manager.delete(p.tenant_id, _webhook_secret_key(bot_id))
    except Exception as e:
        log.log(30, "delete.webhook_secret_cleanup_failed", bot_id=bot_id, error=str(e))
    _write_event(bot_id, "bot.deleted", p.email, "deleted")
    dynamo.delete_bot(p.tenant_id, bot_id)
    log.log(20, "bot.deleted", bot_id=bot_id, actor=p.email)
