"use client";

import { getIdToken } from "./auth";
import type { Bot, BotCommand, DashboardSummary, Event, Secret } from "./types";

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

  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    let body: unknown = undefined;
    try { body = await res.json(); } catch { /* ignore */ }
    throw new ApiError(res.status, `${res.status} ${res.statusText}`, body);
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

  // Secrets
  listSecrets: () => request<Secret[]>("/secrets"),
  createSecret: (data: { name: string; description: string; value: string }) =>
    request<Secret>("/secrets", { method: "POST", body: JSON.stringify(data) }),
  rotateSecret: (id: string, value: string) =>
    request<Secret>(`/secrets/${id}/rotate`, { method: "POST", body: JSON.stringify({ value }) }),
  deleteSecret: (id: string) => request<void>(`/secrets/${id}`, { method: "DELETE" }),

  // Events
  listBotEvents: (botId: string, limit = 50) =>
    request<Event[]>(`/bots/${botId}/events?limit=${limit}`),
  listRecentEvents: (limit = 25) =>
    request<Event[]>(`/events?limit=${limit}`),

  // Dashboard
  dashboard: () => request<DashboardSummary>("/dashboard"),
};

export { ApiError };
