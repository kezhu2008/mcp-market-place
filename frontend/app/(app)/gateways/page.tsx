"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/platform/PageHeader";
import { Button } from "@/components/ui/button";
import { Input, Label, Textarea } from "@/components/ui/input";
import { Modal } from "@/components/platform/Modal";
import { EmptyState } from "@/components/platform/icons";
import { api } from "@/lib/api";
import type { Gateway, GatewayTool } from "@/lib/types";
import { relativeTime } from "@/lib/utils";
import { useToast } from "@/components/platform/Toast";

export default function GatewaysPage() {
  const [gateways, setGateways] = useState<Gateway[]>([]);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [testFor, setTestFor] = useState<Gateway | null>(null);
  const [deleteFor, setDeleteFor] = useState<Gateway | null>(null);

  async function load() {
    setLoading(true);
    try { setGateways(await api.listGateways()); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);

  return (
    <>
      <PageHeader
        title="Gateways"
        description="AgentCore gateways turn an OpenAPI spec + token into MCP tools your harness can call."
        right={<Button variant="accent" onClick={() => setCreateOpen(true)}>Create gateway</Button>}
      />
      <div className="p-s-8">
        {loading ? (
          <EmptyState title="loading…" />
        ) : gateways.length === 0 ? (
          <EmptyState title="no gateways yet" sub="create one to give a harness tool access" />
        ) : (
          <div className="card overflow-hidden">
            <div className="grid grid-cols-[1fr_120px_1fr_120px_120px] gap-[12px] bg-surface-2 px-s-5 py-[8px] overline">
              <div>name</div>
              <div>status</div>
              <div>url</div>
              <div>created</div>
              <div />
            </div>
            {gateways.map((g) => (
              <div
                key={g.id}
                className="grid grid-cols-[1fr_120px_1fr_120px_120px] gap-[12px] items-center px-s-5 py-[10px] border-t border-border"
              >
                <div>
                  <div className="font-mono text-mono text-text">🔌 {g.name}</div>
                  {g.description && (
                    <div className="text-body-sm text-text-mute mt-[2px]">{g.description}</div>
                  )}
                  {g.status === "error" && g.lastError && (
                    <div className="text-body-sm text-red mt-[2px]">{g.lastError}</div>
                  )}
                </div>
                <div className="font-mono text-mono-sm">
                  <StatusChip status={g.status} />
                </div>
                <div className="font-mono text-mono-sm text-text-dim truncate" title={g.gatewayUrl ?? ""}>
                  {g.gatewayUrl ?? "—"}
                </div>
                <div className="font-mono text-mono-sm text-text-dim">{relativeTime(g.createdAt)}</div>
                <div className="flex justify-end gap-[6px]">
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={g.status !== "ready"}
                    onClick={() => setTestFor(g)}
                  >
                    Test
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => setDeleteFor(g)}>Delete</Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      {createOpen && <CreateModal onClose={() => { setCreateOpen(false); load(); }} />}
      {testFor && <TestModal gateway={testFor} onClose={() => setTestFor(null)} />}
      {deleteFor && <DeleteModal gateway={deleteFor} onClose={() => { setDeleteFor(null); load(); }} />}
    </>
  );
}

function TestModal({ gateway, onClose }: { gateway: Gateway; onClose: () => void }) {
  const [busy, setBusy] = useState(false);
  const [tools, setTools] = useState<GatewayTool[] | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const toast = useToast();

  async function run() {
    setBusy(true);
    setTools(null);
    try {
      const res = await api.testGateway(gateway.id);
      setTools(res.tools);
      setLatencyMs(res.latencyMs);
    } catch (e) {
      toast.push({ kind: "error", title: "Test failed", body: (e as Error).message });
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={`Test "${gateway.name}"`}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>Close</Button>
          <Button variant="accent" disabled={busy} onClick={run}>
            {busy ? "Probing…" : "List tools"}
          </Button>
        </>
      }
    >
      <p className="text-body text-text-dim mb-s-5">
        Sends a SigV4-signed <code className="code">tools/list</code> JSON-RPC to the gateway URL. Confirms reachability, IAM auth, and that the OpenAPI spec translated into MCP tools.
      </p>
      {tools !== null && (
        <div className="bg-surface-2 border border-border rounded-sm p-[10px] font-mono text-mono-sm">
          <div className="text-text-mute mb-[6px]">
            {tools.length} tool(s) · {latencyMs}ms
          </div>
          {tools.length === 0 ? (
            <div className="text-text-mute">no tools returned</div>
          ) : (
            <div className="flex flex-col gap-[4px]">
              {tools.map((t) => (
                <div key={t.name} className="text-text-dim">
                  <span className="text-text">{t.name}</span>
                  {t.description && <span className="text-text-mute"> — {t.description}</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </Modal>
  );
}

function StatusChip({ status }: { status: Gateway["status"] }) {
  const color =
    status === "ready" ? "text-green" :
    status === "error" ? "text-red" :
    "text-amber";
  return <span className={color}>{status}</span>;
}

function CreateModal({ onClose }: { onClose: () => void }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [openapiSpec, setOpenapiSpec] = useState("");
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  const canSave = name.trim() && openapiSpec.trim() && token && !busy;

  async function save() {
    setBusy(true);
    try {
      await api.createGateway({ name, description, openapiSpec, token });
      toast.push({ kind: "success", title: "Gateway created", body: `🔌 ${name}` });
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
      title="Create gateway"
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
            placeholder="stripe-api"
            maxLength={64}
          />
        </div>
        <div>
          <Label>description</Label>
          <Textarea
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="what does this gateway expose?"
          />
        </div>
        <div>
          <Label>openapi spec (json or yaml)</Label>
          <Textarea
            mono
            rows={10}
            value={openapiSpec}
            onChange={(e) => setOpenapiSpec(e.target.value)}
            placeholder='{"openapi": "3.0.0", "info": {"title": "..."}, ...}'
          />
        </div>
        <div>
          <Label>upstream API token</Label>
          <Input
            mono
            type="password"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="bearer / api key for the upstream service"
          />
          <div className="font-mono text-mono-sm text-text-mute mt-[4px]">
            stored in Secrets Manager and bound to the gateway target&rsquo;s credential provider; you won&rsquo;t see it again.
          </div>
        </div>
      </div>
    </Modal>
  );
}

function DeleteModal({ gateway, onClose }: { gateway: Gateway; onClose: () => void }) {
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  async function doDelete() {
    setBusy(true);
    try {
      await api.deleteGateway(gateway.id);
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
      title={`Delete "${gateway.name}"?`}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button variant="danger" disabled={busy} onClick={doDelete}>Delete</Button>
        </>
      }
    >
      <p className="text-body text-text-dim">
        Deletes the gateway, target, and credential provider on AWS. Tears down
        the stored API token. Bots that link this gateway must be unlinked first.
      </p>
    </Modal>
  );
}
