"use client";

import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import type { Locale } from "@/i18n/routing";
import type { DocumentItem } from "@/schema/document/document.schema";

import { errorMessageKey } from "../model/document-presentation";
import styles from "../workspace.module.css";
import { DocumentRow } from "./document-row";
import { DocumentUpload } from "./document-upload";
import { InlineError } from "./inline-error";

type DocumentLibraryProps = {
  documents: DocumentItem[];
  locale: Locale;
  errorCode: string | null;
  isLoading: boolean;
  hasNextPage: boolean;
  isLoadingMore: boolean;
  retryingDocumentId: string | null;
  deletingDocumentId: string | null;
  uploadProgress: number | null;
  isUploading: boolean;
  onUpload: (file: File) => void;
  onCancelUpload: () => void;
  onRetryDocument: (documentId: string) => void;
  onDeleteDocument: (documentId: string) => void;
  onLoadMore: () => void;
  onDismissError: () => void;
};

export function DocumentLibrary({
  documents,
  locale,
  errorCode,
  isLoading,
  hasNextPage,
  isLoadingMore,
  retryingDocumentId,
  deletingDocumentId,
  uploadProgress,
  isUploading,
  onUpload,
  onCancelUpload,
  onRetryDocument,
  onDeleteDocument,
  onLoadMore,
  onDismissError,
}: DocumentLibraryProps) {
  const t = useTranslations("Workspace");

  return (
    <aside className={styles.documentsPanel} aria-labelledby="documents-heading">
      <div className={styles.panelHeading}>
        <div>
          <p className={styles.kicker}>{t("sourcesKicker")}</p>
          <h3 id="documents-heading">{t("documentsTitle")}</h3>
        </div>
        <span className={styles.count}>{documents.length}</span>
      </div>

      <DocumentUpload
        isUploading={isUploading}
        progress={uploadProgress}
        onUpload={onUpload}
        onCancel={onCancelUpload}
      />

      {errorCode ? (
        <InlineError
          message={t(errorMessageKey(errorCode))}
          onDismiss={onDismissError}
        />
      ) : null}

      <div className={styles.documentList} aria-live="polite">
        {isLoading ? (
          <div className={styles.emptyDocuments}>
            <span className={styles.spinner} aria-hidden="true" />
            <p>{t("loadingWorkspace")}</p>
          </div>
        ) : documents.length === 0 ? (
          <div className={styles.emptyDocuments}>
            <strong>{t("noDocumentsTitle")}</strong>
            <p>{t("noDocumentsDescription")}</p>
          </div>
        ) : (
          documents.map((document) => (
            <DocumentRow
              key={document.document_id}
              document={document}
              locale={locale}
              isRetrying={retryingDocumentId === document.document_id}
              isDeleting={deletingDocumentId === document.document_id}
              onRetry={() => onRetryDocument(document.document_id)}
              onDelete={() => onDeleteDocument(document.document_id)}
            />
          ))
        )}
      </div>

      {hasNextPage ? (
        <Button
          className={styles.loadMore}
          variant="secondary"
          size="compact"
          onClick={onLoadMore}
          disabled={isLoadingMore}
        >
          {isLoadingMore ? t("loadingMore") : t("loadMore")}
        </Button>
      ) : null}
    </aside>
  );
}
