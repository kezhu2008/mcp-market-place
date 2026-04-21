"use client";

import { useState } from "react";
import { cn, relativeTime } from "@/lib/utils";
import type { Event, EventType } from "@/lib/types";

const DOT_COLOR: Partial<Record<EventType, string>> = {
  "webhook.received": "bg-blue",
  "webhook.bad_token": "bg-red",
  "webhook.error": "bg-red",
  "deploy.started": "bg-amber",
  "deploy.succeeded": "bg-accent",
  "deploy.failed": "bg-red",
  "bot.created": "bg-text-dim",
  "bot.updated": "bg-text-dim",
  "bot.deleted": "bg-text-dim",
  "bot.disabled": "bg-text-dim",
  "secret.created": "bg-violet",
  "secret.rotated": "bg-violet",
};

const GRID = "grid grid-cols-[100px_160px_1fr_100px_24px] gap-[8px]";

export function ActivityTable({ events }: { events: Event[] }) {
  const [expanded, setExpanded] = useState<string | null>(null);

  if (events.length === 0) {
    return (
      <div className="card p-[40px] flex items-center justify-center font-mono text-mono text-text-mute">
        no events yet
      </div>
    );
  }

  return (
    <div className="card overflow-hidden">
      <div className={cn(GRID, "bg-surface-2 px-[14px] py-[8px] overline")}>
        <div>time</div>
        <div>event</div>
        <div>message</div>
        <div>actor</div>
        <div />
      </div>
      {events.map((e) => {
        const isOpen = expanded === e.id;
        return (
          <div key={e.id} className="border-t border-border">
            <button
              onClick={() => setExpanded(isOpen ? null : e.id)}
              className={cn(
                GRID,
                "w-full items-center px-[14px] py-[9px] text-left font-mono text-mono text-text-dim hover:bg-surface-2 transition-colors duration-75"
              )}
            >
              <span>{relativeTime(e.ts)}</span>
              <span className="flex items-center gap-[6px]">
                <span className={cn("w-[5px] h-[5px] rounded-full", DOT_COLOR[e.type] ?? "bg-text-dim")} />
                {e.type}
              </span>
              <span className="text-text truncate">{e.msg}</span>
              <span className="truncate">{e.actor}</span>
              <span className="text-text-mute">{isOpen ? "−" : "+"}</span>
            </button>
            {isOpen && (
              <pre className="bg-surface-2 border-t border-border px-[14px] py-[10px] font-mono text-mono-sm text-text-dim overflow-x-auto">
                {JSON.stringify(e.details, null, 2)}
              </pre>
            )}
          </div>
        );
      })}
    </div>
  );
}
