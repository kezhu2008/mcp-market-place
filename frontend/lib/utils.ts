import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function relativeTime(ts: string | number | null | undefined): string {
  if (!ts) return "—";
  const t = typeof ts === "string" ? Date.parse(ts) : ts;
  if (isNaN(t)) return "—";
  const delta = Math.floor((Date.now() - t) / 1000);
  if (delta < 10) return "just now";
  if (delta < 60) return `${delta}s ago`;
  if (delta < 3600) return `${Math.floor(delta / 60)}m ago`;
  if (delta < 86400) return `${Math.floor(delta / 3600)}h ago`;
  if (delta < 60 * 86400) return `${Math.floor(delta / 86400)}d ago`;
  return new Date(t).toISOString().slice(0, 10);
}

export function shortId(id: string, prefix?: string): string {
  if (prefix && id.startsWith(prefix)) return id;
  return id.length > 14 ? `${id.slice(0, 7)}…${id.slice(-4)}` : id;
}
