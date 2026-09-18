"use client";

import { motion } from "motion/react";
import { Reveal, useReduceMotionSafe } from "@/components/marketing/motion";

const LETTERS = [
  {
    name: "Maya Chen",
    landed: "Backend intern, NYC",
    quote:
      "I accepted three bullets and left the rest. The page still looked like mine — just tighter.",
    note: "Accepted 3 rewrites",
    rotate: -2,
    featured: true,
  },
  {
    name: "Jordan Hale",
    landed: "Career switch into PM",
    quote:
      "The assistant refused to invent a metric. It put [QUANTIFY] instead. That honesty is why I used it.",
    note: "Past week of roles",
    rotate: 1.4,
    featured: false,
  },
  {
    name: "Priya Nair",
    landed: "New-grad SWE, remote",
    quote:
      "Search by the note I typed at download. I keep a Google round and an intern round without mixing files.",
    note: "Snapshot download",
    rotate: 2.2,
    featured: false,
  },
  {
    name: "Alex Okonkwo",
    landed: "Senior designer, hybrid",
    quote:
      "Twenty jobs, then Next. I can actually read a posting instead of scrolling a thousand cards.",
    note: "Jobs, 20 at a time",
    rotate: -1.6,
    featured: false,
  },
  {
    name: "Sam Rivera",
    landed: "Teaching assistant → intern",
    quote:
      "I pasted the job description in chat. It reused words I already earned — nothing I had not done.",
    note: "Tailored in chat",
    rotate: 3,
    featured: false,
  },
];

export function Reviews() {
  const featured = LETTERS.find((letter) => letter.featured)!;
  const rest = LETTERS.filter((letter) => !letter.featured);

  return (
    <section id="reviews" className="scroll-mt-20 mx-auto max-w-6xl px-6 py-20">
      <Reveal>
        <p className="text-xs font-medium tracking-[0.22em] text-[#7c6a58] uppercase">
          From the desk
        </p>
        <h2 className="font-serif mt-3 max-w-lg text-3xl tracking-tight text-[#1c1917] sm:text-4xl">
          Letters, not star ratings.
        </h2>
        <p className="mt-3 max-w-md text-sm leading-relaxed text-[#57534e]">
          Imagined notes from people who kept their original page and only
          accepted the lines that still sounded like them.
        </p>
      </Reveal>

      <div className="mt-12 grid items-start gap-6 md:grid-cols-[1.15fr_0.85fr]">
        <LetterCard letter={featured} delay={0.08} tall />
        <div className="grid gap-4 sm:grid-cols-2">
          {rest.map((letter, index) => (
            <LetterCard
              key={letter.name}
              letter={letter}
              delay={0.12 + index * 0.08}
            />
          ))}
        </div>
      </div>
    </section>
  );
}

function LetterCard({
  letter,
  delay,
  tall,
}: {
  letter: (typeof LETTERS)[number];
  delay: number;
  tall?: boolean;
}) {
  const reduce = useReduceMotionSafe();
  const restRotate = letter.rotate;

  return (
    <motion.article
      className={`origin-center bg-[#fffaf3] p-5 shadow-[4px_8px_0_0_rgba(28,25,23,0.06)] ring-1 ring-[#d9cfc0] ${tall ? "md:min-h-80" : ""}`}
      initial={reduce ? false : { y: -20, rotate: restRotate - 6 }}
      whileInView={{ y: 0, rotate: restRotate }}
      viewport={{ once: true, amount: 0.25 }}
      transition={{
        type: "spring",
        stiffness: 90,
        damping: 16,
        delay,
      }}
      whileHover={
        reduce ? undefined : { y: -8, rotate: 0, scale: 1.02, zIndex: 2 }
      }
    >
      <p className="text-[10px] tracking-[0.18em] text-[#9a3412] uppercase">
        {letter.note}
      </p>
      <blockquote className="font-serif mt-3 text-lg leading-snug text-[#1c1917]">
        {letter.quote}
      </blockquote>
      <footer className="mt-4 border-t border-dashed border-[#d9cfc0] pt-3 text-sm">
        <p className="font-medium text-[#1c1917]">{letter.name}</p>
        <p className="text-[#7c6a58]">{letter.landed}</p>
      </footer>
    </motion.article>
  );
}
