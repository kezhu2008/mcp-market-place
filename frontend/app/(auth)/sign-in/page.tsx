"use client";

import { useEffect } from "react";
import { login } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { LogoMark } from "@/components/platform/icons";

export default function SignInPage() {
  useEffect(() => {
    // no-op — user triggers via button
  }, []);

  return (
    <main className="min-h-dvh flex items-center justify-center bg-bg">
      <div className="card p-s-8 w-[360px]">
        <div className="flex items-center gap-[10px] mb-s-6">
          <LogoMark className="text-[24px]" />
          <div className="text-h1">MCP Platform</div>
        </div>
        <p className="text-body-sm text-text-dim mb-s-7">
          Sign in with your Cognito account to continue.
        </p>
        <Button variant="accent" size="lg" className="w-full" onClick={() => login()}>
          Sign in
        </Button>
      </div>
    </main>
  );
}
