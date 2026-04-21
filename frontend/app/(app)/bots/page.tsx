"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/platform/PageHeader";
import { StatusPill } from "@/components/platform/StatusPill";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EmptyState } from "@/components/platform/icons";
import { api } from "@/lib/api";
import type { Bot, BotStatus } from "@/lib/types";
import { relativeTime } from "@/lib/utils";

type Filter = "all" | BotStatus;

export default function BotsPage() {
  const [bots, setBots] = useState<Bot[]>([]);
  const [filter, setFilter] = useState<Filter>("all");
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listBots().then(setBots).finally(() => setLoading(false));
  }, []);

  const filtered = bots
    .filter((b) => filter === "all" || b.status === filter)
    .filter((b) => b.name.toLowerCase().includes(q.toLowerCase()));

  const counts: Record<Filter, number> = {
    all: bots.length,
    deployed: bots.filter((b) => b.status === "deployed").length,
    draft: bots.filter((b) => b.status === "draft").length,
    deploying: bots.filter((b) => b.status === "deploying").length,
    disabled: bots.filter((b) => b.status === "disabled").length,
    error: bots.filter((b) => b.status === "error").length,
  };

  return (
    <>
      <PageHeader
        title="Bots"
        description="Inbound triggers. Telegram only in Phase 1."
        right={
          <Link href="/bots/new">
            <Button variant="accent" size="md">New bot</Button>
          </Link>
        }
      />
      <div className="p-s-8 flex flex-col gap-s-6">
        <div className="flex items-center gap-[10px]">
          {(["all", "deployed", "draft", "error"] as Filter[]).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-[10px] h-[28px] rounded-sm font-mono text-mono-sm border transition-colors duration-75 ${
                filter === f
                  ? "border-border-strong bg-surface-2 text-text"
                  : "border-border text-text-dim hover:bg-surface-2"
              }`}
            >
              {f} <span className="text-text-mute ml-[4px]">{counts[f]}</span>
            </button>
          ))}
          <div className="ml-auto w-[240px]">
            <Input placeholder="search bots" value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
        </div>
        {loading ? (
          <EmptyState title="loading…" />
        ) : filtered.length === 0 ? (
          <EmptyState title="no bots match these filters" />
        ) : (
          <div className="card overflow-hidden">
            <div className="grid grid-cols-[1fr_100px_120px_140px_80px] gap-[12px] bg-surface-2 px-s-5 py-[8px] overline">
              <div>name</div>
              <div>type</div>
              <div>status</div>
              <div>last event</div>
              <div>commands</div>
            </div>
            {filtered.map((b) => (
              <Link
                key={b.id}
                href={`/bots/${b.id}`}
                className="grid grid-cols-[1fr_100px_120px_140px_80px] gap-[12px] items-center px-s-5 py-[10px] border-t border-border hover:bg-surface-2 transition-colors duration-75"
              >
                <div>
                  <div className="text-body">{b.name}</div>
                  <div className="font-mono text-mono-sm text-text-mute">{b.id}</div>
                </div>
                <div className="font-mono text-mono-sm text-text-dim">{b.type}</div>
                <div><StatusPill status={b.status} livePulse={b.status === "deployed"} /></div>
                <div className="font-mono text-mono-sm text-text-dim">{relativeTime(b.lastEventAt)}</div>
                <div className="font-mono text-mono-sm text-text-dim">{b.commands.length}</div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
