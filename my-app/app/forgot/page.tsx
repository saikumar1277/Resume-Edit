"use client";

import { Suspense, useState, type FormEvent } from "react";
import Link from "next/link";
import { AuthChrome } from "@/components/auth-chrome";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/lib/auth";

function ForgotInner() {
  const { forgotPassword } = useAuth();
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      await forgotPassword(email);
      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not send reset email.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthChrome
      kicker="Account"
      title="Forgot password"
      description={
        sent
          ? "If that email has a password, a reset link is on its way."
          : "We will email a reset link if this account uses a password."
      }
    >
      {sent ? (
        <Button
          variant="link"
          className="h-auto px-0"
          nativeButton={false}
          render={<Link href="/login" />}
        >
          Back to log in
        </Button>
      ) : (
        <form className="grid gap-3" onSubmit={onSubmit}>
          <div className="grid gap-1.5">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          <Button type="submit" disabled={busy}>
            {busy ? "Sending…" : "Send reset link"}
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
      )}
    </AuthChrome>
  );
}

export default function ForgotPage() {
  return (
    <Suspense>
      <ForgotInner />
    </Suspense>
  );
}
