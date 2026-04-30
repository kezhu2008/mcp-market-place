"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Bot,
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
  { href: "/gateways", label: "Gateways", icon: Plug },
  { href: "/tools", label: "Tools", icon: Wrench, soon: true },
  { href: "/mcp-servers", label: "MCP Servers", icon: Server, soon: true },
  { href: "/models", label: "Models", icon: Boxes, soon: true },
  { href: "/secrets", label: "Secrets", icon: KeyRound },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside
      className="w-[232px] shrink-0 border-r border-border bg-surface flex flex-col"
      style={{ height: "100dvh" }}
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
  );
}
