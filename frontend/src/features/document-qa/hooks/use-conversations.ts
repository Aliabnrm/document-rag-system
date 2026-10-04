"use client";

import { useInfiniteQuery } from "@tanstack/react-query";

import { listConversationsApi } from "@/services/api/conversations/conversations.api";
import { coreApi } from "@/services/api/core-api";

import { documentQaKeys } from "./query-keys";

export function useConversations(collectionId: string) {
  const query = useInfiniteQuery({
    queryKey: documentQaKeys.conversations(collectionId),
    queryFn: ({ pageParam, signal }) =>
      listConversationsApi(coreApi, collectionId, pageParam, signal),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (page) => page.next_cursor ?? undefined,
  });
  return {
    ...query,
    conversations: query.data?.pages.flatMap((page) => page.items) ?? [],
  };
}
