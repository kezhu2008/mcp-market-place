"use client";

import { Button } from "@/components/ui/button";
import { logout } from "@/lib/auth";

export function TopBar({ email }: { email?: string }) {
  return (
    <header className="h-[42px] border-b border-border bg-surface flex items-center gap-[12px] px-s-8">
      <div className="font-mono text-mono text-text-dim">mcpp ctl</div>
      <div className="w-px h-[18px] bg-border" />
      <div className="font-mono text-mono-sm text-text-mute">
        <kbd className="bg-surface-2 border border-border rounded-xs px-[5px] py-[1px] text-[10px] mr-[6px]">⌘K</kbd>
        Jump
      </div>
      <div className="ml-auto flex items-center gap-[12px]">
        {email && <span className="font-mono text-mono-sm text-text-mute">{email}</span>}
        <Button variant="ghost" size="sm" onClick={() => logout()}>Sign out</Button>
      </div>
    </header>
  );
}
