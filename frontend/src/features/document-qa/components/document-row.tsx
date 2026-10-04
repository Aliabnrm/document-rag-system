import { useTranslations } from "next-intl";

import { StatusBadge } from "@/components/ui/status-badge";
import type { Locale } from "@/i18n/routing";
import type { DocumentItem } from "@/schema/document/document.schema";

import {
  documentStatusMessageKey,
  errorMessageKey,
  formatFileSize,
} from "../model/document-presentation";
import styles from "../workspace.module.css";
import { DeleteConfirmation } from "./delete-confirmation";

type DocumentRowProps = {
  document: DocumentItem;
  locale: Locale;
  isRetrying: boolean;
  isDeleting: boolean;
  onRetry: () => void;
  onDelete: () => void;
};

export function DocumentRow({
  document,
  locale,
  isRetrying,
  isDeleting,
  onRetry,
  onDelete,
}: DocumentRowProps) {
  const t = useTranslations("Workspace");
  const tone =
    document.status === "ready"
      ? "success"
      : document.status === "failed"
        ? "danger"
        : "progress";

  return (
    <article className={styles.documentRow}>
      <div className={styles.fileMark} aria-hidden="true">
        {document.media_type === "application/pdf" ? "PDF" : "TXT"}
      </div>
      <div className={styles.documentInfo}>
        <strong dir="auto" title={document.display_name}>
          {document.display_name}
        </strong>
        <div className={styles.documentMeta}>
          <span>{formatFileSize(document.size_bytes, locale)}</span>
          {document.page_count ? (
            <span>{t("pageCount", { count: document.page_count })}</span>
          ) : null}
        </div>
        <StatusBadge tone={tone}>
          {t(documentStatusMessageKey(document.status))}
        </StatusBadge>
        {document.error_code ? (
          <p className={styles.documentError}>
            {t(errorMessageKey(document.error_code))}
          </p>
        ) : null}
        <div className={styles.documentActions}>
          {document.status === "failed" ? (
            <button
              type="button"
              className={styles.textButton}
              onClick={onRetry}
              disabled={isRetrying}
            >
              {t("retry")}
            </button>
          ) : null}
          <DeleteConfirmation
            label={t("deleteDocument")}
            confirmation={t("deleteDocumentConfirmation", {
              name: document.display_name,
            })}
            isPending={isDeleting}
            onConfirm={onDelete}
          />
        </div>
      </div>
    </article>
  );
}
