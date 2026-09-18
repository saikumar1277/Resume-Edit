"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import {
  Reveal,
  paperEase,
  useReduceMotionSafe,
} from "@/components/marketing/motion";

const FAQS = [
  {
    q: "Do I have to rebuild my resume from a template?",
    a: "No. You upload the PDF you already use. We keep the page size, margins, and lines, then let you edit them in place.",
  },
  {
    q: "Will the assistant invent numbers or job titles?",
    a: "It is instructed not to. If a bullet needs a metric you did not write, it inserts a [QUANTIFY: …] placeholder instead of guessing.",
  },
  {
    q: "What is the note when I download a PDF?",
    a: "It is the search key in the resume menu. Name the snapshot after the company or round so you can find it later without renaming files.",
  },
  {
    q: "Where do the jobs come from?",
    a: "A local snapshot of public ATS JSON (Greenhouse, Lever, Ashby, Remotive) — not HTML scrape. The list shows twenty roles, then Next.",
  },
  {
    q: "Does download overwrite the copy I am editing?",
    a: "No. Download saves a snapshot first, then prints that copy to a one-page PDF.",
  },
];

export function Faq() {
  const [open, setOpen] = useState<number | null>(0);
  const reduce = useReduceMotionSafe();

  return (
    <section id="faq" className="scroll-mt-20 mx-auto max-w-3xl px-6 py-20">
      <Reveal>
        <p className="text-xs font-medium tracking-[0.22em] text-[#7c6a58] uppercase">
          In the margin
        </p>
        <h2 className="font-serif mt-3 text-3xl tracking-tight text-[#1c1917]">
          Questions, in plain ink.
        </h2>
      </Reveal>
      <div className="mt-10 divide-y divide-[#d9cfc0] border-y border-[#d9cfc0]">
        {FAQS.map((item, index) => {
          const isOpen = open === index;
          return (
            <div key={item.q}>
              <button
                type="button"
                className="flex w-full items-baseline justify-between gap-4 py-4 text-left"
                aria-expanded={isOpen}
                onClick={() => setOpen(isOpen ? null : index)}
              >
                <span className="text-base text-[#1c1917]">{item.q}</span>
                <motion.span
                  className="font-serif text-xl text-[#b4533a]"
                  aria-hidden
                  animate={{ rotate: isOpen ? 45 : 0 }}
                  transition={{ duration: reduce ? 0 : 0.25, ease: paperEase }}
                >
                  +
                </motion.span>
              </button>
              <AnimatePresence initial={false}>
                {isOpen ? (
                  <motion.div
                    initial={reduce ? false : { height: 0 }}
                    animate={{ height: "auto" }}
                    exit={reduce ? undefined : { height: 0 }}
                    transition={{ duration: 0.32, ease: paperEase }}
                    className="overflow-hidden"
                  >
                    <p className="pb-4 text-sm leading-relaxed text-[#57534e]">
                      {item.a}
                    </p>
                  </motion.div>
                ) : null}
              </AnimatePresence>
            </div>
          );
        })}
      </div>
    </section>
  );
}
