"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/platform/PageHeader";
import { KpiCard } from "@/components/platform/KpiCard";
import { BotCard } from "@/components/platform/BotCard";
import { ActivityTable } from "@/components/platform/ActivityTable";
import { EmptyState } from "@/components/platform/icons";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { Bot, DashboardSummary, Event } from "@/lib/types";
import Link from "next/link";

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [bots, setBots] = useState<Bot[]>([]);
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        const [s, b, e] = await Promise.all([
          api.dashboard(),
          api.listBots(),
          api.listRecentEvents(25),
        ]);
        if (!mounted) return;
        setSummary(s);
        setBots(b);
        setEvents(e);
      } finally {
        if (mounted) setLoading(false);
      }
    }
    load();
    const iv = setInterval(load, 5000);
    return () => { mounted = false; clearInterval(iv); };
  }, []);

  return (
    <>
      <PageHeader
        title="Dashboard"
        description="Control plane overview."
        right={
          <Link href="/bots/new">
            <Button variant="accent" size="md">New bot</Button>
          </Link>
        }
      />
      <div className="p-s-5 md:p-s-8 flex flex-col gap-s-6">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-[10px]">
          <KpiCard label="deployed" value={summary?.botsDeployed ?? "—"} accentBar />
          <KpiCard label="drafts" value={summary?.botsDraft ?? "—"} />
          <KpiCard label="errors" value={summary?.botsError ?? "—"} />
          <KpiCard
            label="requests · 24h"
            value={summary?.requests24h ?? "—"}
            sub={summary ? `${summary.errors24h} errors` : undefined}
            accentBar
          />
        </div>
        <section>
          <div className="flex items-center justify-between mb-[12px]">
            <h2 className="overline">Bots</h2>
            <Link href="/bots" className="font-mono text-mono-sm text-text-mute hover:text-text">
              view all →
            </Link>
          </div>
          {loading ? (
            <EmptyState title="loading…" />
          ) : bots.length === 0 ? (
            <EmptyState title="no bots yet" sub="create one to get started" />
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-[12px]">
              {bots.slice(0, 6).map((b) => <BotCard key={b.id} bot={b} />)}
            </div>
          )}
        </section>
        <section>
          <h2 className="overline mb-[12px]">Recent activity</h2>
          <ActivityTable events={events} />
        </section>
      </div>
    </>
  );
}
