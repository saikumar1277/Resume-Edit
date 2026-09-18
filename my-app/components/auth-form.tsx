"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AuthChrome } from "@/components/auth-chrome";
import { apiFetch } from "@/lib/api";
import { useAuth, safeNextPath } from "@/lib/auth";

export function AuthForm({ mode }: { mode: "login" | "signup" }) {
  const router = useRouter();
  const params = useSearchParams();
  const { login, signup, user, loading } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [google, setGoogle] = useState(false);
  const next = safeNextPath(params.get("next"));
  const isSignup = mode === "signup";
  const googleError = params.get("error") === "google";

  useEffect(() => {
    if (!loading && user) router.replace(next);
  }, [loading, user, next, router]);

  useEffect(() => {
    let cancelled = false;
    void apiFetch("/auth/providers")
      .then((res) => (res.ok ? res.json() : { google: false }))
      .then((data: { google?: boolean }) => {
        if (!cancelled) setGoogle(Boolean(data.google));
      })
      .catch(() => {
        if (!cancelled) setGoogle(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (isSignup) {
        await signup(email, password);
      } else {
        await login(email, password);
      }
      router.replace(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthChrome
      kicker={isSignup ? "New desk" : "Welcome back"}
      title={isSignup ? "Create an account" : "Log in"}
      description={
        isSignup
          ? "Your resumes stay on this account. The jobs list is shared."
          : "Open the resumes you saved to this account."
      }
    >
      {googleError ? (
        <p className="mb-3 text-sm text-destructive">
          Google sign-in did not complete. Try again, or use email.
        </p>
      ) : null}
      {google ? (
        <div className="mb-4 grid gap-3">
          <Button
            variant="outline"
            className="w-full"
            nativeButton={false}
            render={
              <a href={`/api/auth/google?next=${encodeURIComponent(next)}`} />
            }
          >
            Continue with Google
          </Button>
          <p className="text-center text-xs tracking-wide text-muted-foreground uppercase">
            or email
          </p>
        </div>
      ) : null}
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
        <div className="grid gap-1.5">
          <div className="flex items-center justify-between">
            <Label htmlFor="password">Password</Label>
            {isSignup ? null : (
              <Button
                variant="link"
                className="h-auto px-0 text-xs"
                nativeButton={false}
                render={<Link href="/forgot" />}
              >
                Forgot password?
              </Button>
            )}
          </div>
          <Input
            id="password"
            type="password"
            autoComplete={isSignup ? "new-password" : "current-password"}
            required
            minLength={8}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </div>
        {error ? <p className="text-sm text-destructive">{error}</p> : null}
        <Button type="submit" disabled={busy}>
          {busy
            ? isSignup
              ? "Creating…"
              : "Signing in…"
            : isSignup
              ? "Sign up"
              : "Log in"}
        </Button>
      </form>
      <p className="mt-4 text-sm text-muted-foreground">
        {isSignup ? "Already have an account?" : "Need an account?"}{" "}
        <Button
          variant="link"
          className="h-auto px-0"
          nativeButton={false}
          render={
            <Link
              href={
                isSignup
                  ? `/login?next=${encodeURIComponent(next)}`
                  : `/signup?next=${encodeURIComponent(next)}`
              }
            />
          }
        >
          {isSignup ? "Log in" : "Sign up"}
        </Button>
      </p>
    </AuthChrome>
  );
}
