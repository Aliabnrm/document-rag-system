import type { DocumentStatus } from "@/schema/document/document.schema";

import { MAX_UPLOAD_BYTES } from "./constants";

export function validateDocumentFile(file: File): string | null {
  const extension = file.name.split(".").pop()?.toLowerCase();
  if (extension !== "pdf" && extension !== "txt") return "unsupported_file_type";
  if (file.size === 0) return "empty_file";
  if (file.size > MAX_UPLOAD_BYTES) return "file_too_large";
  return null;
}

export function documentStatusMessageKey(status: DocumentStatus): string {
  const keys: Record<DocumentStatus, string> = {
    uploaded: "statusUploaded",
    queued: "statusQueued",
    extracting: "statusExtracting",
    chunking: "statusChunking",
    embedding: "statusEmbedding",
    ready: "statusReady",
    failed: "statusFailed",
  };
  return keys[status];
}

export function errorMessageKey(code: string): string {
  const keys: Record<string, string> = {
    file_too_large: "errorFileTooLarge",
    empty_file: "errorEmptyFile",
    unsupported_file_type: "errorUnsupportedType",
    mime_mismatch: "errorFileMismatch",
    extension_mismatch: "errorFileMismatch",
    invalid_text_encoding: "errorTextEncoding",
    encrypted_pdf: "errorEncryptedPdf",
    likely_scanned_pdf: "errorScannedPdf",
    invalid_pdf: "errorPdfExtraction",
    pdf_extraction_failed: "errorPdfExtraction",
    queue_unavailable: "errorProcessingUnavailable",
    dependency_unavailable: "errorProcessingUnavailable",
    dependency_timeout: "errorProcessingUnavailable",
    network_error: "errorNetwork",
    invalid_model_citations: "errorInvalidCitations",
    answer_pipeline_failed: "errorAnswerFailed",
  };
  return keys[code] ?? "errorGeneric";
}

export function formatFileSize(bytes: number, locale: string): string {
  const megabytes = bytes / (1024 * 1024);
  return `${new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(megabytes)} MB`;
}
