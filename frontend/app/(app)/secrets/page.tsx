"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/platform/PageHeader";
import { Button } from "@/components/ui/button";
import { Input, Label, Textarea } from "@/components/ui/input";
import { Modal } from "@/components/platform/Modal";
import { EmptyState } from "@/components/platform/icons";
import { api } from "@/lib/api";
import type { Secret } from "@/lib/types";
import { relativeTime } from "@/lib/utils";
import { useToast } from "@/components/platform/Toast";

export default function SecretsPage() {
  const [secrets, setSecrets] = useState<Secret[]>([]);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [rotateFor, setRotateFor] = useState<Secret | null>(null);

  async function load() {
    setLoading(true);
    try { setSecrets(await api.listSecrets()); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);

  return (
    <>
      <PageHeader
        title="Secrets"
        description="Stored in AWS Secrets Manager. Values never displayed after save."
        right={<Button variant="accent" onClick={() => setCreateOpen(true)}>Create secret</Button>}
      />
      <div className="p-s-5 md:p-s-8">
        {loading ? (
          <EmptyState title="loading…" />
        ) : secrets.length === 0 ? (
          <EmptyState title="no secrets yet" sub="create one to deploy a bot" />
        ) : (
          <div className="overflow-x-auto">
          <div className="card overflow-hidden min-w-[640px]">
            <div className="grid grid-cols-[1fr_160px_160px_120px] gap-[12px] bg-surface-2 px-s-5 py-[8px] overline">
              <div>name</div>
              <div>last used</div>
              <div>last rotated</div>
              <div />
            </div>
            {secrets.map((s) => {
              const stale = Date.now() - Date.parse(s.lastRotatedAt) > 60 * 86400 * 1000;
              return (
                <div
                  key={s.id}
                  className="grid grid-cols-[1fr_160px_160px_120px] gap-[12px] items-center px-s-5 py-[10px] border-t border-border"
                >
                  <div>
                    <div className="font-mono text-mono text-text">🔒 {s.name}</div>
                    {s.description && (
                      <div className="text-body-sm text-text-mute mt-[2px]">{s.description}</div>
                    )}
                  </div>
                  <div className="font-mono text-mono-sm text-text-dim">{relativeTime(s.lastUsedAt)}</div>
                  <div className="font-mono text-mono-sm text-text-dim">
                    {stale && <span className="text-amber mr-[4px]">⚠</span>}
                    {relativeTime(s.lastRotatedAt)}
                  </div>
                  <div className="flex justify-end">
                    <Button variant="secondary" size="sm" onClick={() => setRotateFor(s)}>Rotate</Button>
                  </div>
                </div>
              );
            })}
          </div>
          </div>
        )}
      </div>
      {createOpen && <CreateModal onClose={() => { setCreateOpen(false); load(); }} />}
      {rotateFor && <RotateModal secret={rotateFor} onClose={() => { setRotateFor(null); load(); }} />}
    </>
  );
}

function CreateModal({ onClose }: { onClose: () => void }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  async function save() {
    setBusy(true);
    try {
      await api.createSecret({ name, description, value });
      toast.push({ kind: "success", title: "Created", body: `🔒 ${name}` });
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
      title="Create secret"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button variant="accent" disabled={!name || !value || busy} onClick={save}>
            {busy ? "Saving…" : "Create"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-s-5">
        <div>
          <Label>name</Label>
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="telegram-sales-bot" />
        </div>
        <div>
          <Label>description</Label>
          <Textarea rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>
        <div>
          <Label>value</Label>
          <Input mono type="password" value={value} onChange={(e) => setValue(e.target.value)} placeholder="paste token" />
          <div className="font-mono text-mono-sm text-text-mute mt-[4px]">
            You&apos;ll never see this again after save.
          </div>
        </div>
      </div>
    </Modal>
  );
}

function RotateModal({ secret, onClose }: { secret: Secret; onClose: () => void }) {
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  async function save() {
    setBusy(true);
    try {
      await api.rotateSecret(secret.id, value);
      toast.push({ kind: "success", title: "Rotated", body: `🔒 ${secret.name}` });
      onClose();
    } catch (e) {
      toast.push({ kind: "error", title: "Rotate failed", body: (e as Error).message });
      setBusy(false);
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={`Rotate "${secret.name}"`}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button variant="accent" disabled={!value || busy} onClick={save}>
            {busy ? "Rotating…" : "Rotate"}
          </Button>
        </>
      }
    >
      <p className="text-body text-text-dim mb-s-5">
        ⚠ Regenerating invalidates current webhook and requires redeploy.
      </p>
      <Label>new value</Label>
      <Input mono type="password" value={value} onChange={(e) => setValue(e.target.value)} />
    </Modal>
  );
}
