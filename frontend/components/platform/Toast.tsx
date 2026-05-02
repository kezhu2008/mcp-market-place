"use client";

import { createContext, useCallback, useContext, useState } from "react";
import { cn } from "@/lib/utils";

export type ToastKind = "success" | "info" | "error";
interface ToastItem { id: string; kind: ToastKind; title: string; body?: string }
interface ToastCtx { push: (t: Omit<ToastItem, "id">) => void }

const Ctx = createContext<ToastCtx | null>(null);

export function useToast() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useToast must be inside ToastProvider");
  return ctx;
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const dismiss = useCallback((id: string) => {
    setItems((prev) => prev.filter((x) => x.id !== id));
  }, []);
  const push = useCallback((t: Omit<ToastItem, "id">) => {
    const id = Math.random().toString(36).slice(2);
    setItems((prev) => [...prev, { ...t, id }]);
    // Errors persist until manually dismissed so the user can read/copy them.
    if (t.kind !== "error") {
      setTimeout(() => setItems((prev) => prev.filter((x) => x.id !== id)), 3400);
    }
  }, []);
  return (
    <Ctx.Provider value={{ push }}>
      {children}
      <div className="fixed bottom-[20px] right-[20px] z-50 flex flex-col gap-[8px] max-w-[min(560px,calc(100vw-40px))]">
        {items.map((t) => (
          <div
            key={t.id}
            className={cn(
              "card px-[12px] py-[10px] min-w-[260px] animate-vaSlide border-l-[3px] relative pr-[28px]",
              t.kind === "success" && "border-l-accent",
              t.kind === "info" && "border-l-text",
              t.kind === "error" && "border-l-red"
            )}
          >
            <button
              type="button"
              aria-label="Dismiss"
              onClick={() => dismiss(t.id)}
              className="absolute top-[6px] right-[8px] text-text-mute hover:text-text leading-none text-mono"
            >
              ×
            </button>
            <div className="text-body font-medium">{t.title}</div>
            {t.body && (
              <div className="font-mono text-mono text-text-dim mt-[2px] whitespace-pre-wrap break-words">
                {t.body}
              </div>
            )}
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}
