import type { HTMLAttributes, ReactNode } from "react";
import styles from "./Pill.module.css";

type Tone = "default" | "ink" | "pink" | "teal" | "lavender" | "ochre" | "mint";

interface PillProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: Tone;
  children: ReactNode;
}

export function Pill({ tone = "default", className, children, ...rest }: PillProps) {
  const cls = [styles.pill, styles[`tone-${tone}`], className ?? ""]
    .filter(Boolean)
    .join(" ");
  return (
    <span className={cls} {...rest}>
      {children}
    </span>
  );
}
