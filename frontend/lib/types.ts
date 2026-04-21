// Data types mirroring the backend DynamoDB items.

export type BotStatus = "draft" | "deploying" | "deployed" | "disabled" | "error";
export type BotType = "telegram";
export type Visibility = "private" | "published";

export interface BotCommand {
  cmd: string;
  template: string;
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
  deployedAt: string | null;
  lastEventAt: string | null;
  lastError: string | null;
  requests24h: number;
  errors24h: number;
  createdAt: string;
  updatedAt: string;
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
