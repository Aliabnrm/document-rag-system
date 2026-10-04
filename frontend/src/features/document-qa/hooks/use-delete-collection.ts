"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { deleteCollectionApi } from "@/services/api/collections/collections.api";
import { coreApi } from "@/services/api/core-api";

import { documentQaKeys } from "./query-keys";

export function useDeleteCollection() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (collectionId: string) =>
      deleteCollectionApi(coreApi, collectionId),
    onSuccess: (_, collectionId) => {
      queryClient.removeQueries({
        queryKey: documentQaKeys.collection(collectionId),
      });
      return queryClient.invalidateQueries({
        queryKey: documentQaKeys.collections(),
      });
    },
  });
}
