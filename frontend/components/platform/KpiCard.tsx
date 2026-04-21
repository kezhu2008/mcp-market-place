import { cn } from "@/lib/utils";

export function KpiCard({
  label,
  value,
  sub,
  accentBar,
  className,
}: {
  label: string;
  value: string | number;
  sub?: string;
  accentBar?: boolean;
  className?: string;
}) {
  return (
    <div className={cn("card relative p-[14px]", className)}>
      {accentBar && (
        <span className="absolute left-0 top-0 bottom-0 w-[2px] bg-accent rounded-l-md" />
      )}
      <div className="overline">{label}</div>
      <div className="text-kpi mt-[4px] text-text">{value}</div>
      {sub && <div className="font-mono text-mono-sm text-text-dim mt-[2px]">{sub}</div>}
    </div>
  );
}
