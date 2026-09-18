"use client";

import { useEffect, useState, type ReactNode } from "react";
import { motion, type HTMLMotionProps } from "motion/react";

export const paperEase = [0.16, 1, 0.3, 1] as const;

const viewport = { once: true, amount: 0.2 } as const;

export function useReduceMotionSafe() {
  const [reduce, setReduce] = useState(false);
  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduce(media.matches);
    const onChange = () => setReduce(media.matches);
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);
  return reduce;
}

export function Reveal({
  children,
  className,
  delay = 0,
  y = 22,
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
  y?: number;
}) {
  const reduce = useReduceMotionSafe();
  return (
    <motion.div
      className={className}
      initial={reduce ? false : { y }}
      whileInView={{ y: 0 }}
      viewport={viewport}
      transition={{ duration: 0.7, delay, ease: paperEase }}
    >
      {children}
    </motion.div>
  );
}

export function FadeIn({
  children,
  className,
  delay = 0,
  y = 14,
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
  y?: number;
}) {
  const reduce = useReduceMotionSafe();
  return (
    <motion.div
      className={className}
      initial={reduce ? false : { y }}
      animate={{ y: 0 }}
      transition={{ duration: 0.65, delay, ease: paperEase }}
    >
      {children}
    </motion.div>
  );
}

export function HoverLift(props: HTMLMotionProps<"div">) {
  const reduce = useReduceMotionSafe();
  return (
    <motion.div
      whileHover={reduce ? undefined : { y: -2 }}
      whileTap={reduce ? undefined : { scale: 0.98 }}
      {...props}
    />
  );
}
