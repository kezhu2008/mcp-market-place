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
import type {
  Bot,
  BotCommand,
  BotFunction,
  Event,
  Harness,
} from "@/lib/types";
import { relativeTime } from "@/lib/utils";

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "configuration", label: "Configuration" },
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
        <div className="p-s-5 md:p-s-8"><EmptyState title="loading…" /></div>
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
      <div className="p-s-5 md:p-s-8">
        {tab === "overview" && <OverviewTab bot={bot} />}
        {tab === "configuration" && <ConfigTab bot={bot} onSaved={reload} />}
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

function harnessLabel(harnesses: Harness[], harnessId: string): string {
  const h = harnesses.find((x) => x.id === harnessId);
  return h ? h.name : harnessId;
}

function fnSummary(
  fn: BotFunction | null | undefined,
  harnesses: Harness[],
  fallbackLabel: string,
): string {
  if (!fn) return fallbackLabel;
  return `harness:${harnessLabel(harnesses, fn.harnessId)}`;
}

function OverviewTab({ bot }: { bot: Bot }) {
  const [harnesses, setHarnesses] = useState<Harness[]>([]);
  useEffect(() => {
    api.listHarnesses().then(setHarnesses).catch(() => setHarnesses([]));
  }, []);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-s-6">
      <div className="card p-s-5">
        <div className="overline mb-[10px]">summary</div>
        <dl className="grid grid-cols-[100px_1fr] md:grid-cols-[140px_1fr] gap-y-[8px] font-mono text-mono">
          <dt className="text-text-mute">type</dt><dd>{bot.type}</dd>
          <dt className="text-text-mute">webhook</dt><dd className="code truncate">/{bot.webhookPath}</dd>
          <dt className="text-text-mute">secret</dt><dd className="truncate">{bot.secretId}</dd>
          <dt className="text-text-mute">default fn</dt>
          <dd className="truncate">{fnSummary(bot.defaultFunction, harnesses, "(none)")}</dd>
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
      <div className="card p-s-5 md:col-span-2">
        <div className="overline mb-[10px]">commands</div>
        {bot.commands.length === 0 ? (
          <div className="font-mono text-mono text-text-mute">no commands</div>
        ) : (
          <div className="flex flex-col gap-[6px]">
            {bot.commands.map((c, i) => (
              <div key={i} className="flex items-center gap-[10px] font-mono text-mono">
                <span className="code">{c.cmd}</span>
                <span className="text-text-mute">→</span>
                <span className="text-text-dim truncate">
                  {fnSummary(c.function, harnesses, "(default)")}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

type TestPanelState = { loading: boolean; output?: string; latencyMs?: number; error?: string };

function FunctionEditor({
  value,
  onChange,
  emptyLabel,
  showInheritOption,
  harnesses,
}: {
  value: BotFunction | null | undefined;
  onChange: (next: BotFunction | null) => void;
  emptyLabel: string;
  showInheritOption: boolean;
  harnesses: Harness[];
}) {
  const useDefault = !value;
  const selected = value ? harnesses.find((h) => h.id === value.harnessId) : undefined;

  return (
    <div className="flex flex-col gap-[6px] mt-[6px]">
      {showInheritOption && (
        <label className="flex items-center gap-[6px] font-mono text-mono-sm text-text-mute">
          <input
            type="checkbox"
            checked={useDefault}
            onChange={(e) => {
              if (e.target.checked) onChange(null);
              else {
                const first = harnesses.find((h) => h.status === "ready");
                onChange({
                  type: "bedrock_harness",
                  harnessId: first?.id ?? "",
                });
              }
            }}
          />
          inherit default function
        </label>
      )}
      {!useDefault && (
        <>
          <div>
            <Label>harness</Label>
            {harnesses.length === 0 ? (
              <div className="font-mono text-mono-sm text-text-mute">
                no harnesses yet — <a href="/harnesses" className="text-accent">create one</a> first
              </div>
            ) : (
              <select
                value={value!.harnessId}
                onChange={(e) => onChange({ ...value!, harnessId: e.target.value })}
                className="h-[34px] w-full bg-surface border border-border rounded-sm px-[10px] text-body"
              >
                <option value="">choose a harness…</option>
                {harnesses.map((h) => (
                  <option key={h.id} value={h.id} disabled={h.status !== "ready"}>
                    🤖 {h.name} {h.status !== "ready" ? `· ${h.status}` : ""}
                  </option>
                ))}
              </select>
            )}
            {selected && (
              <div className="font-mono text-mono-sm text-text-mute mt-[4px]">
                {selected.gatewayIds.length} gateway(s) · model: {selected.model}
              </div>
            )}
          </div>
          <div>
            <Label>promptTemplate (optional)</Label>
            <Textarea
              rows={2}
              value={value!.promptTemplate ?? ""}
              onChange={(e) =>
                onChange({ ...value!, promptTemplate: e.target.value || null })
              }
              placeholder="default: {text} (the user's message verbatim)"
            />
          </div>
        </>
      )}
      {useDefault && (
        <div className="font-mono text-mono-sm text-text-mute">{emptyLabel}</div>
      )}
    </div>
  );
}

function TestPanel({
  botId,
  body,
  disabled,
}: {
  botId: string;
  body: () => { commandIndex?: number | null; useDefault?: boolean };
  disabled: boolean;
}) {
  const [text, setText] = useState("hello");
  const [state, setState] = useState<TestPanelState>({ loading: false });
  const toast = useToast();

  async function run() {
    setState({ loading: true });
    try {
      const res = await api.testBotFunction(botId, { text, ...body() });
      setState({ loading: false, output: res.output, latencyMs: res.latencyMs });
    } catch (e) {
      const msg = (e as Error).message;
      setState({ loading: false, error: msg });
      toast.push({ kind: "error", title: "Test failed", body: msg });
    }
  }

  return (
    <div className="mt-[10px] flex flex-col gap-[6px]">
      <div className="flex gap-[8px]">
        <Input
          className="flex-1"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="sample input"
        />
        <Button
          variant="secondary"
          size="sm"
          onClick={run}
          disabled={disabled || state.loading || !text.trim()}
        >
          {state.loading ? "Testing…" : "Test"}
        </Button>
      </div>
      {state.output !== undefined && (
        <div className="bg-surface-2 border border-border rounded-sm p-[8px] font-mono text-mono-sm">
          <div className="text-text-mute mb-[4px]">
            output · {state.latencyMs}ms
          </div>
          <pre className="whitespace-pre-wrap text-text-dim">{state.output}</pre>
        </div>
      )}
      {state.error && (
        <div className="font-mono text-mono-sm text-red">{state.error}</div>
      )}
    </div>
  );
}

function ConfigTab({ bot, onSaved }: { bot: Bot; onSaved: () => void }) {
  const [name, setName] = useState(bot.name);
  const [description, setDescription] = useState(bot.description);
  const [commands, setCommands] = useState<BotCommand[]>(bot.commands);
  const [defaultFunction, setDefaultFunction] = useState<BotFunction | null>(
    bot.defaultFunction ?? null,
  );
  const [harnesses, setHarnesses] = useState<Harness[]>([]);
  const [saving, setSaving] = useState(false);
  const toast = useToast();

  useEffect(() => {
    api.listHarnesses().then(setHarnesses).catch(() => setHarnesses([]));
  }, []);

  const dirty =
    name !== bot.name ||
    description !== bot.description ||
    JSON.stringify(commands) !== JSON.stringify(bot.commands) ||
    JSON.stringify(defaultFunction ?? null) !== JSON.stringify(bot.defaultFunction ?? null);

  // Every configured function must point at a real harness.
  const fnIsValid = (fn: BotFunction | null | undefined) =>
    !fn || harnesses.some((h) => h.id === fn.harnessId);
  const allValid =
    fnIsValid(defaultFunction) && commands.every((c) => fnIsValid(c.function));

  async function save() {
    setSaving(true);
    try {
      await api.updateBot(bot.id, {
        name,
        description,
        commands,
        // PATCH semantics: explicit null clears defaultFunction.
        defaultFunction,
      });
      toast.push({ kind: "success", title: "Saved" });
      onSaved();
    } catch (e) {
      toast.push({ kind: "error", title: "Save failed", body: (e as Error).message });
    } finally { setSaving(false); }
  }

  return (
    <div className="flex flex-col gap-s-6 max-w-[820px]">
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
        <div className="flex items-center justify-between mb-[6px]">
          <Label className="mb-0">default handler (non-slash messages, fallback)</Label>
        </div>
        <div className="font-mono text-mono-sm text-text-mute mb-[6px]">
          invoked for any message without a matching slash command, and for slash commands that don&rsquo;t override their own function.
        </div>
        <FunctionEditor
          value={defaultFunction}
          onChange={setDefaultFunction}
          emptyLabel="(none — bot will not reply when no command matches)"
          showInheritOption={false}
          harnesses={harnesses}
        />
        {!defaultFunction && harnesses.length > 0 && (
          <button
            type="button"
            className="font-mono text-mono-sm text-accent mt-[6px]"
            onClick={() => {
              const first = harnesses.find((h) => h.status === "ready");
              setDefaultFunction({
                type: "bedrock_harness",
                harnessId: first?.id ?? "",
              });
            }}
          >
            + configure default function
          </button>
        )}
        <TestPanel
          botId={bot.id}
          body={() => ({ useDefault: true })}
          disabled={!defaultFunction || !defaultFunction.harnessId || dirty}
        />
        {dirty && (
          <div className="font-mono text-mono-sm text-text-mute mt-[6px]">
            save first to test pending changes
          </div>
        )}
      </div>

      <div className="card p-s-5">
        <Label>commands</Label>
        <div className="flex flex-col gap-s-5">
          {commands.map((c, i) => (
            <div key={i} className="border border-border rounded-sm p-[10px]">
              <div className="flex gap-[8px] items-center">
                <Input
                  mono
                  className="w-[160px]"
                  value={c.cmd}
                  onChange={(e) => {
                    const next = [...commands];
                    next[i] = { ...next[i], cmd: e.target.value };
                    setCommands(next);
                  }}
                />
                <span className="font-mono text-mono-sm text-text-mute">
                  → {fnSummary(c.function, harnesses, "default")}
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="ml-auto"
                  onClick={() => setCommands(commands.filter((_, j) => j !== i))}
                >
                  remove
                </Button>
              </div>
              <details className="mt-[8px]">
                <summary className="cursor-pointer font-mono text-mono-sm text-accent">
                  function override
                </summary>
                <FunctionEditor
                  value={c.function ?? null}
                  onChange={(next) => {
                    const arr = [...commands];
                    arr[i] = { ...arr[i], function: next };
                    setCommands(arr);
                  }}
                  emptyLabel="inherits default function"
                  showInheritOption={true}
                  harnesses={harnesses}
                />
                <TestPanel
                  botId={bot.id}
                  body={() => ({ commandIndex: i })}
                  disabled={dirty}
                />
              </details>
            </div>
          ))}
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setCommands([...commands, { cmd: "/", function: null }])}
          >
            + add command
          </Button>
        </div>
      </div>

      <div className="flex items-center gap-[10px]">
        <span className="font-mono text-mono-sm text-text-mute">
          {dirty ? "unsaved changes" : "in sync"}
        </span>
        <Button
          variant="accent"
          disabled={!dirty || saving || !allValid}
          onClick={save}
          className="ml-auto"
        >
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
