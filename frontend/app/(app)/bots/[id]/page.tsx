"use client";

import { use, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { PageHeader } from "@/components/platform/PageHeader";
import { StatusPill } from "@/components/platform/StatusPill";
import { Button } from "@/components/ui/button";
import { Input, Label, Textarea } from "@/components/ui/input";
import { ActivityTable } from "@/components/platform/ActivityTable";
import { Modal } from "@/components/platform/Modal";
import { EmptyState } from "@/components/platform/icons";
import { useToast } from "@/components/platform/Toast";
import { api } from "@/lib/api";
import type { Bot, BotCommand, Event } from "@/lib/types";
import { relativeTime } from "@/lib/utils";

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "configuration", label: "Configuration" },
  { id: "handler", label: "Handler", stub: true },
  { id: "mcp", label: "MCP Bindings", stub: true },
  { id: "activity", label: "Activity" },
  { id: "settings", label: "Settings" },
] as const;

type Tab = typeof TABS[number]["id"];

export default function BotDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const searchParams = useSearchParams();
  const tab = (searchParams.get("tab") ?? "overview") as Tab;
  const toast = useToast();
  const [bot, setBot] = useState<Bot | null>(null);
  const [events, setEvents] = useState<Event[]>([]);
  const [deployOpen, setDeployOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  async function reload() {
    const [b, e] = await Promise.all([api.getBot(id), api.listBotEvents(id, 50)]);
    setBot(b);
    setEvents(e);
  }

  useEffect(() => {
    reload();
    const iv = setInterval(reload, 3000);
    return () => clearInterval(iv);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function doDeploy() {
    setBusy(true);
    try {
      await api.deployBot(id);
      toast.push({ kind: "success", title: "Deployed", body: bot!.name });
      setDeployOpen(false);
      await reload();
    } catch (e) {
      toast.push({ kind: "error", title: "Deploy failed", body: (e as Error).message });
    } finally {
      setBusy(false);
    }
  }

  async function doDisable() {
    setBusy(true);
    try {
      await api.disableBot(id);
      toast.push({ kind: "info", title: "Disabled" });
      await reload();
    } finally { setBusy(false); }
  }

  async function doDelete() {
    setBusy(true);
    try {
      await api.deleteBot(id);
      toast.push({ kind: "info", title: "Deleted" });
      router.push("/bots");
    } finally { setBusy(false); }
  }

  if (!bot) {
    return (
      <>
        <PageHeader title="Loading…" breadcrumbs={[{ label: "bots", href: "/bots" }]} />
        <div className="p-s-8"><EmptyState title="loading…" /></div>
      </>
    );
  }

  const canDeploy = ["draft", "error", "disabled"].includes(bot.status);

  return (
    <>
      <PageHeader
        title={<>{bot.name}<StatusPill status={bot.status} livePulse={bot.status === "deployed"} /></>}
        breadcrumbs={[{ label: "bots", href: "/bots" }, { label: bot.name }]}
        description={bot.description || undefined}
        right={
          <>
            {bot.status === "deployed" ? (
              <Button variant="secondary" size="md" disabled={busy} onClick={doDisable}>Disable</Button>
            ) : (
              <Button variant="accent" size="md" disabled={!canDeploy || busy} onClick={() => setDeployOpen(true)}>
                {bot.status === "error" ? "Redeploy" : "Deploy"}
              </Button>
            )}
          </>
        }
        tabs={TABS.map((t) => ({ id: t.id, label: t.label, href: `/bots/${id}?tab=${t.id}` }))}
        activeTab={tab}
      />
      <div className="p-s-8">
        {tab === "overview" && <OverviewTab bot={bot} />}
        {tab === "configuration" && <ConfigTab bot={bot} onSaved={reload} />}
        {tab === "handler" && <StubTab name="Handler" />}
        {tab === "mcp" && <StubTab name="MCP Bindings" />}
        {tab === "activity" && <ActivityTable events={events} />}
        {tab === "settings" && <SettingsTab bot={bot} onDelete={() => setDeleteOpen(true)} />}
      </div>

      <Modal
        open={deployOpen}
        onClose={() => setDeployOpen(false)}
        title={`Deploy "${bot.name}"?`}
        footer={
          <>
            <Button variant="secondary" onClick={() => setDeployOpen(false)}>Cancel</Button>
            <Button variant="accent" disabled={busy} onClick={doDeploy}>
              {busy ? "Deploying…" : "Deploy"}
            </Button>
          </>
        }
      >
        <ul className="font-mono text-mono text-text-dim flex flex-col gap-[4px]">
          <li>· register Telegram webhook at <span className="code">/{bot.webhookPath}</span></li>
          <li>· handle {bot.commands.length} command(s)</li>
          <li>· no downtime — previous webhook replaced atomically</li>
        </ul>
      </Modal>

      <Modal
        open={deleteOpen}
        onClose={() => setDeleteOpen(false)}
        title={`Delete "${bot.name}"?`}
        footer={
          <>
            <Button variant="secondary" onClick={() => setDeleteOpen(false)}>Cancel</Button>
            <Button variant="danger" disabled={busy} onClick={doDelete}>Delete</Button>
          </>
        }
      >
        <p className="text-body text-text-dim">
          Tears down the Lambda, removes the Telegram webhook, and deletes all activity history.
          This cannot be undone.
        </p>
      </Modal>
    </>
  );
}

function OverviewTab({ bot }: { bot: Bot }) {
  return (
    <div className="grid grid-cols-2 gap-s-6">
      <div className="card p-s-5">
        <div className="overline mb-[10px]">summary</div>
        <dl className="grid grid-cols-[140px_1fr] gap-y-[8px] font-mono text-mono">
          <dt className="text-text-mute">type</dt><dd>{bot.type}</dd>
          <dt className="text-text-mute">webhook</dt><dd className="code truncate">/{bot.webhookPath}</dd>
          <dt className="text-text-mute">secret</dt><dd className="truncate">{bot.secretId}</dd>
          <dt className="text-text-mute">deployed at</dt><dd>{relativeTime(bot.deployedAt)}</dd>
          <dt className="text-text-mute">last event</dt><dd>{relativeTime(bot.lastEventAt)}</dd>
        </dl>
      </div>
      <div className="card p-s-5">
        <div className="overline mb-[10px]">24h health</div>
        <div className="flex gap-s-7">
          <div>
            <div className="overline">requests</div>
            <div className="text-kpi">{bot.requests24h}</div>
          </div>
          <div>
            <div className="overline">errors</div>
            <div className="text-kpi">{bot.errors24h}</div>
          </div>
        </div>
      </div>
      <div className="card p-s-5 col-span-2">
        <div className="overline mb-[10px]">commands</div>
        {bot.commands.length === 0 ? (
          <div className="font-mono text-mono text-text-mute">no commands</div>
        ) : (
          <div className="flex flex-col gap-[6px]">
            {bot.commands.map((c, i) => (
              <div key={i} className="flex items-center gap-[10px] font-mono text-mono">
                <span className="code">{c.cmd}</span>
                <span className="text-text-mute">→</span>
                <span className="text-text-dim truncate">{c.template}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ConfigTab({ bot, onSaved }: { bot: Bot; onSaved: () => void }) {
  const [name, setName] = useState(bot.name);
  const [description, setDescription] = useState(bot.description);
  const [commands, setCommands] = useState<BotCommand[]>(bot.commands);
  const [saving, setSaving] = useState(false);
  const toast = useToast();

  const dirty = name !== bot.name || description !== bot.description ||
    JSON.stringify(commands) !== JSON.stringify(bot.commands);

  async function save() {
    setSaving(true);
    try {
      await api.updateBot(bot.id, { name, description, commands });
      toast.push({ kind: "success", title: "Saved" });
      onSaved();
    } catch (e) {
      toast.push({ kind: "error", title: "Save failed", body: (e as Error).message });
    } finally { setSaving(false); }
  }

  return (
    <div className="flex flex-col gap-s-6 max-w-[720px]">
      <div className="card p-s-5 flex flex-col gap-s-5">
        <div>
          <Label>name</Label>
          <Input value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div>
          <Label>description</Label>
          <Textarea rows={3} value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>
      </div>
      <div className="card p-s-5">
        <Label>commands</Label>
        <div className="flex flex-col gap-[6px]">
          {commands.map((c, i) => (
            <div key={i} className="flex gap-[8px]">
              <Input mono className="w-[140px]" value={c.cmd} onChange={(e) => {
                const next = [...commands]; next[i] = { ...next[i], cmd: e.target.value }; setCommands(next);
              }} />
              <Input className="flex-1" value={c.template} onChange={(e) => {
                const next = [...commands]; next[i] = { ...next[i], template: e.target.value }; setCommands(next);
              }} />
              <Button variant="ghost" size="sm" onClick={() => setCommands(commands.filter((_, j) => j !== i))}>remove</Button>
            </div>
          ))}
          <Button variant="secondary" size="sm" onClick={() => setCommands([...commands, { cmd: "/", template: "" }])}>
            + add command
          </Button>
        </div>
      </div>
      <div className="flex items-center gap-[10px]">
        <span className="font-mono text-mono-sm text-text-mute">
          {dirty ? "unsaved changes" : "in sync"}
        </span>
        <Button variant="accent" disabled={!dirty || saving} onClick={save} className="ml-auto">
          {saving ? "Saving…" : "Save changes"}
        </Button>
      </div>
    </div>
  );
}

function StubTab({ name }: { name: string }) {
  return <EmptyState title={`${name} — coming in Phase 2`} sub="schema ready, UI deferred" />;
}

function SettingsTab({ bot, onDelete }: { bot: Bot; onDelete: () => void }) {
  return (
    <div className="flex flex-col gap-s-6 max-w-[720px]">
      <div className="card p-s-5">
        <Label>webhook path</Label>
        <div className="flex gap-[8px] items-center">
          <code className="code flex-1">/{bot.webhookPath}</code>
        </div>
      </div>
      <div className="card p-s-5 border-[#ef444444]">
        <div className="overline text-red mb-[8px]">danger zone</div>
        <p className="text-body text-text-dim mb-s-5">
          Tears down the Lambda, removes the Telegram webhook, and deletes all activity history.
          This cannot be undone.
        </p>
        <Button variant="danger" onClick={onDelete}>Delete bot</Button>
      </div>
    </div>
  );
}
