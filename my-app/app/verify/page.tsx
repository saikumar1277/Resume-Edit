"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { AuthChrome } from "@/components/auth-chrome";
import { Button } from "@/components/ui/button";
import { useAuth, safeNextPath } from "@/lib/auth";

function VerifyInner() {
  const router = useRouter();
  const params = useSearchParams();
  const { verifyEmail } = useAuth();
  const token = params.get("token") || "";
  const [error, setError] = useState(
    token ? "" : "This verification link is missing a token.",
  );
  const next = safeNextPath(params.get("next"));

  useEffect(() => {
    if (!token) {
      return;
    }
    let cancelled = false;
    void verifyEmail(token)
      .then(() => {
        if (!cancelled) router.replace(next);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Could not verify.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [token, next, router, verifyEmail]);

  return (
    <AuthChrome
      kicker="Account"
      title="Verifying"
      description={
        error ? "This link is invalid or expired." : "Signing you in…"
      }
    >
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <p className="mt-4 text-sm text-muted-foreground">
        <Button
          variant="link"
          className="h-auto px-0"
          nativeButton={false}
          render={<Link href="/login" />}
        >
          Back to log in
        </Button>
      </p>
    </AuthChrome>
  );
}

export default function VerifyPage() {
  return (
    <Suspense>
      <VerifyInner />
    </Suspense>
  );
}
