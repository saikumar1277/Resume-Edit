"use client";

import Link from "next/link";
import { Reveal } from "@/components/marketing/motion";

export function SiteFooter() {
  return (
    <footer className="border-t border-[#d9cfc0] px-6 py-10">
      <Reveal>
        <div className="mx-auto flex max-w-6xl flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="font-serif text-2xl text-[#1c1917]">Memic</p>
            <p className="mt-2 max-w-sm text-sm leading-relaxed text-[#7c6a58]">
              A resume editor that stays on the paper, and a jobs list that
              knows when to stop.
            </p>
          </div>
          <nav
            className="flex flex-wrap gap-x-5 gap-y-2 text-sm text-[#57534e]"
            aria-label="Footer"
          >
            <Link href="/" className="hover:text-[#1c1917]">
              Home
            </Link>
            <Link href="/login" className="hover:text-[#1c1917]">
              Log in
            </Link>
            <Link href="/signup" className="hover:text-[#1c1917]">
              Sign up
            </Link>
            <Link href="/resumes" className="hover:text-[#1c1917]">
              Resumes
            </Link>
            <Link href="/jobs" className="hover:text-[#1c1917]">
              Jobs
            </Link>
            <a href="#faq" className="hover:text-[#1c1917]">
              FAQ
            </a>
          </nav>
        </div>
        <p className="mx-auto mt-8 max-w-6xl text-xs text-[#a19382]">
          Letters on this page are illustrative. Resumes stay in your account.
          The jobs list is shared.
        </p>
      </Reveal>
    </footer>
  );
}
