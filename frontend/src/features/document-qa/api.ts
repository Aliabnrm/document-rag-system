import { z } from "zod";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const collectionSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  description: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

const documentSchema = z.object({
  document_id: z.string().uuid(),
  document_version_id: z.string().uuid(),
  display_name: z.string(),
  media_type: z.string(),
  size_bytes: z.number(),
  version_number: z.number(),
  status: z.enum([
    "uploaded",
    "queued",
    "extracting",
    "chunking",
    "embedding",
    "ready",
    "failed",
  ]),
  job_id: z.string().uuid(),
  job_status: z.enum(["pending", "running", "succeeded", "failed", "retry_scheduled"]),
  stage: z.string(),
  attempt_count: z.number(),
  error_code: z.string().nullable(),
  page_count: z.number().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

const uploadAcceptedSchema = z.object({
  document_id: z.string().uuid(),
  document_version_id: z.string().uuid(),
  job_id: z.string().uuid(),
  collection_id: z.string().uuid(),
  display_name: z.string(),
  version_number: z.number(),
  status: documentSchema.shape.status,
  job_status: documentSchema.shape.job_status,
  stage: z.string(),
  created_at: z.string(),
});

const documentListSchema = z.object({
  items: z.array(documentSchema),
  next_cursor: z.string().nullable(),
});

const conversationSchema = z.object({
  id: z.string().uuid(),
  collection_id: z.string().uuid(),
  title: z.string().nullable(),
  created_at: z.string(),
});

const errorEnvelopeSchema = z.object({
  error: z.object({
    code: z.string(),
    message_key: z.string(),
    request_id: z.string(),
    details: z.array(z.object({ field: z.string(), code: z.string() })).optional(),
  }),
});

export type Collection = z.infer<typeof collectionSchema>;
export type DocumentItem = z.infer<typeof documentSchema>;
export type UploadAccepted = z.infer<typeof uploadAcceptedSchema>;

export type Citation = {
  evidence_id: string;
  document_name: string;
  page_start: number;
  page_end: number;
  snippet: string;
};

export type AnswerStreamEvent =
  | { event: "retrieval_started"; data: { rag_run_id: string } }
  | { event: "retrieval_completed"; data: { evidence_count: number } }
  | { event: "answer_delta"; data: { text: string } }
  | { event: "citations"; data: { items: Citation[] } }
  | { event: "completed"; data: { abstained: boolean; rag_run_id: string } }
  | { event: "failure"; data: { code: string; message_key: string } };

export class ApiError extends Error {
  constructor(
    readonly code: string,
    readonly messageKey: string,
    readonly requestId?: string,
    readonly status?: number,
  ) {
    super(code);
    this.name = "ApiError";
  }
}

export async function createCollection(input: {
  name: string;
  description?: string;
  signal?: AbortSignal;
}): Promise<Collection> {
  return requestJson(
    "/api/v1/collections",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: input.name, description: input.description || null }),
      signal: input.signal,
    },
    collectionSchema,
  );
}

export async function getCollection(id: string, signal?: AbortSignal): Promise<Collection> {
  return requestJson(`/api/v1/collections/${id}`, { signal }, collectionSchema);
}

export async function listDocuments(
  collectionId: string,
  options: { cursor?: string; signal?: AbortSignal } = {},
) {
  const query = options.cursor ? `?cursor=${encodeURIComponent(options.cursor)}` : "";
  return requestJson(
    `/api/v1/collections/${collectionId}/documents${query}`,
    { signal: options.signal },
    documentListSchema,
  );
}

export function uploadDocument(
  collectionId: string,
  file: File,
  options: { onProgress: (percentage: number) => void; signal?: AbortSignal },
): Promise<UploadAccepted> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", `${apiBaseUrl}/api/v1/collections/${collectionId}/documents`);
    request.setRequestHeader("Accept", "application/json");
    request.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable) {
        options.onProgress(Math.round((event.loaded / event.total) * 100));
      }
    });
    request.addEventListener("load", () => {
      const payload: unknown = safeJson(request.responseText);
      if (request.status < 200 || request.status >= 300) {
        reject(apiErrorFromPayload(payload, request.status));
        return;
      }
      const parsed = uploadAcceptedSchema.safeParse(payload);
      if (!parsed.success) {
        reject(new ApiError("invalid_api_response", "errors.invalid_api_response"));
        return;
      }
      resolve(parsed.data);
    });
    request.addEventListener("error", () => {
      reject(new ApiError("network_error", "errors.network_error"));
    });
    request.addEventListener("abort", () => {
      reject(new DOMException("Upload cancelled", "AbortError"));
    });
    options.signal?.addEventListener("abort", () => request.abort(), { once: true });
    const form = new FormData();
    form.append("file", file, file.name);
    request.send(form);
  });
}

