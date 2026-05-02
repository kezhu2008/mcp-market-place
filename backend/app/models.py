"""Pydantic schemas for API + DynamoDB items."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

BotStatus = Literal["draft", "deploying", "deployed", "disabled", "error"]
BotType = Literal["telegram"]
Visibility = Literal["private", "published"]


class BedrockHarnessFunction(BaseModel):
    type: Literal["bedrock_harness"] = "bedrock_harness"
    # Reference to a platform-managed Harness item (PK=TENANT#<tid>
    # SK=HARNESS#<id>). Webhook resolves this to the runtime ARN +
    # the harness's linked gateway URLs at invoke time.
    harnessId: str
    promptTemplate: str | None = None


# Forward-compatible alias. When a second function type lands (http_webhook,
# raw bedrock InvokeModel, MCP bridge…), promote this to
# Annotated[BedrockHarnessFunction | OtherFunction, Field(discriminator="type")].
BotFunction = BedrockHarnessFunction


class BotCommand(BaseModel):
    cmd: str
    # None → inherit Bot.defaultFunction at runtime (resolved webhook-side).
    function: BotFunction | None = None


class BotCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    description: str = ""
    type: BotType = "telegram"
    secretId: str
    commands: list[BotCommand] = []
    defaultFunction: BotFunction | None = None


class BotUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=64)
    description: str | None = None
    commands: list[BotCommand] | None = None
    # PATCH semantics: missing → no change; explicit null → clear.
    defaultFunction: BotFunction | None = None


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
    defaultFunction: BotFunction | None = None
    deployedAt: str | None = None
    lastEventAt: str | None = None
    lastError: str | None = None
    requests24h: int = 0
    errors24h: int = 0
    createdAt: str
    updatedAt: str


class TestFunctionRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4096)
    commandIndex: int | None = None
    useDefault: bool = False


class TestFunctionResponse(BaseModel):
    output: str
    latencyMs: int
    raw: str


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


GatewayStatus = Literal["creating", "ready", "error"]


class GatewayCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    description: str = ""
    # Inline OpenAPI 3 spec (JSON or YAML). Capped to keep DDB items small;
    # AgentCore accepts inline schemas up to its own limit (currently 1MB,
    # but we cap lower for our DDB single-table item budget).
    openapiSpec: str = Field(min_length=1, max_length=200_000)
    # Bearer / API key passed to the upstream API by the gateway target.
    # Stored in Secrets Manager; never persisted on the Gateway item.
    token: str = Field(min_length=1, max_length=4096)


class Gateway(BaseModel):
    id: str
    tenantId: str
    ownerUserId: str
    name: str
    description: str = ""
    status: GatewayStatus = "creating"
    gatewayArn: str | None = None
    gatewayUrl: str | None = None
    targetId: str | None = None
    credentialProviderArn: str | None = None
    secretId: str  # internal Secret holding the API token
    lastError: str | None = None
    createdAt: str
    updatedAt: str


class GatewayTool(BaseModel):
    name: str
    description: str = ""


class GatewayTestResponse(BaseModel):
    tools: list[GatewayTool]
    latencyMs: int


HarnessStatus = Literal["creating", "ready", "error"]
# Allowlist of foundation model IDs the platform exposes in the create UI.
# The platform container image reads this via the MODEL_ID env var and
# routes to the right provider SDK. Bedrock model availability varies by
# region — operators may need to verify each is enabled in their account
# (Bedrock console → Model access).
HarnessModel = Literal[
    # Anthropic Claude family.
    "anthropic.claude-haiku-4-5-20251001-v1:0",
    "anthropic.claude-sonnet-4-6",
    "anthropic.claude-opus-4-7",
    # Cheap alternatives — open-weights reasoning + chat models on Bedrock.
    "deepseek.r1-v1:0",
    "deepseek.v3-v1:0",
    "minimax.abab-6.5s-chat-v1:0",
]


class HarnessCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    description: str = ""
    model: HarnessModel
    systemPrompt: str = Field(default="", max_length=8000)
    gatewayIds: list[str] = []


class HarnessGatewayUpdate(BaseModel):
    """Only mutable harness field post-create — gateway list.

    `model` and `systemPrompt` are baked into the runtime's env vars at
    CreateAgentRuntime time; changing them requires delete + recreate.
    """

    gatewayIds: list[str]


class Harness(BaseModel):
    id: str
    tenantId: str
    ownerUserId: str
    name: str
    description: str = ""
    model: HarnessModel
    systemPrompt: str = ""
    qualifier: str | None = None
    gatewayIds: list[str] = []
    status: HarnessStatus = "creating"
    agentRuntimeArn: str | None = None
    agentRuntimeId: str | None = None
    lastError: str | None = None
    createdAt: str
    updatedAt: str


class HarnessTestRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4096)


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
