"use client";

import { useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Bot,
  Cpu,
  Wrench,
  Server,
  Boxes,
  KeyRound,
  Plug,
  Settings,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { LogoMark } from "./icons";

interface Item {
  href: string;
  label: string;
  icon: LucideIcon;
  soon?: boolean;
}

const ITEMS: Item[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/bots", label: "Bots", icon: Bot },
  { href: "/harnesses", label: "Harnesses", icon: Cpu },
  { href: "/gateways", label: "Gateways", icon: Plug },
  { href: "/tools", label: "Tools", icon: Wrench, soon: true },
  { href: "/mcp-servers", label: "MCP Servers", icon: Server, soon: true },
  { href: "/models", label: "Models", icon: Boxes, soon: true },
  { href: "/secrets", label: "Secrets", icon: KeyRound },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar({ open = false, onClose }: { open?: boolean; onClose?: () => void }) {
  const pathname = usePathname();

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose?.();
    };
    window.addEventListener("keydown", onKey);
    document.documentElement.classList.add("overflow-hidden");
    return () => {
      window.removeEventListener("keydown", onKey);
      document.documentElement.classList.remove("overflow-hidden");
    };
  }, [open, onClose]);

  return (
    <>
      <div
        className={cn(
          "fixed inset-0 z-30 bg-black/40 md:hidden",
          open ? "block" : "hidden"
        )}
        onClick={onClose}
        aria-hidden="true"
      />
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 w-[232px] border-r border-border bg-surface flex flex-col transition-transform duration-200 ease-out",
          "md:static md:translate-x-0 md:shrink-0 md:h-dvh",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="h-[42px] px-[14px] border-b border-border flex items-center gap-[10px]">
          <LogoMark className="text-[20px]" />
          <div className="font-mono text-mono text-text-dim">acme/prod</div>
        </div>
        <nav className="flex-1 p-[10px] flex flex-col gap-[2px]">
          {ITEMS.map((item) => {
            const active =
              item.href === "/dashboard"
                ? pathname === "/" || pathname === "/dashboard"
                : pathname.startsWith(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={onClose}
                className={cn(
                  "flex items-center gap-[10px] px-[10px] h-[32px] rounded-sm text-body transition-colors duration-75",
                  active
                    ? "bg-accent-soft text-accent border border-[#10b98122]"
                    : "text-text-dim hover:bg-surface-2 hover:text-text border border-transparent"
                )}
              >
                <Icon size={14} className="shrink-0" />
                <span className="flex-1 truncate">{item.label}</span>
                {item.soon && (
                  <span className="font-mono text-[10px] text-text-mute">soon</span>
                )}
              </Link>
            );
          })}
        </nav>
        <div className="p-[12px] border-t border-border font-mono text-mono-sm text-text-mute flex items-center gap-[6px]">
          <span className="w-[6px] h-[6px] rounded-full bg-accent animate-vaPulse" />
          <span>live · ap-southeast-2</span>
        </div>
      </aside>
    </>
  );
}
