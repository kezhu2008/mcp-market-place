import { cn } from "@/lib/utils";
import type { BotStatus } from "@/lib/types";

const STYLES: Record<BotStatus, { bg: string; text: string; dot: string; pulse?: boolean }> = {
  deployed: { bg: "bg-[#10b98118]", text: "text-accent", dot: "bg-accent", pulse: true },
  deploying: { bg: "bg-[#f59e0b18]", text: "text-amber", dot: "bg-amber" },
  draft: { bg: "bg-surface-3", text: "text-text-dim", dot: "bg-stone-500" },
  disabled: { bg: "bg-surface-3", text: "text-text-dim", dot: "bg-stone-500" },
  error: { bg: "bg-[#ef444418]", text: "text-red", dot: "bg-red" },
};

export function StatusPill({
  status,
  className,
  livePulse,
}: {
  status: BotStatus;
  className?: string;
  livePulse?: boolean;
}) {
  const s = STYLES[status];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-[3px] rounded-sm py-[3px] px-[7px] font-mono text-mono-sm font-medium",
        s.bg,
        s.text,
        className
      )}
    >
      <span
        className={cn(
          "w-[6px] h-[6px] rounded-full",
          s.dot,
          livePulse && s.pulse && "animate-vaPulse"
        )}
      />
      <span>{status}</span>
    </span>
  );
}
