import type { HTMLAttributes, ReactNode } from "react";
import styles from "./Card.module.css";

type Tone =
  | "canvas"
  | "cream"
  | "soft"
  | "pink"
  | "teal"
  | "lavender"
  | "peach"
  | "ochre"
  | "mint";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  tone?: Tone;
  size?: "sm" | "md" | "lg";
  padded?: boolean;
  children: ReactNode;
}

export function Card({
  tone = "canvas",
  size = "md",
  padded = true,
  className,
  children,
  ...rest
}: CardProps) {
  const cls = [
    styles.card,
    styles[`tone-${tone}`],
    styles[`size-${size}`],
    padded ? styles.padded : "",
    className ?? "",
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <div className={cls} {...rest}>
      {children}
    </div>
  );
}