export async function getDocument(
  collectionId: string,
  documentId: string,
  signal?: AbortSignal,
): Promise<DocumentItem> {
  return requestJson(
    `/api/v1/collections/${collectionId}/documents/${documentId}`,
    { signal },
    documentSchema,
  );
}

export async function retryDocument(
  collectionId: string,
  documentId: string,
  signal?: AbortSignal,
): Promise<DocumentItem> {
  return requestJson(
    `/api/v1/collections/${collectionId}/documents/${documentId}/ingestion-retries`,
    { method: "POST", signal },
    documentSchema,
  );
}

export async function createConversation(
  collectionId: string,
  signal?: AbortSignal,
): Promise<string> {
  const conversation = await requestJson(
    `/api/v1/collections/${collectionId}/conversations`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: null }),
      signal,
    },
    conversationSchema,
  );
  return conversation.id;
}

export async function streamAnswer(input: {
  conversationId: string;
  question: string;
  language: "fa" | "en";
  signal: AbortSignal;
  onEvent: (event: AnswerStreamEvent) => void;
}): Promise<void> {
  const response = await fetch(
    `${apiBaseUrl}/api/v1/conversations/${input.conversationId}/messages:stream`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify({ question: input.question, language: input.language }),
      signal: input.signal,
    },
  );
  if (!response.ok) {
    throw apiErrorFromPayload(await safeResponseJson(response), response.status);
  }
  if (!response.body) {
    throw new ApiError("stream_unavailable", "errors.stream_unavailable");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    const parsed = parseEventStreamBuffer(buffer);
    buffer = parsed.remaining;
    parsed.events.forEach(input.onEvent);
    if (done) break;
  }
}

export function parseEventStreamBuffer(buffer: string): {
  events: AnswerStreamEvent[];
  remaining: string;
} {
  const normalized = buffer.replaceAll("\r\n", "\n");
  const frames = normalized.split("\n\n");
  const remaining = frames.pop() ?? "";
  const events: AnswerStreamEvent[] = [];
  for (const frame of frames) {
    const eventLine = frame.split("\n").find((line) => line.startsWith("event: "));
    const dataLines = frame
      .split("\n")
      .filter((line) => line.startsWith("data: "))
      .map((line) => line.slice(6));
    if (!eventLine || dataLines.length === 0) continue;
    const event = eventLine.slice(7);
    const data: unknown = safeJson(dataLines.join("\n"));
    const parsed = parseStreamEvent(event, data);
    if (parsed) events.push(parsed);
  }
  return { events, remaining };
}

async function requestJson<T>(
  path: string,
  init: RequestInit,
  schema: z.ZodType<T>,
): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers: { Accept: "application/json", ...init.headers },
  });
  const payload: unknown = await safeResponseJson(response);
  if (!response.ok) throw apiErrorFromPayload(payload, response.status);
  const parsed = schema.safeParse(payload);
  if (!parsed.success) {
    throw new ApiError("invalid_api_response", "errors.invalid_api_response", undefined, 502);
  }
  return parsed.data;
}

function apiErrorFromPayload(payload: unknown, status: number): ApiError {
  const parsed = errorEnvelopeSchema.safeParse(payload);
  if (!parsed.success) {
    return new ApiError("request_failed", "errors.request_failed", undefined, status);
  }
  return new ApiError(
    parsed.data.error.code,
    parsed.data.error.message_key,
    parsed.data.error.request_id,
    status,
  );
}

function parseStreamEvent(event: string, data: unknown): AnswerStreamEvent | null {
  if (!data || typeof data !== "object") return null;
  const record = data as Record<string, unknown>;
  if (event === "answer_delta" && typeof record.text === "string") {
    return { event, data: { text: record.text } };
  }
  if (event === "retrieval_started" && typeof record.rag_run_id === "string") {
    return { event, data: { rag_run_id: record.rag_run_id } };
  }
  if (event === "retrieval_completed" && typeof record.evidence_count === "number") {
    return { event, data: { evidence_count: record.evidence_count } };
  }
  if (event === "completed" && typeof record.abstained === "boolean") {
    return {
      event,
      data: {
        abstained: record.abstained,
        rag_run_id: String(record.rag_run_id ?? ""),
      },
    };
  }
  if (event === "failure" && typeof record.code === "string") {
    return {
      event,
      data: { code: record.code, message_key: String(record.message_key ?? "") },
    };
  }
  if (event === "citations" && Array.isArray(record.items)) {
    const items = z
      .array(
        z.object({
          evidence_id: z.string(),
          document_name: z.string(),
          page_start: z.number(),
          page_end: z.number(),
          snippet: z.string(),
        }),
      )
      .safeParse(record.items);
    if (items.success) return { event, data: { items: items.data } };
  }
  return null;
}

function safeJson(value: string): unknown {
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

async function safeResponseJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}
