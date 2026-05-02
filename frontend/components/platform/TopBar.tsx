"use client";

import { Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import { logout } from "@/lib/auth";

export function TopBar({ email, onMenu }: { email?: string; onMenu?: () => void }) {
  return (
    <header className="h-[42px] border-b border-border bg-surface flex items-center gap-[10px] md:gap-[12px] px-s-5 md:px-s-8">
      {onMenu && (
        <button
          type="button"
          aria-label="Open menu"
          onClick={onMenu}
          className="md:hidden -ml-[6px] p-[6px] rounded-sm text-text-dim hover:bg-surface-2"
        >
          <Menu size={16} />
        </button>
      )}
      <div className="font-mono text-mono text-text-dim">mcpp ctl</div>
      <div className="hidden sm:block w-px h-[18px] bg-border" />
      <div className="hidden md:block font-mono text-mono-sm text-text-mute">
        <kbd className="bg-surface-2 border border-border rounded-xs px-[5px] py-[1px] text-[10px] mr-[6px]">⌘K</kbd>
        Jump
      </div>
      <div className="ml-auto flex items-center gap-[12px]">
        {email && <span className="hidden md:inline font-mono text-mono-sm text-text-mute">{email}</span>}
        <Button variant="ghost" size="sm" onClick={() => logout()}>Sign out</Button>
      </div>
    </header>
  );
}
