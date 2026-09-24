"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { z } from "zod";

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

import { COLLECTION_STORAGE_KEY } from "../model/constants";
import { documentQaKeys } from "./query-keys";

const StoredCollectionIdSchema = z.string().uuid();

export function useActiveCollection() {
  const queryClient = useQueryClient();
  const [collectionId, setCollectionId] = useState<string | null | undefined>();

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const stored = window.localStorage.getItem(COLLECTION_STORAGE_KEY);
      const parsed = StoredCollectionIdSchema.safeParse(stored);
      if (parsed.success) {
        setCollectionId(parsed.data);
      } else {
        window.localStorage.removeItem(COLLECTION_STORAGE_KEY);
        setCollectionId(null);
      }
    }, 0);

    return () => window.clearTimeout(timer);
  }, []);

  const collectionQuery = useQuery({
    queryKey: documentQaKeys.collection(collectionId ?? "inactive"),
    queryFn: ({ signal }) => getCollectionApi(coreApi, collectionId!, signal),
    enabled: Boolean(collectionId),
  });

  const createCollection = useMutation({
    mutationFn: (input: CreateCollectionInput) => createCollectionApi(coreApi, input),
  });

  function activateCollection(collection: Collection) {
    window.localStorage.setItem(COLLECTION_STORAGE_KEY, collection.id);
    queryClient.setQueryData(documentQaKeys.collection(collection.id), collection);
    setCollectionId(collection.id);
  }

  function clearCollection() {
    window.localStorage.removeItem(COLLECTION_STORAGE_KEY);
    queryClient.removeQueries({ queryKey: documentQaKeys.all });
    setCollectionId(null);
    createCollection.reset();
  }

  return {
    collection: collectionQuery.data ?? null,
    isBooting:
      collectionId === undefined ||
      (Boolean(collectionId) && collectionQuery.isPending),
    restoreErrorCode: collectionQuery.error
      ? errorCodeOf(collectionQuery.error)
      : null,
    createCollection,
    activateCollection,
    clearCollection,
  };
}
