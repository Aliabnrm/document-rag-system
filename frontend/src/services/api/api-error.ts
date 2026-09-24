import axios from "axios";

import { ApiErrorEnvelopeSchema } from "@/schema/api/error.schema";

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

export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;

  if (axios.isAxiosError(error)) {
    if (error.response) {
      return apiErrorFromPayload(error.response.data, error.response.status);
    }
    return new ApiError("network_error", "errors.network_error");
  }

  return new ApiError("request_failed", "errors.request_failed");
}

export function apiErrorFromPayload(payload: unknown, status: number): ApiError {
  const envelope = ApiErrorEnvelopeSchema.safeParse(payload);
  if (!envelope.success) {
    return new ApiError("request_failed", "errors.request_failed", undefined, status);
  }

  return new ApiError(
    envelope.data.error.code,
    envelope.data.error.message_key,
    envelope.data.error.request_id,
    status,
  );
}

export function errorCodeOf(error: unknown): string {
  return toApiError(error).code;
}

export function isAbortError(error: unknown): boolean {
  return (
    axios.isCancel(error) ||
    (error instanceof DOMException && error.name === "AbortError")
  );
}
