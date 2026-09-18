"use client";

import Link from "next/link";
import { AppShell } from "@/components/app-shell";
import { RequireAuth } from "@/components/require-auth";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function ResumesPage() {
  return (
    <RequireAuth>
    <AppShell
      active="resumes"
      status="Upload or search a saved resume"
      menuDefaultOpen
    >
      <main className="flex flex-1 items-start p-8">
        <Card className="max-w-md animate-in fade-in slide-in-from-bottom-2 duration-300 ring-border">
          <CardHeader>
            <p className="text-xs tracking-wide text-muted-foreground uppercase">
              Your files
            </p>
            <CardTitle className="font-serif text-2xl tracking-tight">
              Resume editor
            </CardTitle>
            <CardDescription>
              Open the menu to upload a PDF or search a note you saved when
              downloading. Resumes on this page belong to your account. Browse{" "}
              <Button
                variant="link"
                className="h-auto px-0"
                nativeButton={false}
                render={<Link href="/jobs" />}
              >
                open roles
              </Button>{" "}
              when you are ready to apply.
            </CardDescription>
          </CardHeader>
        </Card>
      </main>
    </AppShell>
    </RequireAuth>
  );
}
