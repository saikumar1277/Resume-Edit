"use client";

import { Suspense } from "react";
import { AppShell } from "@/components/app-shell";
import { Skeleton } from "@/components/ui/skeleton";
import JobsBoard from "./JobsBoard";

export default function JobsPage() {
  return (
    <AppShell active="jobs" status="Browse open roles">
      <main className="min-h-0 flex-1 overflow-auto">
        <Suspense
          fallback={
            <div className="mx-auto flex max-w-6xl flex-col gap-3 p-6">
              <Skeleton className="h-10 w-48" />
              <Skeleton className="h-24 w-full" />
              <Skeleton className="h-24 w-full" />
            </div>
          }
        >
          <JobsBoard />
        </Suspense>
      </main>
    </AppShell>
  );
}
