"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getIdToken } from "@/lib/auth";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let alive = true;
    (async () => {
      const token = await getIdToken();
      if (!alive) return;
      if (!token) {
        router.replace("/sign-in");
        return;
      }
      setReady(true);
    })();
    return () => {
      alive = false;
    };
  }, [router]);

  if (!ready) return null;
  return <>{children}</>;
}
