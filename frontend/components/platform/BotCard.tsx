import Link from "next/link";
import { StatusPill } from "./StatusPill";
import { relativeTime } from "@/lib/utils";
import type { Bot } from "@/lib/types";
import { TelegramMark } from "./icons";

export function BotCard({ bot }: { bot: Bot }) {
  return (
    <Link
      href={`/bots/${bot.id}`}
      className="card p-[12px] hover:-translate-y-[1px] hover:border-border-strong transition-all duration-75 flex flex-col gap-[10px]"
    >
      <div className="flex items-start gap-[10px]">
        <div className="w-[32px] h-[32px] rounded-md bg-surface-2 flex items-center justify-center shrink-0">
          <TelegramMark className="w-[18px] h-[18px]" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-[8px]">
            <div className="text-body font-medium truncate">{bot.name}</div>
            <StatusPill status={bot.status} livePulse={bot.status === "deployed"} className="ml-auto shrink-0" />
          </div>
          <div className="font-mono text-mono-sm text-text-mute mt-[2px] truncate">
            {bot.type} · {bot.id}
          </div>
        </div>
      </div>
      <div className="flex items-center gap-[12px] font-mono text-mono-sm text-text-dim mt-auto">
        <span>↗ {bot.requests24h ?? 0}/24h</span>
        <span>◷ {relativeTime(bot.lastEventAt)}</span>
      </div>
    </Link>
  );
}
