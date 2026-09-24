"use client";

import { useTranslations } from "next-intl";
import { type ChangeEvent, type DragEvent, type FormEvent, useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/status-badge";
import type { Locale } from "@/i18n/routing";

import {
  ApiError,
  type Citation,
  type Collection,
  type DocumentItem,
  createCollection,
  createConversation,
  getCollection,
  getDocument,
  listDocuments,
  retryDocument,
  streamAnswer,
  uploadDocument,
} from "./api";
import styles from "./workspace.module.css";

const COLLECTION_STORAGE_KEY = "document-qa.collection-id";
const MAX_UPLOAD_BYTES = 50 * 1024 * 1024;
const PROCESSING_STATUSES = new Set<DocumentItem["status"]>([
  "uploaded",
  "queued",
  "extracting",
  "chunking",
  "embedding",
]);

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  status?: "retrieving" | "streaming" | "complete" | "failed" | "cancelled";
  citations?: Citation[];
  abstained?: boolean;
};

export function DocumentQaWorkspace({ locale }: { locale: Locale }) {
  const t = useTranslations("Workspace");
  const [collection, setCollection] = useState<Collection | null>(null);
  const [collectionName, setCollectionName] = useState("");
  const [collectionDescription, setCollectionDescription] = useState("");
  const [isBooting, setIsBooting] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [isAnswering, setIsAnswering] = useState(false);
  const [lastQuestion, setLastQuestion] = useState<string | null>(null);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const uploadAbortRef = useRef<AbortController | null>(null);
  const answerAbortRef = useRef<AbortController | null>(null);
  const evidencePanelRef = useRef<HTMLElement>(null);
  const citationTriggerRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const savedId = window.localStorage.getItem(COLLECTION_STORAGE_KEY);
    if (!savedId) {
      queueMicrotask(() => setIsBooting(false));
      return () => controller.abort();
    }
    Promise.all([getCollection(savedId, controller.signal), listDocuments(savedId, { signal: controller.signal })])
      .then(([savedCollection, page]) => {
        setCollection(savedCollection);
        setDocuments(page.items);
        setNextCursor(page.next_cursor);
      })
      .catch((error: unknown) => {
        if (!isAbortError(error)) {
          window.localStorage.removeItem(COLLECTION_STORAGE_KEY);
          setErrorCode(errorCodeOf(error));
        }
      })
      .finally(() => setIsBooting(false));
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!collection || !documents.some((item) => PROCESSING_STATUSES.has(item.status))) return;
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      const processing = documents.filter((item) => PROCESSING_STATUSES.has(item.status));
      try {
        const refreshed = await Promise.all(
          processing.map((item) =>
            getDocument(collection.id, item.document_id, controller.signal),
          ),
        );
        const byId = new Map(refreshed.map((item) => [item.document_id, item]));
        setDocuments((current) => current.map((item) => byId.get(item.document_id) ?? item));
      } catch (error: unknown) {
        if (!isAbortError(error)) setErrorCode(errorCodeOf(error));
      }
    }, 1200);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [collection, documents]);

  useEffect(() => {
    if (!selectedCitation) return;
    const trigger = citationTriggerRef.current;
    const panel = evidencePanelRef.current;
    panel?.querySelector<HTMLButtonElement>("button")?.focus();
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setSelectedCitation(null);
    };
    window.addEventListener("keydown", handleEscape);
    return () => {
      window.removeEventListener("keydown", handleEscape);
      trigger?.focus();
    };
  }, [selectedCitation]);

  const readyDocuments = documents.filter((item) => item.status === "ready");

  async function handleCreateCollection(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!collectionName.trim()) return;
    setIsCreating(true);
    setErrorCode(null);
    try {
      const created = await createCollection({
        name: collectionName.trim(),
        description: collectionDescription.trim(),
      });
      window.localStorage.setItem(COLLECTION_STORAGE_KEY, created.id);
      setCollection(created);
      setDocuments([]);
      setNextCursor(null);
    } catch (error: unknown) {
      setErrorCode(errorCodeOf(error));
    } finally {
      setIsCreating(false);
    }
  }

  async function handleFiles(files: FileList | File[]) {
    const file = files[0];
    if (!collection || !file) return;
    const validationError = validateFile(file);
    if (validationError) {
      setErrorCode(validationError);
      return;
    }
    const controller = new AbortController();
    uploadAbortRef.current = controller;
    setUploadProgress(0);
    setErrorCode(null);
    try {
      await uploadDocument(collection.id, file, {
        onProgress: setUploadProgress,
        signal: controller.signal,
      });
      const page = await listDocuments(collection.id, { signal: controller.signal });
      setDocuments(page.items);
      setNextCursor(page.next_cursor);
    } catch (error: unknown) {
      if (!isAbortError(error)) setErrorCode(errorCodeOf(error));
    } finally {
      uploadAbortRef.current = null;
      setUploadProgress(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    void handleFiles(event.dataTransfer.files);
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    if (event.target.files) void handleFiles(event.target.files);
  }

  async function handleLoadMore() {
    if (!collection || !nextCursor) return;
    setIsLoadingMore(true);
    try {
      const page = await listDocuments(collection.id, { cursor: nextCursor });
      setDocuments((current) => [...current, ...page.items]);
      setNextCursor(page.next_cursor);
    } catch (error: unknown) {
      setErrorCode(errorCodeOf(error));
    } finally {
      setIsLoadingMore(false);
    }
  }

  async function handleRetryDocument(documentId: string) {
    if (!collection) return;
    setErrorCode(null);
    try {
      const refreshed = await retryDocument(collection.id, documentId);
      setDocuments((current) =>
        current.map((item) => (item.document_id === documentId ? refreshed : item)),
      );
    } catch (error: unknown) {
      setErrorCode(errorCodeOf(error));
    }
  }

  async function submitQuestion(value: string) {
    if (!collection || !value.trim() || isAnswering || readyDocuments.length === 0) return;
    const trimmed = value.trim();
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed,
    };
    const assistantId = crypto.randomUUID();
    setMessages((current) => [
      ...current,
      userMessage,
      { id: assistantId, role: "assistant", content: "", status: "retrieving" },
    ]);
    setQuestion("");
    setLastQuestion(trimmed);
    setIsAnswering(true);
    setErrorCode(null);
    const controller = new AbortController();
    answerAbortRef.current = controller;
    try {
      const activeConversationId =
        conversationId ?? (await createConversation(collection.id, controller.signal));
      if (!conversationId) setConversationId(activeConversationId);
      await streamAnswer({
        conversationId: activeConversationId,
        question: trimmed,
        language: locale,
        signal: controller.signal,
        onEvent: (event) => {
          setMessages((current) =>
            current.map((message) => {
              if (message.id !== assistantId) return message;
              if (event.event === "retrieval_completed") {
                return { ...message, status: "streaming" };
              }
              if (event.event === "answer_delta") {
                return {
                  ...message,
                  content: message.content + event.data.text,
                  status: "streaming",
                };
              }
              if (event.event === "citations") {
                return { ...message, citations: event.data.items };
              }
              if (event.event === "completed") {
                return {
                  ...message,
                  status: "complete",
                  abstained: event.data.abstained,
                };
              }
              if (event.event === "failure") {
                return { ...message, status: "failed" };
              }
              return message;
            }),
          );
          if (event.event === "failure") setErrorCode(event.data.code);
        },
      });
    } catch (error: unknown) {
      const cancelled = isAbortError(error);
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantId
            ? { ...message, status: cancelled ? "cancelled" : "failed" }
            : message,
        ),
      );
      if (!cancelled) setErrorCode(errorCodeOf(error));
    } finally {
      answerAbortRef.current = null;
      setIsAnswering(false);
    }
  }

  function handleQuestionSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitQuestion(question);
  }

  function resetCollection() {
    answerAbortRef.current?.abort();
    uploadAbortRef.current?.abort();
    window.localStorage.removeItem(COLLECTION_STORAGE_KEY);
    setCollection(null);
    setDocuments([]);
    setMessages([]);
    setConversationId(null);
    setSelectedCitation(null);
    setErrorCode(null);
  }

  if (isBooting) {
    return (
      <section className={styles.bootState} aria-live="polite">
        <span className={styles.spinner} aria-hidden="true" />
        <p>{t("loadingWorkspace")}</p>
      </section>
    );
  }

  if (!collection) {
    return (
      <section className={styles.onboarding} aria-labelledby="workspace-heading">
        <div className={styles.onboardingIntro}>
          <p className={styles.kicker}>{t("startKicker")}</p>
          <h2 id="workspace-heading">{t("startTitle")}</h2>
          <p>{t("startDescription")}</p>
        </div>
        <form className={styles.collectionForm} onSubmit={handleCreateCollection}>
          <label htmlFor="collection-name">{t("collectionName")}</label>
          <input
            id="collection-name"
            value={collectionName}
            onChange={(event) => setCollectionName(event.target.value)}
            maxLength={160}
            placeholder={t("collectionNamePlaceholder")}
            required
          />
          <label htmlFor="collection-description">{t("collectionDescription")}</label>
          <textarea
            id="collection-description"
            value={collectionDescription}
            onChange={(event) => setCollectionDescription(event.target.value)}
            maxLength={1000}
            placeholder={t("collectionDescriptionPlaceholder")}
            rows={3}
          />
          {errorCode ? <InlineError message={errorText(errorCode, t)} /> : null}
          <Button type="submit" disabled={isCreating || !collectionName.trim()}>
            {isCreating ? t("creatingCollection") : t("createCollection")}
          </Button>
        </form>
      </section>
    );
  }

  return (
    <section className={styles.workspace} aria-labelledby="collection-heading">
      <header className={styles.workspaceHeader}>
        <div>
          <p className={styles.kicker}>{t("activeCollection")}</p>
          <h2 id="collection-heading" dir="auto">{collection.name}</h2>
          {collection.description ? <p dir="auto">{collection.description}</p> : null}
        </div>
        <Button variant="quiet" size="compact" onClick={resetCollection}>
          {t("changeCollection")}
        </Button>
      </header>

      {errorCode ? (
        <InlineError message={errorText(errorCode, t)} onDismiss={() => setErrorCode(null)} />
      ) : null}

      <div className={styles.workspaceGrid}>
        <aside className={styles.documentsPanel} aria-labelledby="documents-heading">
          <div className={styles.panelHeading}>
            <div>
              <p className={styles.kicker}>{t("sourcesKicker")}</p>
              <h3 id="documents-heading">{t("documentsTitle")}</h3>
            </div>
            <span className={styles.count}>{documents.length}</span>
          </div>

          <div
            className={styles.dropzone}
            onDragOver={(event) => event.preventDefault()}
            onDrop={handleDrop}
          >
            <input
              ref={fileInputRef}
              className={styles.visuallyHidden}
              id="document-file"
              type="file"
              accept=".pdf,.txt,application/pdf,text/plain"
              onChange={handleFileChange}
              disabled={uploadProgress !== null}
            />
            <div className={styles.uploadIcon} aria-hidden="true">↑</div>
            <strong>{t("dropFile")}</strong>
            <span>{t("fileRequirements")}</span>
            <Button
              variant="secondary"
              size="compact"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploadProgress !== null}
            >
              {t("chooseFile")}
            </Button>
            {uploadProgress !== null ? (
              <div
                className={styles.uploadProgress}
                aria-live="polite"
                role="progressbar"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={uploadProgress}
                aria-label={t("uploading", { progress: uploadProgress })}
              >
                <div className={styles.progressTrack}>
                  <span style={{ inlineSize: `${uploadProgress}%` }} />
                </div>
                <div className={styles.progressMeta}>
                  <span>{t("uploading", { progress: uploadProgress })}</span>
                  <button type="button" onClick={() => uploadAbortRef.current?.abort()}>
                    {t("cancel")}
                  </button>
                </div>
              </div>
            ) : null}
          </div>

          <div className={styles.documentList} aria-live="polite">
            {documents.length === 0 ? (
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
                  statusLabel={statusText(document.status, t)}
                  failureLabel={document.error_code ? errorText(document.error_code, t) : null}
                  onRetry={() => void handleRetryDocument(document.document_id)}
                  retryLabel={t("retry")}
                  pageLabel={t("pageCount", { count: document.page_count ?? 0 })}
                />
              ))
            )}
          </div>
          {nextCursor ? (
            <Button
              className={styles.loadMore}
              variant="secondary"
              size="compact"
              onClick={() => void handleLoadMore()}
              disabled={isLoadingMore}
            >
              {isLoadingMore ? t("loadingMore") : t("loadMore")}
            </Button>
          ) : null}
        </aside>

        <main className={styles.chatPanel}>
          <div className={styles.chatHeader}>
            <div>
              <p className={styles.kicker}>{t("answerKicker")}</p>
              <h3>{t("chatTitle")}</h3>
            </div>
            <StatusBadge tone={readyDocuments.length ? "success" : "neutral"}>
              {readyDocuments.length
                ? t("readySources", { count: readyDocuments.length })
                : t("waitingForSource")}
            </StatusBadge>
          </div>

          <div className={styles.messages} aria-live="polite" aria-relevant="additions text">
            {messages.length === 0 ? (
              <div className={styles.chatEmpty}>
                <div className={styles.chatEmptyMark} aria-hidden="true">“</div>
                <h4>{t("chatEmptyTitle")}</h4>
                <p>
                  {readyDocuments.length
                    ? t("chatEmptyReady")
                    : t("chatEmptyWaiting")}
                </p>
              </div>
            ) : (
              messages.map((message) => (
                <article
                  key={message.id}
                  className={`${styles.message} ${styles[message.role]}`}
                >
                  <p className={styles.messageRole}>
                    {message.role === "user" ? t("you") : t("groundedAnswer")}
                  </p>
                  {message.status === "retrieving" && !message.content ? (
                    <p className={styles.retrieving}>
                      <span className={styles.spinner} aria-hidden="true" />
                      {t("retrievingEvidence")}
                    </p>
                  ) : (
                    <p className={styles.messageContent} dir="auto">
                      {message.content ||
                        (message.status === "failed"
                          ? t("answerFailed")
                          : message.status === "cancelled"
                            ? t("answerCancelled")
                            : "")}
                    </p>
                  )}
                  {message.abstained ? (
                    <StatusBadge tone="warning">{t("insufficientEvidence")}</StatusBadge>
                  ) : null}
                  {message.citations?.length ? (
                    <div className={styles.citations}>
                      <p>{t("evidenceUsed")}</p>
                      {message.citations.map((citation) => (
                        <button
                          type="button"
                          key={citation.evidence_id}
                          className={styles.citationButton}
                          onClick={(event) => {
                            citationTriggerRef.current = event.currentTarget;
                            setSelectedCitation(citation);
                          }}
                          aria-label={t("openCitation", {
                            document: citation.document_name,
                            page: citation.page_start,
                          })}
                        >
                          <span>{citation.evidence_id}</span>
                          <strong dir="auto">{citation.document_name}</strong>
                          <small>{pageRange(citation, t)}</small>
                        </button>
                      ))}
                    </div>
                  ) : null}
                </article>
              ))
            )}
          </div>

          <form className={styles.composer} onSubmit={handleQuestionSubmit}>
            <label className={styles.visuallyHidden} htmlFor="question">
              {t("questionLabel")}
            </label>
            <textarea
              id="question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder={
                readyDocuments.length ? t("questionPlaceholder") : t("questionDisabled")
              }
              disabled={readyDocuments.length === 0 || isAnswering}
              rows={2}
              maxLength={4000}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  event.currentTarget.form?.requestSubmit();
                }
              }}
            />
            <div className={styles.composerFooter}>
              <span>{t("composerHint")}</span>
              {isAnswering ? (
                <Button variant="danger" size="compact" onClick={() => answerAbortRef.current?.abort()}>
                  {t("stopAnswer")}
                </Button>
              ) : (
                <Button type="submit" disabled={!question.trim() || readyDocuments.length === 0}>
                  {t("askQuestion")}
                </Button>
              )}
            </div>
            {!isAnswering && lastQuestion && messages.at(-1)?.status === "failed" ? (
              <button
                type="button"
                className={styles.retryAnswer}
                onClick={() => void submitQuestion(lastQuestion)}
              >
                {t("retryLastQuestion")}
              </button>
            ) : null}
          </form>
        </main>
      </div>

      {selectedCitation ? (
        <aside
          ref={evidencePanelRef}
          className={styles.evidencePanel}
          aria-labelledby="evidence-heading"
          aria-modal="true"
          role="dialog"
          onKeyDown={(event) => {
            if (event.key === "Tab") {
              event.preventDefault();
              evidencePanelRef.current?.querySelector<HTMLButtonElement>("button")?.focus();
            }
          }}
        >
          <header>
            <div>
              <p className={styles.kicker}>{selectedCitation.evidence_id}</p>
              <h3 id="evidence-heading" dir="auto">{selectedCitation.document_name}</h3>
              <p>{pageRange(selectedCitation, t)}</p>
            </div>
            <Button variant="quiet" size="compact" onClick={() => setSelectedCitation(null)}>
              {t("closeEvidence")}
            </Button>
          </header>
          <blockquote dir="auto">{selectedCitation.snippet}</blockquote>
          <p className={styles.evidenceNote}>{t("evidenceNote")}</p>
        </aside>
      ) : null}
    </section>
  );
}

