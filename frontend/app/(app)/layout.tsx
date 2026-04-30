import { AuthGate } from "@/components/platform/AuthGate";
import { Sidebar } from "@/components/platform/Sidebar";
import { TopBar } from "@/components/platform/TopBar";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGate>
      <div className="flex min-h-dvh">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <TopBar />
          <div className="flex-1 overflow-y-auto">{children}</div>
        </div>
      </div>
    </AuthGate>
  );
}
