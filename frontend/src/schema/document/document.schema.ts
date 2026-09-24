import { z } from "zod";

export const DocumentStatusSchema = z.enum([
  "uploaded",
  "queued",
  "extracting",
  "chunking",
  "embedding",
  "ready",
  "failed",
]);

export const IngestionJobStatusSchema = z.enum([
  "pending",
  "running",
  "succeeded",
  "failed",
  "retry_scheduled",
]);

export const DocumentSchema = z.object({
  document_id: z.string().uuid(),
  document_version_id: z.string().uuid(),
  display_name: z.string(),
  media_type: z.string(),
  size_bytes: z.number(),
  version_number: z.number(),
  status: DocumentStatusSchema,
  job_id: z.string().uuid(),
  job_status: IngestionJobStatusSchema,
  stage: z.string(),
  attempt_count: z.number(),
  error_code: z.string().nullable(),
  page_count: z.number().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const DocumentListSchema = z.object({
  items: z.array(DocumentSchema),
  next_cursor: z.string().nullable(),
});

export const UploadAcceptedSchema = z.object({
  document_id: z.string().uuid(),
  document_version_id: z.string().uuid(),
  job_id: z.string().uuid(),
  collection_id: z.string().uuid(),
  display_name: z.string(),
  version_number: z.number(),
  status: DocumentStatusSchema,
  job_status: IngestionJobStatusSchema,
  stage: z.string(),
  created_at: z.string(),
});

export type DocumentStatus = z.infer<typeof DocumentStatusSchema>;
export type DocumentItem = z.infer<typeof DocumentSchema>;
export type DocumentList = z.infer<typeof DocumentListSchema>;
export type UploadAccepted = z.infer<typeof UploadAcceptedSchema>;
