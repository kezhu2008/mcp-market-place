"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Hub } from "aws-amplify/utils";
import { configureAmplify, getIdToken, login } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { LogoMark } from "@/components/platform/icons";

export default function SignInPage() {
  const router = useRouter();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    configureAmplify();

    let alive = true;

    const checkSession = async () => {
      const token = await getIdToken();
      if (!alive) return;
      if (token) {
        router.replace("/dashboard");
      } else {
        setChecking(false);
      }
    };

    // Initial check (handles already-signed-in case + OAuth redirect-back).
    checkSession();

    // Re-check whenever Amplify finishes a sign-in flow (e.g. redirect-back
    // exchange of ?code=... for tokens, which is async after configure).
    const unsubscribe = Hub.listen("auth", ({ payload }) => {
      if (
        payload.event === "signedIn" ||
        payload.event === "signInWithRedirect"
      ) {
        checkSession();
      }
    });

    return () => {
      alive = false;
      unsubscribe();
    };
  }, [router]);

  if (checking) return null;

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
