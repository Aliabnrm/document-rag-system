"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { coreApi } from "@/services/api/core-api";
import { retryDocumentApi } from "@/services/api/documents/documents.api";

import { documentQaKeys } from "./query-keys";

export function useRetryDocument(collectionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (documentId: string) =>
      retryDocumentApi(coreApi, collectionId, documentId),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: documentQaKeys.documents(collectionId),
      }),
  });
}