function DocumentRow({
  document,
  locale,
  statusLabel,
  failureLabel,
  onRetry,
  retryLabel,
  pageLabel,
}: {
  document: DocumentItem;
  locale: Locale;
  statusLabel: string;
  failureLabel: string | null;
  onRetry: () => void;
  retryLabel: string;
  pageLabel: string;
}) {
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
        <strong dir="auto" title={document.display_name}>{document.display_name}</strong>
        <div className={styles.documentMeta}>
          <span>{formatBytes(document.size_bytes, locale)}</span>
          {document.page_count ? <span>{pageLabel}</span> : null}
        </div>
        <StatusBadge tone={tone}>{statusLabel}</StatusBadge>
        {failureLabel ? <p className={styles.documentError}>{failureLabel}</p> : null}
        {document.status === "failed" ? (
          <button type="button" className={styles.textButton} onClick={onRetry}>
            {retryLabel}
          </button>
        ) : null}
      </div>
    </article>
  );
}

function InlineError({ message, onDismiss }: { message: string; onDismiss?: () => void }) {
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

function validateFile(file: File): string | null {
  const extension = file.name.split(".").pop()?.toLowerCase();
  if (extension !== "pdf" && extension !== "txt") return "unsupported_file_type";
  if (file.size === 0) return "empty_file";
  if (file.size > MAX_UPLOAD_BYTES) return "file_too_large";
  return null;
}

function statusText(status: DocumentItem["status"], t: ReturnType<typeof useTranslations>) {
  switch (status) {
    case "uploaded": return t("statusUploaded");
    case "queued": return t("statusQueued");
    case "extracting": return t("statusExtracting");
    case "chunking": return t("statusChunking");
    case "embedding": return t("statusEmbedding");
    case "ready": return t("statusReady");
    case "failed": return t("statusFailed");
  }
}

function errorText(code: string, t: ReturnType<typeof useTranslations>) {
  switch (code) {
    case "file_too_large": return t("errorFileTooLarge");
    case "empty_file": return t("errorEmptyFile");
    case "unsupported_file_type": return t("errorUnsupportedType");
    case "mime_mismatch":
    case "extension_mismatch": return t("errorFileMismatch");
    case "invalid_text_encoding": return t("errorTextEncoding");
    case "encrypted_pdf": return t("errorEncryptedPdf");
    case "likely_scanned_pdf": return t("errorScannedPdf");
    case "invalid_pdf":
    case "pdf_extraction_failed": return t("errorPdfExtraction");
    case "queue_unavailable":
    case "dependency_unavailable":
    case "dependency_timeout": return t("errorProcessingUnavailable");
    case "network_error": return t("errorNetwork");
    case "invalid_model_citations": return t("errorInvalidCitations");
    case "answer_pipeline_failed": return t("errorAnswerFailed");
    default: return t("errorGeneric");
  }
}

function errorCodeOf(error: unknown): string {
  if (error instanceof ApiError) return error.code;
  return "network_error";
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

function formatBytes(bytes: number, locale: Locale): string {
  const megabytes = bytes / (1024 * 1024);
  return `${new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(megabytes)} MB`;
}

function pageRange(citation: Citation, t: ReturnType<typeof useTranslations>): string {
  return citation.page_start === citation.page_end
    ? t("page", { page: citation.page_start })
    : t("pageRange", { start: citation.page_start, end: citation.page_end });
}
