import type { DocumentStatus } from "@/schema/document/document.schema";

export const COLLECTION_STORAGE_KEY = "document-qa.collection-id";
export const MAX_UPLOAD_BYTES = 50 * 1024 * 1024;

export const PROCESSING_DOCUMENT_STATUSES = new Set<DocumentStatus>([
  "uploaded",
  "queued",
  "extracting",
  "chunking",
  "embedding",
]);
