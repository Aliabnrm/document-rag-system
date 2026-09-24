import type { AxiosInstance } from "axios";

import {
  CollectionSchema,
  type Collection,
  type CreateCollectionInput,
} from "@/schema/collection/collection.schema";
import { requestAndParse } from "@/services/api/core-api";

export function createCollectionApi(
  api: AxiosInstance,
  input: CreateCollectionInput,
  signal?: AbortSignal,
): Promise<Collection> {
  return requestAndParse(
    api.post(
      "/api/v1/collections",
      {
        name: input.name,
        description: input.description || null,
      },
      { signal },
    ),
    CollectionSchema,
  );
}

export function getCollectionApi(
  api: AxiosInstance,
  collectionId: string,
  signal?: AbortSignal,
): Promise<Collection> {
  return requestAndParse(
    api.get(`/api/v1/collections/${collectionId}`, { signal }),
    CollectionSchema,
  );
}
