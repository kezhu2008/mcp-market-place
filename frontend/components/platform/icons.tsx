export function TelegramMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} aria-hidden>
      <path d="M9.417 15.181l-.397 5.584c.568 0 .814-.244 1.109-.537l2.663-2.545 5.518 4.041c1.012.556 1.725.264 1.998-.931l3.622-16.972.001-.001c.321-1.491-.539-2.073-1.524-1.706L2.229 9.28c-1.458.566-1.436 1.378-.249 1.746l5.19 1.62 12.055-7.593c.567-.378 1.084-.168.66.21l-9.468 8.918z" />
    </svg>
  );
}

export function LogoMark({ className }: { className?: string }) {
  return (
    <span className={`text-accent ${className ?? ""}`} aria-hidden>◆</span>
  );
}

export function EmptyState({ title, sub }: { title: string; sub?: string }) {
  return (
    <div className="card py-[48px] px-[20px] flex flex-col items-center justify-center gap-[10px]">
      <svg width="88" height="64" viewBox="0 0 88 64" fill="none" aria-hidden>
        <defs>
          <pattern id="dots" width="6" height="6" patternUnits="userSpaceOnUse">
            <circle cx="1" cy="1" r="1" fill="var(--border-strong)" />
          </pattern>
        </defs>
        <rect width="88" height="64" fill="url(#dots)" opacity="0.5" />
        <rect x="14" y="16" width="36" height="20" fill="var(--surface)" stroke="var(--border-strong)" strokeWidth="1" rx="3" />
        <rect x="44" y="28" width="30" height="20" fill="var(--surface)" stroke="var(--border-strong)" strokeWidth="1" rx="3" />
      </svg>
      <div className="font-mono text-mono text-text-mute">{title}</div>
      {sub && <div className="font-mono text-mono-sm text-text-mute">{sub}</div>}
    </div>
  );
}
