"""Pydantic schemas for API + DynamoDB items."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

BotStatus = Literal["draft", "deploying", "deployed", "disabled", "error"]
BotType = Literal["telegram"]
Visibility = Literal["private", "published"]


class BotCommand(BaseModel):
    cmd: str
    template: str


class BotCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    description: str = ""
    type: BotType = "telegram"
    secretId: str
    commands: list[BotCommand] = []


class BotUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=64)
    description: str | None = None
    commands: list[BotCommand] | None = None


class Bot(BaseModel):
    id: str
    tenantId: str
    ownerUserId: str
    visibility: Visibility = "private"
    priceCents: int = 0
    name: str
    description: str = ""
    type: BotType = "telegram"
    status: BotStatus = "draft"
    secretId: str
    webhookPath: str
    commands: list[BotCommand] = []
    deployedAt: str | None = None
    lastEventAt: str | None = None
    lastError: str | None = None
    requests24h: int = 0
    errors24h: int = 0
    createdAt: str
    updatedAt: str


class SecretCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    description: str = ""
    value: str = Field(min_length=1)


class SecretRotate(BaseModel):
    value: str = Field(min_length=1)


class Secret(BaseModel):
    id: str
    tenantId: str
    ownerUserId: str
    visibility: Visibility = "private"
    priceCents: int = 0
    name: str
    description: str = ""
    smArn: str
    lastRotatedAt: str
    lastUsedAt: str | None = None
    createdAt: str


class Event(BaseModel):
    id: str
    botId: str
    ts: str
    type: str
    msg: str
    actor: str
    details: dict[str, Any] = {}


class DashboardSummary(BaseModel):
    botsDeployed: int = 0
    botsDraft: int = 0
    botsError: int = 0
    requests24h: int = 0
    errors24h: int = 0
