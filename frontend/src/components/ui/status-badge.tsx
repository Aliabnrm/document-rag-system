import type { ReactNode } from "react";

import styles from "./primitives.module.css";

export function StatusBadge({
  children,
  tone,
}: {
  children: ReactNode;
  tone: "neutral" | "progress" | "success" | "danger" | "warning";
}) {
  return (
    <span className={`${styles.badge} ${styles[`badge_${tone}`]}`}>
      <span className={styles.badgeDot} aria-hidden="true" />
      {children}
    </span>
  );
}
