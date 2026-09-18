"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { MenuIcon, XIcon } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { paperEase, useReduceMotionSafe } from "@/components/marketing/motion";
import { useAuth } from "@/lib/auth";

const links = [
  { href: "#reviews", label: "Letters" },
  { href: "#how", label: "How it works" },
  { href: "#faq", label: "FAQ" },
];

export function SiteHeader() {
  const [open, setOpen] = useState(false);
  const reduce = useReduceMotionSafe();
  const { user, loading, logout } = useAuth();
  const router = useRouter();

  return (
    <header className="sticky top-0 z-30 border-b border-[#d9cfc0]/80 bg-[#f6f1e8]/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center gap-3 px-6 py-3">
        <Link
          href="/"
          className="font-serif text-xl tracking-tight text-[#1c1917]"
        >
          Memic
        </Link>

        <nav
          className="ml-6 hidden items-center gap-5 text-sm text-[#57534e] md:flex"
          aria-label="Marketing"
        >
          {links.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="underline-offset-4 hover:text-[#1c1917] hover:underline"
            >
              {link.label}
            </a>
          ))}
        </nav>

        <div className="ml-auto hidden items-center gap-2 md:flex">
          <Link
            href="/jobs"
            className="rounded-lg px-2.5 py-1.5 text-sm text-[#1c1917] hover:bg-white/40"
          >
            Browse jobs
          </Link>
          {loading ? null : user ? (
            <>
              <Link
                href="/resumes"
                className="rounded-lg bg-[#1c1917] px-2.5 py-1.5 text-sm text-[#f6f1e8] hover:bg-[#1c1917]/85"
              >
                Your resumes
              </Link>
              <button
                type="button"
                className="rounded-lg px-2.5 py-1.5 text-sm text-[#1c1917] hover:bg-white/40"
                onClick={() => {
                  void logout().then(() => router.push("/"));
                }}
              >
                Log out
              </button>
            </>
          ) : (
            <>
              <Link
                href="/login"
                className="rounded-lg px-2.5 py-1.5 text-sm text-[#1c1917] hover:bg-white/40"
              >
                Log in
              </Link>
              <Link
                href="/signup"
                className="rounded-lg bg-[#1c1917] px-2.5 py-1.5 text-sm text-[#f6f1e8] hover:bg-[#1c1917]/85"
              >
                Sign up
              </Link>
            </>
          )}
        </div>

        <button
          type="button"
          className="ml-auto inline-flex size-8 items-center justify-center rounded-lg md:hidden"
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          onClick={() => setOpen((value) => !value)}
        >
          {open ? (
            <XIcon className="size-4" />
          ) : (
            <MenuIcon className="size-4" />
          )}
        </button>
      </div>

      <AnimatePresence>
        {open ? (
          <motion.div
            className="overflow-hidden border-t border-[#d9cfc0]/80 md:hidden"
            initial={reduce ? false : { height: 0 }}
            animate={{ height: "auto" }}
            exit={reduce ? undefined : { height: 0 }}
            transition={{ duration: 0.28, ease: paperEase }}
          >
            <nav
              className="flex flex-col gap-3 px-6 py-3 text-sm"
              aria-label="Mobile"
            >
              {links.map((link) => (
                <a
                  key={link.href}
                  href={link.href}
                  className="text-[#57534e]"
                  onClick={() => setOpen(false)}
                >
                  {link.label}
                </a>
              ))}
              <Link href="/jobs" onClick={() => setOpen(false)}>
                Browse jobs
              </Link>
              {user ? (
                <>
                  <Link href="/resumes" onClick={() => setOpen(false)}>
                    Your resumes
                  </Link>
                  <button
                    type="button"
                    className="text-left"
                    onClick={() => {
                      setOpen(false);
                      void logout().then(() => router.push("/"));
                    }}
                  >
                    Log out
                  </button>
                </>
              ) : (
                <>
                  <Link href="/login" onClick={() => setOpen(false)}>
                    Log in
                  </Link>
                  <Link href="/signup" onClick={() => setOpen(false)}>
                    Sign up
                  </Link>
                </>
              )}
            </nav>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </header>
  );
}
