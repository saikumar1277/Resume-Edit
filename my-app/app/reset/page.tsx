"use client";

import { Suspense, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { AuthChrome } from "@/components/auth-chrome";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth, safeNextPath } from "@/lib/auth";

function ResetInner() {
  const router = useRouter();
  const params = useSearchParams();
  const { resetPassword } = useAuth();
  const token = params.get("token") || "";
  const next = safeNextPath(params.get("next"));
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(
    token ? "" : "This reset link is missing a token.",
  );

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      await resetPassword(token, password);
      router.replace(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not reset password.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthChrome
      kicker="Account"
      title="Set a new password"
      description="Choose a password at least 8 characters long."
    >
      <form className="grid gap-3" onSubmit={onSubmit}>
        <div className="grid gap-1.5">
          <Label htmlFor="password">New password</Label>
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            disabled={!token}
          />
        </div>
        {error ? <p className="text-sm text-destructive">{error}</p> : null}
        <Button type="submit" disabled={busy || !token}>
          {busy ? "Saving…" : "Update password"}
        </Button>
        <Button
          variant="link"
          className="h-auto px-0"
          nativeButton={false}
          render={<Link href="/login" />}
        >
          Back to log in
        </Button>
      </form>
    </AuthChrome>
  );
}

export default function ResetPage() {
  return (
    <Suspense>
      <ResetInner />
    </Suspense>
  );
}
