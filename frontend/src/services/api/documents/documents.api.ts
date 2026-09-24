import type { AxiosInstance } from "axios";

import {
  DocumentListSchema,
  DocumentSchema,
  UploadAcceptedSchema,
  type DocumentItem,
  type DocumentList,
  type UploadAccepted,
} from "@/schema/document/document.schema";
import { requestAndParse } from "@/services/api/core-api";

type ListDocumentsOptions = {
  cursor?: string | null;
  signal?: AbortSignal;
};

type UploadDocumentOptions = {
  onProgress: (percentage: number) => void;
  signal?: AbortSignal;
};

export function listDocumentsApi(
  api: AxiosInstance,
  collectionId: string,
  options: ListDocumentsOptions = {},
): Promise<DocumentList> {
  return requestAndParse(
    api.get(`/api/v1/collections/${collectionId}/documents`, {
      params: options.cursor ? { cursor: options.cursor } : undefined,
      signal: options.signal,
    }),
    DocumentListSchema,
  );
}

export function uploadDocumentApi(
  api: AxiosInstance,
  collectionId: string,
  file: File,
  options: UploadDocumentOptions,
): Promise<UploadAccepted> {
  const form = new FormData();
  form.append("file", file, file.name);

  return requestAndParse(
    api.post(`/api/v1/collections/${collectionId}/documents`, form, {
      signal: options.signal,
      timeout: 0,
      onUploadProgress: (event) => {
        if (event.total) {
          options.onProgress(Math.round((event.loaded / event.total) * 100));
        }
      },
    }),
    UploadAcceptedSchema,
  );
}

export function retryDocumentApi(
  api: AxiosInstance,
  collectionId: string,
  documentId: string,
  signal?: AbortSignal,
): Promise<DocumentItem> {
  return requestAndParse(
    api.post(
      `/api/v1/collections/${collectionId}/documents/${documentId}/ingestion-retries`,
      undefined,
      { signal },
    ),
    DocumentSchema,
  );
}
