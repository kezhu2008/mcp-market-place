"use client";

import { useState } from "react";
import { AuthGate } from "@/components/platform/AuthGate";
import { Sidebar } from "@/components/platform/Sidebar";
import { TopBar } from "@/components/platform/TopBar";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <AuthGate>
      <div className="flex min-h-dvh">
        <Sidebar open={drawerOpen} onClose={() => setDrawerOpen(false)} />
        <div className="flex-1 flex flex-col min-w-0">
          <TopBar onMenu={() => setDrawerOpen(true)} />
          <div className="flex-1 overflow-y-auto">{children}</div>
        </div>
      </div>
    </AuthGate>
  );
}
