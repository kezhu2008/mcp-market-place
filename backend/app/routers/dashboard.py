from __future__ import annotations

from fastapi import APIRouter, Depends

from ..deps import Principal, current_principal
from ..models import DashboardSummary
from ..services import dynamo

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardSummary)
async def dashboard(p: Principal = Depends(current_principal)) -> DashboardSummary:
    bots = dynamo.list_bots(p.tenant_id)
    return DashboardSummary(
        botsDeployed=sum(1 for b in bots if b.get("status") == "deployed"),
        botsDraft=sum(1 for b in bots if b.get("status") == "draft"),
        botsError=sum(1 for b in bots if b.get("status") == "error"),
        requests24h=sum(int(b.get("requests24h", 0) or 0) for b in bots),
        errors24h=sum(int(b.get("errors24h", 0) or 0) for b in bots),
    )
