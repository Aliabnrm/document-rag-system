import { useTranslations } from "next-intl";

import styles from "../workspace.module.css";

type InlineErrorProps = {
  message: string;
  onDismiss?: () => void;
};

export function InlineError({ message, onDismiss }: InlineErrorProps) {
  const t = useTranslations("Workspace");

  return (
    <div className={styles.inlineError} role="alert">
      <span>{message}</span>
      {onDismiss ? (
        <button type="button" onClick={onDismiss} aria-label={t("dismissError")}>
          ×
        </button>
      ) : null}
    </div>
  );
}
