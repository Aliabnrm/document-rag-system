import type { AxiosInstance } from "axios";

import {
  ConversationListPageSchema,
  ConversationSchema,
  MessageListPageSchema,
  type Conversation,
  type ConversationListPage,
  type MessageListPage,
} from "@/schema/conversation/conversation.schema";
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

export function listConversationsApi(
  api: AxiosInstance,
  collectionId: string,
  cursor?: string,
  signal?: AbortSignal,
): Promise<ConversationListPage> {
  return requestAndParse(
    api.get(`/api/v1/collections/${collectionId}/conversations`, {
      params: { cursor, page_size: 20 },
      signal,
    }),
    ConversationListPageSchema,
  );
}

export function listConversationMessagesApi(
  api: AxiosInstance,
  conversationId: string,
  afterPosition?: number,
  signal?: AbortSignal,
): Promise<MessageListPage> {
  return requestAndParse(
    api.get(`/api/v1/conversations/${conversationId}/messages`, {
      params: { after_position: afterPosition, page_size: 100 },
      signal,
    }),
    MessageListPageSchema,
  );
}
