import { useTranslations } from "next-intl";

import styles from "../workspace.module.css";

export function LoadingWorkspace() {
  const t = useTranslations("Workspace");

  return (
    <section className={styles.bootState} aria-live="polite">
      <span className={styles.spinner} aria-hidden="true" />
      <p>{t("loadingWorkspace")}</p>
    </section>
  );
}
