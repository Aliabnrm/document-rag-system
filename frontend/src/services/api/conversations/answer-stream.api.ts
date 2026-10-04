import type { ZodType } from "zod";

import {
  AnswerCompletedDataSchema,
  AnswerDeltaDataSchema,
  AnswerFailureDataSchema,
  type AnswerStreamEvent,
  CitationsDataSchema,
  RetrievalCompletedDataSchema,
  RetrievalStartedDataSchema,
} from "@/schema/conversation/answer-stream.schema";
import { ApiError, apiErrorFromPayload } from "@/services/api/api-error";
import { runtimeConfig } from "@/services/runtime-config";

type StreamAnswerInput = {
  conversationId: string;
  question: string;
  language: "fa" | "en";
  signal: AbortSignal;
  onEvent: (event: AnswerStreamEvent) => void;
};

export async function streamAnswerApi(input: StreamAnswerInput): Promise<void> {
  const csrfToken = readBrowserCookie(runtimeConfig.csrfCookieName);
  const response = await fetch(
    `${runtimeConfig.apiBaseUrl}/api/v1/conversations/${input.conversationId}/messages:stream`,
    {
      method: "POST",
      credentials: "include",
      headers: {
        Accept: "text/event-stream",
        "Content-Type": "application/json",
        ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}),
      },
      body: JSON.stringify({
        question: input.question,
        language: input.language,
      }),
      signal: input.signal,
    },
  );

  if (!response.ok) {
    const payload = await safeResponseJson(response);
    throw apiErrorFromPayload(payload, response.status);
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
    if (done && buffer.trim()) buffer += "\n\n";
    const parsed = parseEventStreamBuffer(buffer);
    buffer = parsed.remaining;
    parsed.events.forEach(input.onEvent);
    if (done) break;
  }
}

function readBrowserCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const prefix = `${encodeURIComponent(name)}=`;
  const cookie = document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(prefix));
  if (!cookie) return null;
  const value = cookie.slice(prefix.length);
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

export function parseEventStreamBuffer(buffer: string): {
  events: AnswerStreamEvent[];
  remaining: string;
} {
  const frames = buffer.replaceAll("\r\n", "\n").split("\n\n");
  const remaining = frames.pop() ?? "";
  const events = frames.flatMap(parseEventStreamFrame);
  return { events, remaining };
}

function parseEventStreamFrame(frame: string): AnswerStreamEvent[] {
  const lines = frame.split("\n");
  const event = lines.find((line) => line.startsWith("event: "))?.slice(7);
  const dataLines = lines
    .filter((line) => line.startsWith("data: "))
    .map((line) => line.slice(6));
  if (!event || dataLines.length === 0) return [];

  const data = safeJson(dataLines.join("\n"));
  const parsed = parseStreamEvent(event, data);
  return parsed ? [parsed] : [];
}

function parseStreamEvent(event: string, data: unknown): AnswerStreamEvent | null {
  switch (event) {
    case "retrieval_started": {
      const parsed = parseEventData(data, RetrievalStartedDataSchema);
      return parsed ? { event, data: parsed } : null;
    }
    case "retrieval_completed": {
      const parsed = parseEventData(data, RetrievalCompletedDataSchema);
      return parsed ? { event, data: parsed } : null;
    }
    case "answer_delta": {
      const parsed = parseEventData(data, AnswerDeltaDataSchema);
      return parsed ? { event, data: parsed } : null;
    }
    case "citations": {
      const parsed = parseEventData(data, CitationsDataSchema);
      return parsed ? { event, data: parsed } : null;
    }
    case "completed": {
      const parsed = parseEventData(data, AnswerCompletedDataSchema);
      return parsed ? { event, data: parsed } : null;
    }
    case "failure": {
      const parsed = parseEventData(data, AnswerFailureDataSchema);
      return parsed ? { event, data: parsed } : null;
    }
    default:
      return null;
  }
}

function parseEventData<TData>(
  data: unknown,
  schema: ZodType<TData>,
): TData | null {
  const parsed = schema.safeParse(data);
  return parsed.success ? parsed.data : null;
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
