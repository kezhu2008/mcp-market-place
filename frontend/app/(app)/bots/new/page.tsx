"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { PageHeader } from "@/components/platform/PageHeader";
import { Button } from "@/components/ui/button";
import { Input, Label, Textarea } from "@/components/ui/input";
import { api } from "@/lib/api";
import type { BotCommand, Secret } from "@/lib/types";
import { useToast } from "@/components/platform/Toast";

export default function NewBotPage() {
  const router = useRouter();
  const toast = useToast();
  const [step, setStep] = useState<1 | 2>(1);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [secretId, setSecretId] = useState("");
  const [commands, setCommands] = useState<BotCommand[]>([{ cmd: "/ping", template: "pong" }]);
  const [secrets, setSecrets] = useState<Secret[]>([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.listSecrets().then(setSecrets).catch(() => setSecrets([]));
  }, []);

  const canNext1 = name.trim().length > 0 && name.length <= 64;
  const canSave = canNext1 && !!secretId && commands.every((c) => c.cmd.startsWith("/") && c.template.trim());

  async function save(deploy: boolean) {
    if (!canSave) return;
    setSaving(true);
    try {
      const bot = await api.createBot({ name, description, secretId, commands });
      if (deploy) await api.deployBot(bot.id);
      toast.push({ kind: "success", title: deploy ? "Deployed" : "Saved as draft", body: bot.name });
      router.push(`/bots/${bot.id}`);
    } catch (e) {
      toast.push({ kind: "error", title: "Save failed", body: (e as Error).message });
      setSaving(false);
    }
  }

  return (
    <>
      <PageHeader
        title="New bot"
        breadcrumbs={[{ label: "bots", href: "/bots" }, { label: "new" }]}
        description="Telegram only in Phase 1."
      />
      <div className="p-s-8 flex gap-s-8 max-w-[1100px]">
        <div className="flex-1">
          <div className="flex items-center gap-[10px] mb-s-7 font-mono text-mono-sm">
            <span className={step === 1 ? "text-accent" : "text-text-mute"}>1 · identity</span>
            <span className="text-text-mute">—</span>
            <span className={step === 2 ? "text-accent" : "text-text-mute"}>2 · telegram config</span>
          </div>
          {step === 1 ? (
            <div className="card p-s-7 flex flex-col gap-s-6">
              <div>
                <Label>name</Label>
                <Input value={name} onChange={(e) => setName(e.target.value)} maxLength={64} placeholder="sales-bot" />
                <div className="font-mono text-mono-sm text-text-mute mt-[4px]">{name.length}/64</div>
              </div>
              <div>
                <Label>description</Label>
                <Textarea rows={3} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="what does this bot do?" />
              </div>
              <div>
                <Label>type</Label>
                <div className="flex gap-[8px]">
                  <div className="border border-accent bg-accent-soft rounded-sm px-[12px] py-[8px] text-body">Telegram</div>
                  <div className="border border-border rounded-sm px-[12px] py-[8px] text-body text-text-mute">Slack · soon</div>
                  <div className="border border-border rounded-sm px-[12px] py-[8px] text-body text-text-mute">Discord · soon</div>
                </div>
              </div>
              <div className="flex justify-end gap-[8px] pt-s-4">
                <Button variant="secondary" onClick={() => router.push("/bots")}>Cancel</Button>
                <Button variant="accent" disabled={!canNext1} onClick={() => setStep(2)}>Next</Button>
              </div>
            </div>
          ) : (
            <div className="card p-s-7 flex flex-col gap-s-6">
              <div>
                <Label>bot token secret</Label>
                {secrets.length === 0 ? (
                  <div className="font-mono text-mono-sm text-text-mute">
                    no secrets yet — <a href="/secrets" className="text-accent">create one</a> first
                  </div>
                ) : (
                  <select
                    value={secretId}
                    onChange={(e) => setSecretId(e.target.value)}
                    className="h-[34px] w-full bg-surface border border-border rounded-sm px-[10px] text-body"
                  >
                    <option value="">choose a secret…</option>
                    {secrets.map((s) => (
                      <option key={s.id} value={s.id}>🔒 {s.name}</option>
                    ))}
                  </select>
                )}
              </div>
              <div>
                <Label>commands</Label>
                <div className="flex flex-col gap-[6px]">
                  {commands.map((c, i) => (
                    <div key={i} className="flex gap-[8px] items-center">
                      <Input
                        mono
                        className="w-[140px]"
                        value={c.cmd}
                        onChange={(e) => {
                          const next = [...commands];
                          next[i] = { ...next[i], cmd: e.target.value };
                          setCommands(next);
                        }}
                      />
                      <Input
                        className="flex-1"
                        value={c.template}
                        onChange={(e) => {
                          const next = [...commands];
                          next[i] = { ...next[i], template: e.target.value };
                          setCommands(next);
                        }}
                      />
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setCommands(commands.filter((_, j) => j !== i))}
                      >
                        remove
                      </Button>
                    </div>
                  ))}
                  <Button variant="secondary" size="sm" onClick={() => setCommands([...commands, { cmd: "/", template: "" }])}>
                    + add command
                  </Button>
                </div>
              </div>
              <div className="flex justify-between gap-[8px] pt-s-4">
                <Button variant="secondary" onClick={() => setStep(1)}>Back</Button>
                <div className="flex gap-[8px]">
                  <Button variant="secondary" disabled={!canSave || saving} onClick={() => save(false)}>
                    Save as draft
                  </Button>
                  <Button variant="accent" disabled={!canSave || saving} onClick={() => save(true)}>
                    {saving ? "Saving…" : "Save & deploy"}
                  </Button>
                </div>
              </div>
            </div>
          )}
        </div>
        <aside className="w-[280px] shrink-0">
          <div className="card p-s-5">
            <div className="overline mb-[8px]">what deploy will do</div>
            <ul className="font-mono text-mono-sm text-text-dim flex flex-col gap-[4px]">
              <li>· register Telegram webhook</li>
              <li>· flip status to deployed</li>
              <li>· start receiving events</li>
            </ul>
          </div>
        </aside>
      </div>
    </>
  );
}
