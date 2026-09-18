"use client";

import { motion } from "motion/react";
import {
  Reveal,
  paperEase,
  useReduceMotionSafe,
} from "@/components/marketing/motion";

const STEPS = [
  {
    n: "I",
    title: "Upload the PDF",
    body: "We keep the page size and the lines. You do not start from a blank template.",
  },
  {
    n: "II",
    title: "Accept a rewrite",
    body: "Chat suggests one block at a time. Reject is a first-class action. Nothing lands until you say so.",
  },
  {
    n: "III",
    title: "Open a posting",
    body: "Filter the snapshot, read twenty roles, hit Next. The apply button is the company’s own page.",
  },
];

export function HowItWorks() {
  const reduce = useReduceMotionSafe();

  return (
    <section
      id="how"
      className="scroll-mt-20 border-y border-[#d9cfc0] bg-[#efe6d6]/60"
    >
      <div className="mx-auto max-w-6xl px-6 py-20">
        <Reveal>
          <p className="text-xs font-medium tracking-[0.22em] text-[#7c6a58] uppercase">
            Three moves
          </p>
          <h2 className="font-serif mt-3 text-3xl tracking-tight text-[#1c1917] sm:text-4xl">
            Desk, not dashboard.
          </h2>
        </Reveal>
        <ol className="mt-12 grid gap-8 md:grid-cols-3">
          {STEPS.map((step, index) => (
            <motion.li
              key={step.n}
              className="flex flex-col gap-3"
              initial={reduce ? false : { y: 18 }}
              whileInView={{ y: 0 }}
              viewport={{ once: true, amount: 0.4 }}
              transition={{
                duration: 0.6,
                delay: index * 0.12,
                ease: paperEase,
              }}
            >
              <motion.span
                className="font-serif text-4xl text-[#b4533a]"
                initial={reduce ? false : { scale: 0.85 }}
                whileInView={{ scale: 1 }}
                viewport={{ once: true }}
                transition={{
                  type: "spring",
                  stiffness: 200,
                  damping: 14,
                  delay: 0.1 + index * 0.12,
                }}
              >
                {step.n}
              </motion.span>
              <h3 className="text-base font-medium text-[#1c1917]">
                {step.title}
              </h3>
              <p className="text-sm leading-relaxed text-[#57534e]">
                {step.body}
              </p>
            </motion.li>
          ))}
        </ol>
      </div>
    </section>
  );
}
