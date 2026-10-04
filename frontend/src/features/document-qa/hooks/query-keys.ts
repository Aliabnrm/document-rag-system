export const documentQaKeys = {
  all: ["document-qa"] as const,
  collections: () => [...documentQaKeys.all, "collections"] as const,
  collection: (collectionId: string) =>
    [...documentQaKeys.all, "collection", collectionId] as const,
  documents: (collectionId: string) =>
    [...documentQaKeys.all, "documents", collectionId] as const,
  conversations: (collectionId: string) =>
    [...documentQaKeys.all, "conversations", collectionId] as const,
  messages: (conversationId: string) =>
    [...documentQaKeys.all, "messages", conversationId] as const,
};
