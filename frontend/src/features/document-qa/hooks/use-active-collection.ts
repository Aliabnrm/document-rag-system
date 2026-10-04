"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import type {
  Collection,
  CreateCollectionInput,
} from "@/schema/collection/collection.schema";
import { errorCodeOf } from "@/services/api/api-error";
import {
  createCollectionApi,
  getCollectionApi,
} from "@/services/api/collections/collections.api";
import { coreApi } from "@/services/api/core-api";

import { documentQaKeys } from "./query-keys";

export function useActiveCollection(initialCollectionId?: string) {
  const queryClient = useQueryClient();
  const [collectionId, setCollectionId] = useState<string | null>(
    initialCollectionId ?? null,
  );

  const collectionQuery = useQuery({
    queryKey: documentQaKeys.collection(collectionId ?? "inactive"),
    queryFn: ({ signal }) => getCollectionApi(coreApi, collectionId!, signal),
    enabled: Boolean(collectionId),
  });

  const createCollection = useMutation({
    mutationFn: (input: CreateCollectionInput) => createCollectionApi(coreApi, input),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: documentQaKeys.collections() }),
  });

  function activateCollection(collection: Collection) {
    queryClient.setQueryData(documentQaKeys.collection(collection.id), collection);
    setCollectionId(collection.id);
  }

  function clearCollection() {
    queryClient.removeQueries({ queryKey: documentQaKeys.collection(collectionId ?? "") });
    setCollectionId(null);
    createCollection.reset();
  }

  return {
    collection: collectionQuery.data ?? null,
    isBooting: Boolean(collectionId) && collectionQuery.isPending,
    restoreErrorCode: collectionQuery.error
      ? errorCodeOf(collectionQuery.error)
      : null,
    createCollection,
    activateCollection,
    clearCollection,
  };
}
