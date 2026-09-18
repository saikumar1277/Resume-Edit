"use client";

import Link from "next/link";
import { motion } from "motion/react";
import { paperEase, useReduceMotionSafe } from "@/components/marketing/motion";

export function ProductSplit() {
  const reduce = useReduceMotionSafe();

  return (
    <section className="mx-auto grid max-w-6xl gap-6 px-6 py-20 md:grid-cols-2">
      <motion.article
        className="flex flex-col justify-between bg-white p-6 ring-1 ring-[#d9cfc0]"
        initial={reduce ? false : { x: -24 }}
        whileInView={{ x: 0 }}
        viewport={{ once: true, amount: 0.3 }}
        transition={{ duration: 0.7, ease: paperEase }}
        whileHover={reduce ? undefined : { y: -4 }}
      >
        <div>
          <p className="text-[10px] tracking-[0.18em] text-[#7c6a58] uppercase">
            The page
          </p>
          <h2 className="font-serif mt-2 text-2xl text-[#1c1917]">
            Editor with a quiet assistant
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-[#57534e]">
            TipTap on the original canvas. Chat on the side. Each suggestion is
            a card: the old line struck through, the new line waiting, Accept or
            Reject.
          </p>
          <ul className="mt-5 space-y-2 text-sm text-[#1c1917]">
            <li className="flex gap-2">
              <span className="text-[#b4533a]">—</span>
              No invented metrics, employers, or tools
            </li>
            <li className="flex gap-2">
              <span className="text-[#b4533a]">—</span>
              Download is a snapshot, so the working copy stays
            </li>
            <li className="flex gap-2">
              <span className="text-[#b4533a]">—</span>
              Fit to one page when you export
            </li>
          </ul>
        </div>
        <Link
          href="/resumes"
          className="mt-8 inline-flex self-start rounded-full bg-[#1c1917] px-3 py-1.5 text-sm text-[#f6f1e8] hover:bg-[#1c1917]/85"
        >
          Open the editor
        </Link>
      </motion.article>

      <motion.article
        className="flex flex-col justify-between bg-[#1c1917] p-6 text-[#f6f1e8]"
        initial={reduce ? false : { x: 24 }}
        whileInView={{ x: 0 }}
        viewport={{ once: true, amount: 0.3 }}
        transition={{ duration: 0.7, delay: 0.08, ease: paperEase }}
        whileHover={reduce ? undefined : { y: -4 }}
      >
        <div>
          <p className="text-[10px] tracking-[0.18em] text-[#d6c4a8] uppercase">
            The listings
          </p>
          <h2 className="font-serif mt-2 text-2xl">Jobs in a snapshot</h2>
          <p className="mt-3 text-sm leading-relaxed text-[#d6c4a8]">
            Title search, intern through senior, workplace and type chips. The
            list is twenty roles, then Next — not an infinite dump.
          </p>
          <ul className="mt-5 space-y-2 text-sm">
            <li className="flex gap-2">
              <span className="text-[#e8b298]">—</span>
              Public ATS JSON, stored locally
            </li>
            <li className="flex gap-2">
              <span className="text-[#e8b298]">—</span>
              Experience inferred from the title
            </li>
            <li className="flex gap-2">
              <span className="text-[#e8b298]">—</span>
              Open posting is the company’s own page
            </li>
          </ul>
        </div>
        <Link
          href="/jobs"
          className="mt-8 inline-flex self-start rounded-full border border-[#f6f1e8]/30 px-3 py-1.5 text-sm text-[#f6f1e8] hover:bg-white/10"
        >
          Browse the board
        </Link>
      </motion.article>
    </section>
  );
}
