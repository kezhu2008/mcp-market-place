// Data types mirroring the backend DynamoDB items.

export type BotStatus = "draft" | "deploying" | "deployed" | "disabled" | "error";
export type BotType = "telegram";
export type Visibility = "private" | "published";

// AgentCore runtime ARN, e.g.
//   arn:aws:bedrock-agentcore:ap-southeast-2:668532754740:runtime/sales-harness
export const AGENTCORE_RUNTIME_ARN_RE =
  /^arn:aws:bedrock-agentcore:[a-z0-9-]+:\d{12}:runtime\/.+$/;

export interface BedrockHarnessFunction {
  type: "bedrock_harness";
  agentRuntimeArn: string;
  qualifier?: string | null;
  promptTemplate?: string | null;
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
