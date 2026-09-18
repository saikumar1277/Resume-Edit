"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export function AuthChrome({
  kicker,
  title,
  description,
  children,
}: {
  kicker: string;
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <div className="flex min-h-full flex-col bg-background text-foreground">
      <header className="border-b border-border/80 px-6 py-3">
        <div className="mx-auto flex max-w-md items-center justify-between">
          <Link href="/" className="font-serif text-xl tracking-tight">
            Page one
          </Link>
          <Link
            href="/jobs"
            className="text-sm text-muted-foreground hover:text-foreground"
          >
            Browse jobs
          </Link>
        </div>
      </header>
      <main className="flex flex-1 items-start justify-center p-6 py-16">
        <Card className="w-full max-w-md ring-border">
          <CardHeader>
            <p className="text-xs tracking-wide text-muted-foreground uppercase">
              {kicker}
            </p>
            <CardTitle className="font-serif text-3xl tracking-tight">
              {title}
            </CardTitle>
            <CardDescription>{description}</CardDescription>
          </CardHeader>
          <CardContent>{children}</CardContent>
        </Card>
      </main>
    </div>
  );
}
