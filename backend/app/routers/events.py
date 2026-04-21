from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..deps import Principal, current_principal
from ..models import Event
from ..services import dynamo

router = APIRouter(tags=["events"])


def _strip(item: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in item.items() if k not in ("PK", "SK", "GSI2PK", "GSI2SK", "ttl")}


@router.get("/bots/{bot_id}/events", response_model=list[Event])
async def bot_events(bot_id: str, limit: int = 50, p: Principal = Depends(current_principal)) -> list[Event]:
    # Ensure the bot belongs to tenant before revealing events.
    bot = dynamo.get_bot(p.tenant_id, bot_id)
    if not bot:
        raise HTTPException(404, "bot not found")
    return [Event(**_strip(i)) for i in dynamo.list_bot_events(bot_id, limit)]


@router.get("/events", response_model=list[Event])
async def recent_events(limit: int = 25, p: Principal = Depends(current_principal)) -> list[Event]:
    # Phase 1: fan-out across tenant's bots. Trivial cost for single-tenant.
    bots = dynamo.list_bots(p.tenant_id)
    all_events: list[dict[str, Any]] = []
    for b in bots:
        all_events.extend(dynamo.list_bot_events(b["id"], limit))
    all_events.sort(key=lambda e: e["ts"], reverse=True)
    return [Event(**_strip(i)) for i in all_events[:limit]]
