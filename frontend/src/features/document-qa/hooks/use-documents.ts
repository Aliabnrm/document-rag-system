"use client";

import { useInfiniteQuery } from "@tanstack/react-query";

import { coreApi } from "@/services/api/core-api";
import { listDocumentsApi } from "@/services/api/documents/documents.api";

import { PROCESSING_DOCUMENT_STATUSES } from "../model/constants";
import { documentQaKeys } from "./query-keys";

export function useDocuments(collectionId?: string) {
  const query = useInfiniteQuery({
    queryKey: documentQaKeys.documents(collectionId ?? "inactive"),
    queryFn: ({ pageParam, signal }) =>
      listDocumentsApi(coreApi, collectionId!, {
        cursor: pageParam,
        signal,
      }),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    enabled: Boolean(collectionId),
    refetchInterval: ({ state }) => {
      const hasProcessingDocument = state.data?.pages.some((page) =>
        page.items.some((document) =>
          PROCESSING_DOCUMENT_STATUSES.has(document.status),
        ),
      );
      return hasProcessingDocument ? 1_200 : false;
    },
  });

  return {
    ...query,
    documents: query.data?.pages.flatMap((page) => page.items) ?? [],
  };
}
