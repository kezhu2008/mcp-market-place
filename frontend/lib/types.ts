// Data types mirroring the backend DynamoDB items.

export type BotStatus = "draft" | "deploying" | "deployed" | "disabled" | "error";
export type BotType = "telegram";
export type Visibility = "private" | "published";

export interface BedrockHarnessFunction {
  type: "bedrock_harness";
  // Reference to a platform-managed Harness item. The webhook resolves
  // this to the runtime ARN + the harness's linked gateway URLs at
  // invoke time; users never type the ARN themselves.
  harnessId: string;
  promptTemplate?: string | null;
}

export type GatewayStatus = "creating" | "ready" | "error";

export interface Gateway {
  id: string;
  tenantId: string;
  ownerUserId: string;
  name: string;
  description: string;
  status: GatewayStatus;
  gatewayArn: string | null;
  gatewayUrl: string | null;
  targetId: string | null;
  credentialProviderArn: string | null;
  secretId: string;
  lastError: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface GatewayCreate {
  name: string;
  description?: string;
  openapiSpec: string;
  token: string;
}

export interface GatewayTool {
  name: string;
  description: string;
}

export interface GatewayTestResponse {
  tools: GatewayTool[];
  latencyMs: number;
}

export type HarnessStatus = "creating" | "ready" | "error";
// Allowlist of Bedrock foundation models the platform exposes in the
// "Create harness" form. Mirror of the backend `HarnessModel` literal.
export type HarnessModel =
  | "anthropic.claude-haiku-4-5-20251001-v1:0"
  | "anthropic.claude-sonnet-4-6"
  | "anthropic.claude-opus-4-7"
  | "deepseek.r1-v1:0"
  | "deepseek.v3-v1:0"
  | "minimax.abab-6.5s-chat-v1:0";

// Order ≈ price ascending so cheap models render first in the dropdown.
export const HARNESS_MODELS: { id: HarnessModel; label: string }[] = [
  { id: "deepseek.v3-v1:0", label: "DeepSeek V3 · cheap" },
  { id: "deepseek.r1-v1:0", label: "DeepSeek R1 · cheap reasoning" },
  { id: "minimax.abab-6.5s-chat-v1:0", label: "MiniMax abab 6.5s · cheap" },
  { id: "anthropic.claude-haiku-4-5-20251001-v1:0", label: "Claude Haiku 4.5" },
  { id: "anthropic.claude-sonnet-4-6", label: "Claude Sonnet 4.6" },
  { id: "anthropic.claude-opus-4-7", label: "Claude Opus 4.7" },
];

export interface Harness {
  id: string;
  tenantId: string;
  ownerUserId: string;
  name: string;
  description: string;
  model: HarnessModel;
  systemPrompt: string;
  qualifier: string | null;
  gatewayIds: string[];
  status: HarnessStatus;
  agentRuntimeArn: string | null;
  agentRuntimeId: string | null;
  lastError: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface HarnessCreate {
  name: string;
  description?: string;
  model: HarnessModel;
  systemPrompt?: string;
  gatewayIds?: string[];
}

export type BotFunction = BedrockHarnessFunction;

export interface BotCommand {
  cmd: string;
  // null/undefined → inherit Bot.defaultFunction at runtime.
  function?: BotFunction | null;
}

export interface Bot {
  id: string;
  tenantId: string;
  ownerUserId: string;
  visibility: Visibility;
  priceCents: number;
  name: string;
  description: string;
  type: BotType;
  status: BotStatus;
  secretId: string;
  webhookPath: string;
  commands: BotCommand[];
  defaultFunction?: BotFunction | null;
  deployedAt: string | null;
  lastEventAt: string | null;
  lastError: string | null;
  requests24h: number;
  errors24h: number;
  createdAt: string;
  updatedAt: string;
}

export interface TestFunctionRequest {
  text: string;
  commandIndex?: number | null;
  useDefault?: boolean;
}

export interface TestFunctionResponse {
  output: string;
  latencyMs: number;
  raw: string;
}

export interface Secret {
  id: string;
  tenantId: string;
  ownerUserId: string;
  visibility: Visibility;
  priceCents: number;
  name: string;
  description: string;
  smArn: string;
  lastRotatedAt: string;
  lastUsedAt: string | null;
  createdAt: string;
}

export type EventType =
  | "bot.created"
  | "bot.updated"
  | "bot.deleted"
  | "bot.disabled"
  | "deploy.started"
  | "deploy.succeeded"
  | "deploy.failed"
  | "webhook.received"
  | "webhook.bad_token"
  | "webhook.error"
  | "webhook.no_function"
  | "webhook.harness.invoked"
  | "webhook.harness.error"
  | "function.tested"
  | "secret.created"
  | "secret.rotated";

export interface Event {
  id: string;
  botId: string;
  ts: string;
  type: EventType;
  msg: string;
  actor: string;
  details: Record<string, unknown>;
}

export interface DashboardSummary {
  botsDeployed: number;
  botsDraft: number;
  botsError: number;
  requests24h: number;
  errors24h: number;
}
