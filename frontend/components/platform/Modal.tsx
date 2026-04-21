"use client";

import { useEffect } from "react";
import { cn } from "@/lib/utils";

export function Modal({
  open,
  onClose,
  title,
  children,
  footer,
  width = 520,
}: {
  open: boolean;
  onClose: () => void;
  title: React.ReactNode;
  children: React.ReactNode;
  footer?: React.ReactNode;
  width?: number;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[rgba(0,0,0,0.35)] animate-vaFade">
      <div
        className={cn("bg-surface border border-border rounded-lg shadow-lg animate-vaPop")}
        style={{ width, maxWidth: "calc(100vw - 40px)" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-s-7 py-[14px] border-b border-border flex items-center gap-[10px]">
          <h2 className="text-h2 flex-1">{title}</h2>
          <button
            onClick={onClose}
            className="text-text-mute hover:text-text text-[18px] leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>
        <div className="p-s-7">{children}</div>
        {footer && (
          <div className="px-s-7 py-[14px] border-t border-border flex items-center justify-end gap-[8px]">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
