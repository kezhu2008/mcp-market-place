import { cn } from "@/lib/utils";
import Link from "next/link";

export interface Breadcrumb { label: string; href?: string }

export function PageHeader({
  title,
  description,
  breadcrumbs,
  right,
  tabs,
  activeTab,
  children,
  className,
}: {
  title: React.ReactNode;
  description?: string;
  breadcrumbs?: Breadcrumb[];
  right?: React.ReactNode;
  tabs?: { id: string; label: string; href: string; badge?: string }[];
  activeTab?: string;
  children?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("px-s-5 md:px-s-8 pt-s-5 md:pt-s-6 pb-0 border-b border-border", className)}>
      {breadcrumbs && breadcrumbs.length > 0 && (
        <div className="font-mono text-mono-sm text-text-mute mb-[6px] flex items-center gap-[4px]">
          {breadcrumbs.map((b, i) => (
            <span key={i} className="flex items-center gap-[4px]">
              {b.href ? (
                <Link href={b.href} className="hover:text-text-dim">{b.label}</Link>
              ) : (
                <span>{b.label}</span>
              )}
              {i < breadcrumbs.length - 1 && <span>/</span>}
            </span>
          ))}
        </div>
      )}
      <div className="flex flex-col sm:flex-row sm:items-start gap-[10px] sm:gap-[12px]">
        <div className="flex-1 min-w-0">
          <h1 className="text-h1 flex flex-wrap items-center gap-[8px] md:gap-[10px]">{title}</h1>
          {description && <p className="text-body-sm text-text-dim mt-[4px]">{description}</p>}
        </div>
        {right && <div className="shrink-0 flex flex-wrap items-center gap-[8px]">{right}</div>}
      </div>
      {tabs && (
        <div className="flex items-center gap-0 mt-s-6 -mb-px overflow-x-auto">
          {tabs.map((t) => {
            const active = t.id === activeTab;
            return (
              <Link
                key={t.id}
                href={t.href}
                className={cn(
                  "px-[14px] py-[10px] text-body border-b-2 transition-colors duration-75",
                  active
                    ? "border-text text-text font-medium"
                    : "border-transparent text-text-dim hover:text-text"
                )}
              >
                {t.label}
                {t.badge && (
                  <span className="ml-[6px] font-mono text-mono-sm text-text-mute">{t.badge}</span>
                )}
              </Link>
            );
          })}
        </div>
      )}
      {children}
    </div>
  );
}
