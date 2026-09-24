import type { AxiosInstance } from "axios";

import { ConversationSchema, type Conversation } from "@/schema/conversation/conversation.schema";
import { requestAndParse } from "@/services/api/core-api";

export function createConversationApi(
  api: AxiosInstance,
  collectionId: string,
  signal?: AbortSignal,
): Promise<Conversation> {
  return requestAndParse(
    api.post(
      `/api/v1/collections/${collectionId}/conversations`,
      { title: null },
      { signal },
    ),
    ConversationSchema,
  );
}
