"use client";

import { useInfiniteQuery } from "@tanstack/react-query";

import { listCollectionsApi } from "@/services/api/collections/collections.api";
import { coreApi } from "@/services/api/core-api";

import { documentQaKeys } from "./query-keys";

export function useCollections() {
  const query = useInfiniteQuery({
    queryKey: documentQaKeys.collections(),
    queryFn: ({ pageParam, signal }) =>
      listCollectionsApi(coreApi, pageParam, signal),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (page) => page.next_cursor ?? undefined,
  });
  return {
    ...query,
    collections: query.data?.pages.flatMap((page) => page.items) ?? [],
  };
}
