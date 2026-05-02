"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/platform/PageHeader";
import { Button } from "@/components/ui/button";
import { Input, Label, Textarea } from "@/components/ui/input";
import { Modal } from "@/components/platform/Modal";
import { EmptyState } from "@/components/platform/icons";
import { api } from "@/lib/api";
import type { Gateway, Harness, HarnessModel } from "@/lib/types";
import { HARNESS_MODELS } from "@/lib/types";
import { relativeTime } from "@/lib/utils";
import { useToast } from "@/components/platform/Toast";

export default function HarnessesPage() {
  const [harnesses, setHarnesses] = useState<Harness[]>([]);
  const [gateways, setGateways] = useState<Gateway[]>([]);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [testFor, setTestFor] = useState<Harness | null>(null);
  const [deleteFor, setDeleteFor] = useState<Harness | null>(null);
  const [redeployingId, setRedeployingId] = useState<string | null>(null);
  const toast = useToast();

  async function redeploy(h: Harness) {
    setRedeployingId(h.id);
    try {
      await api.redeployHarness(h.id);
      toast.push({ kind: "success", title: "Redeployed", body: `🤖 ${h.name}` });
    } catch (e) {
      toast.push({ kind: "error", title: "Redeploy failed", body: (e as Error).message });
    } finally {
      setRedeployingId(null);
      load();
    }
  }

  async function load() {
    setLoading(true);
    try {
      const [hns, gws] = await Promise.all([
        api.listHarnesses(),
        api.listGateways().catch(() => [] as Gateway[]),
      ]);
      setHarnesses(hns);
      setGateways(gws);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { load(); }, []);

  return (
    <>
      <PageHeader
        title="Harnesses"
        description="Platform-managed AgentCore runtimes. Each harness picks a model + system prompt and links the gateways it can call as MCP tools."
        right={<Button variant="accent" onClick={() => setCreateOpen(true)}>Create harness</Button>}
      />
      <div className="p-s-5 md:p-s-8">
        {loading ? (
          <EmptyState title="loading…" />
        ) : harnesses.length === 0 ? (
          <EmptyState title="no harnesses yet" sub="create one to wire up a bot" />
        ) : (
          <div className="overflow-x-auto">
          <div className="card overflow-hidden min-w-[860px]">
            <div className="grid grid-cols-[1fr_120px_1fr_100px_120px_180px] gap-[12px] bg-surface-2 px-s-5 py-[8px] overline">
              <div>name</div>
              <div>status</div>
              <div>model</div>
              <div>gateways</div>
              <div>created</div>
              <div />
            </div>
            {harnesses.map((h) => (
              <div
                key={h.id}
                className="grid grid-cols-[1fr_120px_1fr_100px_120px_180px] gap-[12px] items-center px-s-5 py-[10px] border-t border-border"
              >
                <div>
                  <div className="font-mono text-mono text-text">🤖 {h.name}</div>
                  {h.description && (
                    <div className="text-body-sm text-text-mute mt-[2px]">{h.description}</div>
                  )}
                  {h.status === "error" && h.lastError && (
                    <div className="text-body-sm text-red mt-[2px]">{h.lastError}</div>
                  )}
                </div>
                <div className="font-mono text-mono-sm">
                  <StatusChip status={h.status} />
                </div>
                <div className="font-mono text-mono-sm text-text-dim truncate" title={h.model}>
                  {modelLabel(h.model)}
                </div>
                <div className="font-mono text-mono-sm text-text-dim">
                  {h.gatewayIds.length}
                </div>
                <div className="font-mono text-mono-sm text-text-dim">
                  {relativeTime(h.createdAt)}
                </div>
                <div className="flex justify-end gap-[6px]">
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={h.status !== "ready"}
                    onClick={() => setTestFor(h)}
                  >
                    Test
                  </Button>
                  {h.status !== "creating" && (
                    <Button
                      variant="secondary"
                      size="sm"
                      disabled={redeployingId === h.id}
                      onClick={() => redeploy(h)}
                    >
                      {redeployingId === h.id ? "…" : "Redeploy"}
                    </Button>
                  )}
                  <Button variant="ghost" size="sm" onClick={() => setDeleteFor(h)}>
                    Delete
                  </Button>
                </div>
              </div>
            ))}
          </div>
          </div>
        )}
      </div>
      {createOpen && (
        <CreateModal
          gateways={gateways}
          onClose={() => { setCreateOpen(false); load(); }}
        />
      )}
      {testFor && <TestModal harness={testFor} onClose={() => setTestFor(null)} />}
      {deleteFor && (
        <DeleteModal
          harness={deleteFor}
          onClose={() => { setDeleteFor(null); load(); }}
        />
      )}
    </>
  );
}

function modelLabel(id: string): string {
  return HARNESS_MODELS.find((m) => m.id === id)?.label ?? id;
}

function StatusChip({ status }: { status: Harness["status"] }) {
  const color =
    status === "ready" ? "text-green" :
    status === "error" ? "text-red" :
    "text-amber";
  return <span className={color}>{status}</span>;
}

function CreateModal({ gateways, onClose }: { gateways: Gateway[]; onClose: () => void }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  // Default to the cheapest model in the list — DeepSeek V3.
  const [model, setModel] = useState<HarnessModel>(HARNESS_MODELS[0].id);
  const [systemPrompt, setSystemPrompt] = useState("");
  const [selectedGateways, setSelectedGateways] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  const canSave = name.trim() && model && !busy;

  function toggleGateway(id: string) {
    const next = new Set(selectedGateways);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelectedGateways(next);
  }

  async function save() {
    setBusy(true);
    try {
      await api.createHarness({
        name,
        description,
        model,
        systemPrompt,
        gatewayIds: Array.from(selectedGateways),
      });
      toast.push({ kind: "success", title: "Harness ready", body: `🤖 ${name}` });
      onClose();
    } catch (e) {
      toast.push({ kind: "error", title: "Create failed", body: (e as Error).message });
      setBusy(false);
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title="Create harness"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button variant="accent" disabled={!canSave} onClick={save}>
            {busy ? "Provisioning…" : "Create"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-s-5">
        <div>
          <Label>name</Label>
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="sales-agent"
            maxLength={64}
          />
        </div>
        <div>
          <Label>description</Label>
          <Textarea
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="what does this agent do?"
          />
        </div>
        <div>
          <Label>model</Label>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value as HarnessModel)}
            className="h-[34px] w-full bg-surface border border-border rounded-sm px-[10px] text-body"
          >
            {HARNESS_MODELS.map((m) => (
              <option key={m.id} value={m.id}>{m.label}</option>
            ))}
          </select>
        </div>
        <div>
          <Label>system prompt</Label>
          <Textarea
            rows={5}
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            placeholder="you are a helpful assistant for…"
          />
        </div>
        <div>
          <Label>gateways (mcp tools the harness can call)</Label>
          {gateways.length === 0 ? (
            <div className="font-mono text-mono-sm text-text-mute">
              no gateways yet — <a href="/gateways" className="text-accent">create one</a> first to give this harness tools
            </div>
          ) : (
            <div className="flex flex-col gap-[4px]">
              {gateways.map((g) => {
                const disabled = g.status !== "ready";
                return (
                  <label
                    key={g.id}
                    className={`flex items-center gap-[6px] font-mono text-mono-sm ${disabled ? "text-text-mute" : "text-text-dim"}`}
                  >
                    <input
                      type="checkbox"
                      checked={selectedGateways.has(g.id)}
                      disabled={disabled}
                      onChange={() => toggleGateway(g.id)}
                    />
                    🔌 {g.name}
                    <span className="text-text-mute">· {g.status}</span>
                  </label>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
}

function TestModal({ harness, onClose }: { harness: Harness; onClose: () => void }) {
  const [text, setText] = useState("hello");
  const [busy, setBusy] = useState(false);
  const [output, setOutput] = useState<string | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  async function run() {
    setBusy(true);
    setOutput(null);
    setError(null);
    try {
      const res = await api.testHarness(harness.id, text);
      setOutput(res.output);
      setLatencyMs(res.latencyMs);
    } catch (e) {
      const msg = (e as Error).message;
      setError(msg);
      toast.push({ kind: "error", title: "Test failed", body: msg });
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={`Test "${harness.name}"`}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>Close</Button>
          <Button variant="accent" disabled={!text.trim() || busy} onClick={run}>
            {busy ? "Running…" : "Run"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-s-5">
        <div>
          <Label>sample input</Label>
          <Textarea
            rows={3}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="ask something…"
          />
        </div>
        {output !== null && (
          <div className="bg-surface-2 border border-border rounded-sm p-[10px] font-mono text-mono-sm">
            <div className="text-text-mute mb-[4px]">
              output · {latencyMs}ms
            </div>
            <pre className="whitespace-pre-wrap text-text-dim">{output}</pre>
          </div>
        )}
        {error !== null && (
          <div className="bg-surface-2 border border-border border-l-[3px] border-l-red rounded-sm p-[10px] font-mono text-mono-sm">
            <div className="text-red mb-[4px]">error</div>
            <pre className="whitespace-pre-wrap break-words text-text-dim">{error}</pre>
          </div>
        )}
      </div>
    </Modal>
  );
}

function DeleteModal({ harness, onClose }: { harness: Harness; onClose: () => void }) {
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  async function doDelete() {
    setBusy(true);
    try {
      await api.deleteHarness(harness.id);
      toast.push({ kind: "info", title: "Deleted" });
      onClose();
    } catch (e) {
      toast.push({ kind: "error", title: "Delete failed", body: (e as Error).message });
      setBusy(false);
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={`Delete "${harness.name}"?`}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button variant="danger" disabled={busy} onClick={doDelete}>Delete</Button>
        </>
      }
    >
      <p className="text-body text-text-dim">
        Tears down the AgentCore runtime on AWS. Bots that link this harness must be unlinked first.
      </p>
    </Modal>
  );
}
