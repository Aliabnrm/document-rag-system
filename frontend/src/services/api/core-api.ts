import axios, { type AxiosResponse } from "axios";
import { type ZodType } from "zod";

import { runtimeConfig } from "@/services/runtime-config";

import { ApiError, isAbortError, toApiError } from "./api-error";

export const coreApi = axios.create({
  baseURL: runtimeConfig.apiBaseUrl,
  withCredentials: true,
  withXSRFToken: true,
  xsrfCookieName: runtimeConfig.csrfCookieName,
  xsrfHeaderName: "X-CSRF-Token",
  headers: {
    Accept: "application/json",
  },
  timeout: 30_000,
});

export async function requestAndParse<T>(
  request: Promise<AxiosResponse<unknown>>,
  schema: ZodType<T>,
): Promise<T> {
  try {
    const response = await request;
    const parsed = schema.safeParse(response.data);
    if (!parsed.success) {
      throw new ApiError(
        "invalid_api_response",
        "errors.invalid_api_response",
        undefined,
        502,
      );
    }
    return parsed.data;
  } catch (error: unknown) {
    if (isAbortError(error)) throw error;
    throw toApiError(error);
  }
}
