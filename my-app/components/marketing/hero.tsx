"use client";

import Link from "next/link";
import { motion } from "motion/react";
import {
  FadeIn,
  HoverLift,
  paperEase,
  useReduceMotionSafe,
} from "@/components/marketing/motion";

export function Hero() {
  return (
    <section className="mx-auto grid max-w-6xl items-center gap-12 px-6 py-16 md:grid-cols-[1.1fr_0.9fr] md:py-24">
      <div>
        <FadeIn>
          <p className="text-xs font-medium tracking-[0.22em] text-[#7c6a58] uppercase">
            A desk for the job hunt
          </p>
        </FadeIn>
        <FadeIn delay={0.08}>
          <h1 className="font-serif mt-4 max-w-xl text-4xl leading-[1.08] tracking-tight text-[#1c1917] sm:text-5xl md:text-6xl">
            Keep the page. Change the line they actually read.
          </h1>
        </FadeIn>
        <FadeIn delay={0.16}>
          <p className="mt-5 max-w-md text-base leading-relaxed text-[#57534e]">
            Upload the PDF you already have. Accept rewrites one bullet at a
            time. When the page feels honest, open a posting from the snapshot —
            twenty roles at a time, not a firehose.
          </p>
        </FadeIn>
        <FadeIn delay={0.24}>
          <div className="mt-8 flex flex-wrap gap-3">
            <HoverLift>
              <Link
                href="/resumes"
                className="inline-flex h-10 items-center rounded-full bg-[#1c1917] px-5 text-sm font-medium text-[#f6f1e8] hover:bg-[#1c1917]/85"
              >
                Upload a resume
              </Link>
            </HoverLift>
            <HoverLift>
              <Link
                href="/jobs"
                className="inline-flex h-10 items-center rounded-full border border-[#c4b6a4] px-5 text-sm font-medium text-[#1c1917] hover:bg-white/50"
              >
                See open roles
              </Link>
            </HoverLift>
          </div>
        </FadeIn>
      </div>

      <PaperMock />
    </section>
  );
}

function PaperMock() {
  const reduce = useReduceMotionSafe();

  return (
    <div className="relative mx-auto w-full max-w-sm" aria-hidden>
      <motion.div
        className="absolute -left-6 top-10 hidden h-28 w-20 rounded-sm bg-[#e7dcc8] shadow-sm md:block"
        initial={reduce ? false : { rotate: -16, y: -12 }}
        animate={{ rotate: -8, y: 0 }}
        transition={{ duration: 0.8, delay: 0.2, ease: paperEase }}
      />
      <motion.div
        className="relative rounded-sm bg-white px-7 py-8 shadow-[0_18px_40px_-24px_rgba(28,25,23,0.45)] ring-1 ring-[#d9cfc0]"
        initial={reduce ? false : { y: -28, rotate: -8 }}
        animate={{ y: 0, rotate: 2 }}
        transition={{
          type: "spring",
          stiffness: 70,
          damping: 14,
          delay: 0.12,
        }}
        whileHover={reduce ? undefined : { rotate: 0, y: -4 }}
      >
        <p className="text-center text-[11px] font-semibold tracking-[0.18em] text-[#1c1917]">
          A. CANDIDATE
        </p>
        <p className="mt-1 text-center text-[9px] text-[#7c6a58]">
          Binghamton, NY · software engineer
        </p>
        <div className="mx-auto mt-3 h-px w-24 bg-[#1c1917]" />
        <p className="mt-4 text-[10px] font-semibold tracking-[0.16em] text-[#1c1917]">
          EXPERIENCE
        </p>
        <motion.p
          className="mt-2 text-[11px] leading-snug text-[#7c6a58] line-through"
          initial={reduce ? false : { y: 6 }}
          animate={{ y: 0 }}
          transition={{ delay: 0.55, duration: 0.4, ease: paperEase }}
        >
          Responsible for helping build an AI assistant and other features.
        </motion.p>
        <motion.p
          className="mt-2 border-l-2 border-[#b4533a] pl-2 text-[11px] leading-snug text-[#1c1917]"
          initial={reduce ? false : { x: -8 }}
          animate={{ x: 0 }}
          transition={{ delay: 0.75, duration: 0.45, ease: paperEase }}
        >
          Built Sam Bot, a RAG compliance assistant, cutting Medicaid waiver
          lookup from hours to seconds.
        </motion.p>
        <motion.span
          className="mt-3 inline-block rounded-full bg-[#f3e4d4] px-2 py-0.5 text-[9px] tracking-wide text-[#9a3412] uppercase"
          initial={reduce ? false : { scale: 0.7, rotate: -12 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{
            type: "spring",
            stiffness: 260,
            damping: 16,
            delay: 0.95,
          }}
        >
          Rewrite waiting
        </motion.span>
      </motion.div>
    </div>
  );
}
