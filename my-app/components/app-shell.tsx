"use client";

import { type ReactNode, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { MoreVerticalIcon } from "lucide-react";
import { ResumeMenu } from "@/components/resume-menu";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";

export function AppShell({
  children,
  active,
  status,
  tools,
  actions,
  aside,
  fileName,
  currentId,
  menuDefaultOpen = false,
}: {
  children: ReactNode;
  active: "home" | "resumes" | "jobs";
  status?: ReactNode;
  tools?: ReactNode;
  actions?: ReactNode;
  aside?: ReactNode;
  fileName?: string;
  currentId?: string;
  menuDefaultOpen?: boolean;
}) {
  const [menuOpen, setMenuOpen] = useState(menuDefaultOpen);
  const { user, loading, logout } = useAuth();
  const router = useRouter();

  return (
    <div className="app-frame">
      <div className="editor-shell flex min-h-full flex-col">
        <header className="no-print sticky top-0 z-20 border-b border-border/80 bg-background/90 backdrop-blur supports-backdrop-filter:bg-background/80">
          <div className="flex flex-wrap items-center gap-2 px-3 py-2">
            <Button
              variant="ghost"
              size="icon"
              aria-label={menuOpen ? "Close menu" : "Open menu"}
              aria-pressed={menuOpen}
              onClick={() => setMenuOpen((value) => !value)}
            >
              <MoreVerticalIcon />
            </Button>
            <Link
              href="/"
              className="font-serif text-xl tracking-tight text-foreground"
            >
              Page one
            </Link>
            <nav className="flex items-center gap-1" aria-label="App">
              <Button
                size="sm"
                variant={active === "resumes" ? "secondary" : "ghost"}
                nativeButton={false}
                render={<Link href="/resumes" />}
              >
                Resumes
              </Button>
              <Button
                size="sm"
                variant={active === "jobs" ? "secondary" : "ghost"}
                nativeButton={false}
                render={<Link href="/jobs" />}
              >
                Jobs
              </Button>
            </nav>
            {tools}
            {status ? (
              <p className="min-w-16 text-xs text-muted-foreground">{status}</p>
            ) : null}
            <div className="ml-auto flex items-center gap-2">
              {loading ? null : user ? (
                <>
                  <span className="hidden max-w-40 truncate text-xs text-muted-foreground sm:inline">
                    {user.email}
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      void logout().then(() => router.push("/"));
                    }}
                  >
                    Log out
                  </Button>
                </>
              ) : (
                <>
                  <Button
                    variant="ghost"
                    size="sm"
                    nativeButton={false}
                    render={<Link href="/login" />}
                  >
                    Log in
                  </Button>
                  <Button
                    size="sm"
                    nativeButton={false}
                    render={<Link href="/signup" />}
                  >
                    Sign up
                  </Button>
                </>
              )}
              {actions}
            </div>
          </div>
        </header>
        {children}
      </div>
      {aside}
      <ResumeMenu
        open={menuOpen}
        onOpenChange={setMenuOpen}
        fileName={fileName}
        currentId={currentId}
      />
    </div>
  );
}
