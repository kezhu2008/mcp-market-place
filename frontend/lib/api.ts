"use client";

import { getIdToken } from "./auth";
import type {
  Bot,
  BotCommand,
  DashboardSummary,
  Event,
  Gateway,
  GatewayCreate,
  GatewayTestResponse,
  Harness,
  HarnessCreate,
  Secret,
  TestFunctionRequest,
  TestFunctionResponse,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

class ApiError extends Error {
  constructor(public status: number, message: string, public body?: unknown) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = await getIdToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string> | undefined),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const method = (init?.method ?? "GET").toUpperCase();
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, { ...init, headers });
  } catch (e) {
    // Network / CORS / DNS — fetch threw before getting a response. The
    // browser console will have the precise reason; the user-facing message
    // names the request so it's easy to pin down.
    const msg = e instanceof Error ? e.message : String(e);
    throw new ApiError(0, `Network error: ${method} ${path} — ${msg}`);
  }

  if (!res.ok) {
    let body: unknown = undefined;
    let detail = "";
    try {
      body = await res.json();
      const d = (body as { detail?: unknown })?.detail;
      if (typeof d === "string") detail = d;
      else if (d !== undefined) detail = JSON.stringify(d);
    } catch { /* response had no JSON body */ }
    const summary = detail
      ? `${res.status} ${res.statusText}: ${detail}`
      : `${res.status} ${res.statusText}`;
    throw new ApiError(res.status, `${method} ${path} — ${summary}`, body);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  // Bots
  listBots: () => request<Bot[]>("/bots"),
  getBot: (id: string) => request<Bot>(`/bots/${id}`),
  createBot: (data: Partial<Bot> & { name: string; secretId: string; commands: BotCommand[] }) =>
    request<Bot>("/bots", { method: "POST", body: JSON.stringify(data) }),
  updateBot: (id: string, data: Partial<Bot>) =>
    request<Bot>(`/bots/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteBot: (id: string) => request<void>(`/bots/${id}`, { method: "DELETE" }),
  deployBot: (id: string) => request<Bot>(`/bots/${id}/deploy`, { method: "POST" }),
  disableBot: (id: string) => request<Bot>(`/bots/${id}/disable`, { method: "POST" }),
  testBotFunction: (id: string, body: TestFunctionRequest) =>
    request<TestFunctionResponse>(`/bots/${id}/test-function`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  // Secrets
  listSecrets: () => request<Secret[]>("/secrets"),
  createSecret: (data: { name: string; description: string; value: string }) =>
    request<Secret>("/secrets", { method: "POST", body: JSON.stringify(data) }),
  rotateSecret: (id: string, value: string) =>
    request<Secret>(`/secrets/${id}/rotate`, { method: "POST", body: JSON.stringify({ value }) }),
  deleteSecret: (id: string) => request<void>(`/secrets/${id}`, { method: "DELETE" }),

  // Gateways
  listGateways: () => request<Gateway[]>("/gateways"),
  getGateway: (id: string) => request<Gateway>(`/gateways/${id}`),
  createGateway: (data: GatewayCreate) =>
    request<Gateway>("/gateways", { method: "POST", body: JSON.stringify(data) }),
  deleteGateway: (id: string) => request<void>(`/gateways/${id}`, { method: "DELETE" }),
  testGateway: (id: string) =>
    request<GatewayTestResponse>(`/gateways/${id}/test`, { method: "POST" }),

  // Harnesses
  listHarnesses: () => request<Harness[]>("/harnesses"),
  getHarness: (id: string) => request<Harness>(`/harnesses/${id}`),
  createHarness: (data: HarnessCreate) =>
    request<Harness>("/harnesses", { method: "POST", body: JSON.stringify(data) }),
  updateHarnessGateways: (id: string, gatewayIds: string[]) =>
    request<Harness>(`/harnesses/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ gatewayIds }),
    }),
  deleteHarness: (id: string) => request<void>(`/harnesses/${id}`, { method: "DELETE" }),
  testHarness: (id: string, text: string) =>
    request<TestFunctionResponse>(`/harnesses/${id}/test`, {
      method: "POST",
      body: JSON.stringify({ text }),
    }),

  // Events
  listBotEvents: (botId: string, limit = 50) =>
    request<Event[]>(`/bots/${botId}/events?limit=${limit}`),
  listRecentEvents: (limit = 25) =>
    request<Event[]>(`/events?limit=${limit}`),

  // Dashboard
  dashboard: () => request<DashboardSummary>("/dashboard"),
};

export { ApiError };
